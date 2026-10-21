"""Korekta rozmiaru i położenia obszaru netto stron (TrimBox) — czysta logika, bez PyMuPDF i Tk.

Wzorowane na oknie Impozycjonera 4 „Korekta położenia i rozmiaru obszaru netto” (menu tabeli stron
„Koryguj odczytane rozmiary…”); z tekstów okna i komunikatów (E1) oraz metadanych wywołań (REA):
  * rozmiar netto: poziomo H × pionowo V [mm] i położenie (odsunięcia od krawędzi strony);
  * zakres: wybrana strona albo wszystkie / nieparzyste / parzyste strony, w zaznaczonym pliku albo w całej tabeli;
  * korekta trafia tylko na strony o tym samym rozmiarze co strona korygowana — pozostałe są wypisywane;
  * „wczytaj wartości zdefiniowane w pliku” = powrót do TrimBox z pliku;
  * korekta jest zapamiętana w tabeli (projekcie), plik PDF na dysku się nie zmienia.
Decyzje własne (H-38): ramka w mm w widocznej orientacji strony (po /Rotate), liczona od lewego górnego rogu
widocznej strony; „ten sam rozmiar” = obie krawędzie różnią się ≤ 0,5 mm (jak tolerancja formatu w silniku).

Ramka = (z lewej, od góry, szerokość, wysokość) w mm.
"""
from __future__ import annotations

from math import isfinite

SCOPE_PAGE = 'Tylko ta strona'
SCOPE_ALL = 'Wszystkie strony'
SCOPE_ODD = 'Strony nieparzyste'
SCOPE_EVEN = 'Strony parzyste'
SCOPES = (SCOPE_PAGE, SCOPE_ALL, SCOPE_ODD, SCOPE_EVEN)
SIZE_TOLERANCE = 0.5

Box = tuple[float, float, float, float]


def check_box(box, page_w: float, page_h: float) -> Box:
    """Ramka musi mieć dodatnie wymiary i mieścić się w stronie (tolerancja 0,01 mm)."""
    if len(box) != 4:
        raise ValueError('Ramka netto: z lewej, od góry, szerokość, wysokość')
    left, top, width, height = (float(v) for v in box)
    if not all(isfinite(v) for v in (left, top, width, height)):
        raise ValueError('Ramka netto: wartości muszą być liczbami')
    if width <= 0 or height <= 0:
        raise ValueError('Rozmiar netto musi być większy od zera')
    if left < -0.01 or top < -0.01 or left + width > page_w + 0.01 or top + height > page_h + 0.01:
        raise ValueError(f'Ramka netto {width:g} × {height:g} mm (od {left:g}, {top:g}) wychodzi poza stronę '
                         f'{page_w:g} × {page_h:g} mm')
    return (round(left, 3), round(top, 3), round(width, 3), round(height, 3))


def centred(page_w: float, page_h: float, width: float, height: float) -> Box:
    """Ramka o zadanym rozmiarze wyśrodkowana na stronie."""
    return check_box(((page_w - width) / 2, (page_h - height) / 2, width, height), page_w, page_h)


def same_size(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= SIZE_TOLERANCE and abs(a[1] - b[1]) <= SIZE_TOLERANCE


def in_scope(page: int, chosen: int, scope: str) -> bool:
    """Czy strona (od 1) należy do zakresu korekty wyznaczonego od strony `chosen`."""
    if scope == SCOPE_PAGE:
        return page == chosen
    if scope == SCOPE_ALL:
        return True
    if scope == SCOPE_ODD:
        return page % 2 == 1
    if scope == SCOPE_EVEN:
        return page % 2 == 0
    raise ValueError(f'Nieznany zakres korekty: {scope}')


def plan_correction(files: list[list[tuple[float, float]]], chosen_file: int, chosen_page: int,
                    scope: str, whole_table: bool) -> tuple[dict[int, list[int]], list[tuple[int, int]]]:
    """Strony, na które trafi korekta, i strony pominięte (inny rozmiar niż strona korygowana).

    `files` = rozmiary stron (szer., wys. w mm, widoczne) każdego pliku tabeli. Zwraca
    ({plik: [strony od 1]}, [(plik, strona) pominięte]).
    """
    reference = files[chosen_file][chosen_page - 1]
    targets: dict[int, list[int]] = {}
    skipped: list[tuple[int, int]] = []
    for f, sizes in enumerate(files):
        if f != chosen_file and (not whole_table or scope == SCOPE_PAGE):
            continue
        for page, size in enumerate(sizes, start=1):
            if f == chosen_file and scope == SCOPE_PAGE and page != chosen_page:
                continue
            if not in_scope(page, chosen_page, scope):
                continue
            if same_size(size, reference):
                targets.setdefault(f, []).append(page)
            else:
                skipped.append((f, page))
    return targets, skipped


def apply(boxes: dict[str, list[float]], pages: list[int], box: Box | None) -> dict[str, list[float]]:
    """Nowe korekty pliku: ustaw ramkę na stronach `pages` albo (box=None) wróć do wartości z pliku."""
    result = dict(boxes)
    for page in pages:
        if box is None:
            result.pop(str(page), None)
        else:
            result[str(page)] = list(box)
    return result
