"""Reguły nazwy pliku wynikowego (czysty Python, bez PyMuPDF i Tk).

Z tekstów okien Impozycjonera 4 (własne streszczenie, nie kopia): nazwa pliku wynikowego nie może
zawierać znaków # % & * : < > ? / \\ { } ani pionowej kreski i nie może być nazwą pliku
przetwarzanego; opcjonalnie dopisuje się stałą frazę „--IMPOZYCJONER”.
Decyzja własna: porównanie z plikami wejściowymi bez katalogu i bez rozróżniania wielkości liter.
"""
from __future__ import annotations

import re

FORBIDDEN_OUTPUT_CHARS = '#%&*:<>?/\\{}|'
IMPOSITION_PHRASE = '--IMPOZYCJONER'

_SEPARATORS = re.compile(r'[\\/]')
_PDF_EXTENSION = re.compile(r'\.pdf$', re.IGNORECASE)


def output_name_problem(name: str, inputs: list[str] = ()) -> str | None:
    """Komunikat błędu dla nazwy pliku wynikowego (bez katalogu) albo None, gdy nazwa jest poprawna."""
    if not isinstance(name, str) or not name.strip() or not _PDF_EXTENSION.sub('', name).strip():
        return 'Podaj nazwę pliku wynikowego.'
    bad = sorted({ch for ch in name if ch in FORBIDDEN_OUTPUT_CHARS})
    if bad:
        return ('Nazwa pliku wynikowego zawiera niedozwolone znaki: ' + ' '.join(bad)
                + '. Niedozwolone są: ' + ' '.join(FORBIDDEN_OUTPUT_CHARS) + '.')
    lowered = name.casefold()
    for source in inputs:
        if _SEPARATORS.split(source)[-1].casefold() == lowered:
            return 'Nazwa pliku wynikowego nie może być taka sama jak nazwa pliku przetwarzanego.'
    return None


def add_imposition_phrase(name: str) -> str:
    """Dopisz „--IMPOZYCJONER” przed rozszerzeniem .pdf (raz; ponowne wywołanie nic nie zmienia)."""
    stem = _PDF_EXTENSION.sub('', name)
    extension = name[len(stem):] or '.pdf'
    if stem.endswith(IMPOSITION_PHRASE):
        return stem + extension
    return stem + IMPOSITION_PHRASE + extension


IMPOSITION_SUFFIX = 'impozycja'
PAGES_SUFFIX = 'strony'


def _mm(value: float) -> str:
    """Wymiar do nazwy pliku: bez zbędnych zer, przecinek dziesiętny (np. 93, 148,5)."""
    text = f'{round(float(value), 2):.2f}'.rstrip('0').rstrip('.')
    return text.replace('.', ',')


def default_output_name(source: str, trim_w: float, trim_h: float, suffix: str = IMPOSITION_SUFFIX) -> str:
    """Podpowiadana nazwa pliku po impozycji: <nazwa oryginału>_<netto szer.>x<netto wys.>mm_<dopisek>.pdf.

    Np. „wizytowki.pdf”, użytek 93 × 53 → „wizytowki_93x53mm_impozycja.pdf”. Znaki niedozwolone w nazwie
    pliku wynikowego są zamieniane na podkreślenie; pusta nazwa źródła → „montaz”.
    """
    stem = _PDF_EXTENSION.sub('', _SEPARATORS.split(source or '')[-1]).strip()
    stem = ''.join('_' if ch in FORBIDDEN_OUTPUT_CHARS else ch for ch in stem) or 'montaz'
    return f'{stem}_{_mm(trim_w)}x{_mm(trim_h)}mm_{suffix}.pdf'


# --- Łączenie plików wynikowych (okno „Łączenie plików wynikowych” Imp4, E1; H-48) ----------------------------

OUTPUT_ONE = 'Jeden plik'
OUTPUT_MODES = (
    OUTPUT_ONE,
    'Jeden plik + arkusze',
    'Jeden plik + arkusze + każda strona osobno',
    'Jeden plik + każda strona osobno',
    'Arkusze',
    'Arkusze + każda strona osobno',
    'Każda strona osobno (bez łączenia)',
)


def output_parts(mode: str) -> tuple[bool, bool, bool]:
    """(jeden plik, plik na każdy arkusz, plik na każdą stronę) dla wariantu łączenia."""
    if mode not in OUTPUT_MODES:
        raise ValueError(f'Pliki wynikowe: {", ".join(OUTPUT_MODES)}')
    if mode == OUTPUT_MODES[-1]:
        return False, False, True
    return mode.startswith('Jeden plik'), 'arkusze' in mode.lower(), 'osobno' in mode


def _numbered(name: str, word: str, number: int, count: int) -> str:
    stem = _PDF_EXTENSION.sub('', name)
    width = max(2, len(str(count)))
    return f'{stem}--{word}{number:0{width}d}.pdf'


def sheet_file_name(output_name: str, number: int, count: int) -> str:
    """Plik arkusza: <nazwa>--arkusz-01.pdf (H-48)."""
    return _numbered(output_name, 'arkusz-', number, count)


def page_file_name(output_name: str, number: int, count: int) -> str:
    """Plik pojedynczej strony pliku wynikowego: <nazwa>--01.pdf (jak przy dzieleniu stron, P-06; H-48)."""
    return _numbered(output_name, '', number, count)
