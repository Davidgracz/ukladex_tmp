"""Wiersze tabeli stron: wakaty, wstawianie i zamiana plików/stron, kopiuj/wytnij/wklej — czysta logika.

Wzorowane na menu tabeli stron Impozycjonera 4 (E1, teksty menu): wstaw wakat PRZED / PO / TUTAJ (wyczyść wiersz),
usuń wszystkie dodane wakaty, wstaw plik PRZED / PO, zamień plik/stronę, zamień na inną stronę z pliku, kopiuj,
wytnij, wklej, zaznacz wiersze ujęte / nieujęte w impozycji, zaznacz takie same.

Model (H-45): pozycja projektu (`Job`) ma opcjonalną listę `pages` — kolejność wierszy: numer strony pliku (od 1)
albo `None` = wakat (puste pole użytku). Brak listy = wszystkie strony pliku po kolei (dotychczasowe zachowanie).
Wstawienie pliku albo stron innego pliku w środek pozycji dzieli ją na dwie pozycje z tymi samymi ustawieniami;
przy nakładzie > 1 byłoby to zmianą kolejności druku, więc jest jawnie odrzucane. Sąsiednie pozycje tego samego
pliku o identycznych ustawieniach są po operacji scalane.

Wewnątrz modułu strony liczymy od 0 (jak w silniku), w `Job.pages` — od 1 (jak w tabeli i w projekcie).
"""
from __future__ import annotations

import copy
from dataclasses import fields, replace
from typing import Callable, Sequence

Row = int | None   # strona od 0 albo wakat

WHERE_BEFORE = 'przed'
WHERE_AFTER = 'po'
WHERE_HERE = 'tutaj'


def sequence(pages: Sequence | None, count: int) -> list[Row]:
    """Wiersze pozycji (strony od 0 / None). Zły wpis → ValueError z opisem."""
    if pages is None:
        return list(range(count))
    if not isinstance(pages, (list, tuple)):
        raise ValueError('Kolejność stron pozycji musi być listą')
    result: list[Row] = []
    for entry in pages:
        if entry is None:
            result.append(None)
            continue
        if type(entry) is not int or not 1 <= entry <= count:
            raise ValueError(f'Kolejność stron: strona {entry!r} poza zakresem 1–{count}')
        result.append(entry - 1)
    return result


def stored(rows: Sequence[Row], count: int) -> list[int | None] | None:
    """Postać do zapisu w projekcie; pełna kolejność 1…n bez wakatów → None (jak stare projekty)."""
    if list(rows) == list(range(count)):
        return None
    return [None if r is None else r + 1 for r in rows]


def _check_row(rows: Sequence[Row], row: int, allow_end: bool = False):
    high = len(rows) if allow_end else len(rows) - 1
    if type(row) is not int or not 0 <= row <= high:
        raise ValueError('Nie ma takiego wiersza w pozycji')


def insert_vacancy(rows: Sequence[Row], row: int, where: str, count: int = 1) -> list[Row]:
    """Wakat przed / po wierszu albo w jego miejscu (wiersz zostaje wyczyszczony)."""
    _check_row(rows, row)
    if type(count) is not int or not 1 <= count <= 1000:
        raise ValueError('Liczba wakatów: 1–1000')
    result = list(rows)
    if where == WHERE_HERE:
        result[row] = None
    elif where == WHERE_BEFORE:
        result[row:row] = [None] * count
    elif where == WHERE_AFTER:
        result[row + 1:row + 1] = [None] * count
    else:
        raise ValueError(f'Nieznane położenie wakatu: {where}')
    return result


def remove_vacancies(rows: Sequence[Row]) -> list[Row]:
    return [r for r in rows if r is not None]


def replace_page(rows: Sequence[Row], row: int, page: int, count: int) -> list[Row]:
    _check_row(rows, row)
    if type(page) is not int or not 0 <= page < count:
        raise ValueError(f'Strona poza zakresem 1–{count}')
    result = list(rows)
    result[row] = page
    return result


# --- operacje na liście pozycji (plików) ------------------------------------------------------

Counts = Callable[[str], int]   # liczba stron pliku


def _rows(job, counts: Counts) -> list[Row]:
    return sequence(job.pages, counts(job.path))


def _with_rows(job, rows: Sequence[Row], counts: Counts):
    return replace(job, pages=stored(rows, counts(job.path)), page_roles=copy.deepcopy(job.page_roles),
                   page_boxes=copy.deepcopy(job.page_boxes), page_sizes=copy.deepcopy(job.page_sizes))


def _same_settings(a, b) -> bool:
    return all(getattr(a, f.name) == getattr(b, f.name) for f in fields(a) if f.name != 'pages')


def normalize(jobs: list, counts: Counts) -> list:
    """Scala sąsiednie pozycje tego samego pliku o tych samych ustawieniach (nakład 1); usuwa puste pozycje."""
    result: list = []
    for job in jobs:
        rows = _rows(job, counts)
        if not rows:
            continue
        if result and result[-1].copies == 1 and job.copies == 1 and _same_settings(result[-1], job):
            result[-1] = _with_rows(result[-1], _rows(result[-1], counts) + rows, counts)
        else:
            result.append(_with_rows(job, rows, counts))
    return result


def split(jobs: list, index: int, row: int, counts: Counts) -> tuple[list, int]:
    """Dzieli pozycję przed wierszem `row`. Zwraca (nowa lista, indeks pozycji, przed którą można wstawiać)."""
    job = jobs[index]
    rows = _rows(job, counts)
    _check_row(rows, row, allow_end=True)
    if row in (0, len(rows)):
        return list(jobs), index + (row == len(rows))
    if job.copies != 1:
        raise ValueError(f'{job.path}: nie można wstawiać w środek pozycji z nakładem {job.copies} — kolejność '
                         'druku by się zmieniła. Ustaw nakład 1 albo wstaw przed lub po całej pozycji.')
    head, tail = _with_rows(job, rows[:row], counts), _with_rows(job, rows[row:], counts)
    return list(jobs[:index]) + [head, tail] + list(jobs[index + 1:]), index + 1


def insert_jobs(jobs: list, index: int, row: int, where: str, new_jobs: list, counts: Counts) -> list:
    """Wstawia pozycje (np. nowy plik albo wklejone wiersze) przed / po wierszu `row` pozycji `index`."""
    if where not in (WHERE_BEFORE, WHERE_AFTER):
        raise ValueError(f'Nieznane położenie: {where}')
    rows = _rows(jobs[index], counts)
    _check_row(rows, row)
    at = row if where == WHERE_BEFORE else row + 1
    parts, position = split(jobs, index, at, counts)
    return normalize(parts[:position] + list(new_jobs) + parts[position:], counts)


def replace_with_page_of(jobs: list, index: int, row: int, job_template, page: int, counts: Counts) -> list:
    """„Zamień plik/stronę”: wiersz dostaje stronę `page` (od 0) innego albo tego samego pliku."""
    target = jobs[index]
    rows = _rows(target, counts)
    _check_row(rows, row)
    if job_template.path == target.path and _same_settings(job_template, target):
        result = list(jobs)
        result[index] = _with_rows(target, replace_page(rows, row, page, counts(target.path)), counts)
        return result
    count = counts(job_template.path)
    if type(page) is not int or not 0 <= page < count:
        raise ValueError(f'Strona poza zakresem 1–{count}')
    if target.copies != 1 and len(rows) > 1:
        raise ValueError(f'{target.path}: zamiana jednego wiersza na stronę innego pliku przy nakładzie '
                         f'{target.copies} zmieniłaby kolejność druku. Ustaw nakład 1.')
    new = _with_rows(replace(job_template, copies=target.copies), [page], counts)
    pieces = [_with_rows(target, rows[:row], counts), new, _with_rows(target, rows[row + 1:], counts)]
    return normalize(list(jobs[:index]) + pieces + list(jobs[index + 1:]), counts)   # puste części znikają


def copy_rows(jobs: list, selection: Sequence[tuple[int, int]], counts: Counts) -> list[tuple[object, Row]]:
    """Schowek: [(wzór pozycji bez kolejności stron, strona od 0 / None)] w kolejności tabeli."""
    clip = []
    for index, row in sorted(set(selection)):
        rows = _rows(jobs[index], counts)
        _check_row(rows, row)
        clip.append((replace(jobs[index], pages=None), rows[row]))
    return clip


def remove_rows(jobs: list, selection: Sequence[tuple[int, int]], counts: Counts) -> list:
    """„Wytnij”: usuwa wiersze z pozycji; pozycja bez wierszy znika z projektu."""
    chosen: dict[int, set[int]] = {}
    for index, row in selection:
        _check_row(_rows(jobs[index], counts), row)
        chosen.setdefault(index, set()).add(row)
    result = []
    for index, job in enumerate(jobs):
        rows = _rows(job, counts)
        if index in chosen:
            if job.copies != 1 and len(chosen[index]) < len(rows):
                raise ValueError(f'{job.path}: wycinanie części wierszy przy nakładzie {job.copies} — ustaw nakład 1.')
            rows = [r for i, r in enumerate(rows) if i not in chosen[index]]
        if rows:
            result.append(_with_rows(job, rows, counts))
    return normalize(result, counts)


def jobs_from_clipboard(clip: Sequence[tuple[object, Row]], counts: Counts) -> list:
    """Wklejane pozycje: kolejne wiersze tego samego pliku i ustawień tworzą jedną pozycję (nakład 1)."""
    result = []
    for template, row in clip:
        if result and result[-1][0].path == template.path and _same_settings(result[-1][0], template):
            result[-1][1].append(row)
        else:
            result.append((replace(template, copies=1), [row]))
    return [_with_rows(template, rows, counts) for template, rows in result]


# --- zaznaczanie --------------------------------------------------------------------------------

def rows_included(jobs: list, counts: Counts, skip_role: str) -> list[tuple[int, int]]:
    """Wiersze ujęte w impozycji: strony bez roli „Pomiń” oraz wakaty (zajmują pole użytku)."""
    found = []
    for index, job in enumerate(jobs):
        for row, page in enumerate(_rows(job, counts)):
            if page is None or job.role_for(page) != skip_role:
                found.append((index, row))
    return found


def rows_excluded(jobs: list, counts: Counts, skip_role: str) -> list[tuple[int, int]]:
    included = set(rows_included(jobs, counts, skip_role))
    return [(i, r) for i, job in enumerate(jobs) for r in range(len(_rows(job, counts))) if (i, r) not in included]


def rows_same(jobs: list, counts: Counts, chosen: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Wiersze z tą samą stroną tego samego pliku co zaznaczone (wakaty — wszystkie wakaty)."""
    wanted = set()
    for index, row in chosen:
        rows = _rows(jobs[index], counts)
        _check_row(rows, row)
        wanted.add(None if rows[row] is None else (jobs[index].path, rows[row]))
    found = []
    for index, job in enumerate(jobs):
        for row, page in enumerate(_rows(job, counts)):
            if (None if page is None else (job.path, page)) in wanted:
                found.append((index, row))
    return found
