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


# --- Zmiana rozmiaru stron (skalowanie TrimBox do zadanych wymiarów) --------------------------------------------
# Obserwacja działającego Impozycjonera (E3, zrzuty użytkownika 2026-10-21, wersja nowsza niż 4.0.4.0 w G:\ukladex):
# tabela stron → „Zmień parametry w zaznaczonych wierszach” (Szerokość / Wysokość [mm]) skaluje strony A4 i A6 do
# 108 × 151; opcje rozmiaru: „szerokość i wysokość niezależnie” (+ „włącz kadrowanie”), „tylko szerokość
# (wysokość proporcjonalnie)”, „tylko wysokość (szerokość proporcjonalnie)”, „nowa szerokość i wysokość TrimBox”,
# „zachowaj orientację (pion/poziom)”, „definiuj spad [mm]”.
RESIZE_STRETCH = 'Szerokość i wysokość niezależnie'
RESIZE_CROP = 'Szerokość i wysokość z kadrowaniem'
RESIZE_WIDTH = 'Tylko szerokość (wysokość proporcjonalnie)'
RESIZE_HEIGHT = 'Tylko wysokość (szerokość proporcjonalnie)'
RESIZE_MODES = (RESIZE_STRETCH, RESIZE_CROP, RESIZE_WIDTH, RESIZE_HEIGHT)


def resize_spec(width: float, height: float, mode: str = RESIZE_STRETCH, keep_orientation: bool = True,
                bleed: float = 0.0) -> dict:
    """Sprawdzony opis zmiany rozmiaru jednej strony (zapisywany w projekcie)."""
    if mode not in RESIZE_MODES:
        raise ValueError(f'Nieznany sposób zmiany rozmiaru: {mode}')
    for value, label in ((width, 'Szerokość'), (height, 'Wysokość')):
        if not isfinite(value) or not 1 <= value <= 5000:
            raise ValueError(f'{label}: 1–5000 mm')
    if not isfinite(bleed) or not 0 <= bleed <= 50:
        raise ValueError('Spad: 0–50 mm')
    return {'w': round(float(width), 3), 'h': round(float(height), 3), 'mode': mode,
            'keep_orientation': bool(keep_orientation), 'bleed': round(float(bleed), 3)}


def resize_plan(trim_w: float, trim_h: float, spec: dict) -> tuple[float, float, tuple[float, float]]:
    """Nowy TrimBox strony (szer., wys.) i rozmiar wycinka źródła (szer., wys.) do przeskalowania — wszystko w mm,
    w widocznej orientacji strony. Wycinek jest wyśrodkowany w TrimBox źródła.

    H-39: „zachowaj orientację” zamienia szerokość z wysokością, gdy strona ma inną orientację niż wymiary docelowe;
    „niezależnie” rozciąga w obu osiach; „z kadrowaniem” zachowuje proporcje i przycina nadmiar równo z obu stron.
    """
    w, h = spec['w'], spec['h']
    mode = spec.get('mode', RESIZE_STRETCH)
    # Zachowanie orientacji ma sens tylko, gdy podano oba wymiary (w trybach jednego wymiaru drugi jest pomijany).
    if mode in (RESIZE_STRETCH, RESIZE_CROP) and spec.get('keep_orientation', True) \
            and abs(trim_w - trim_h) > 0.01 * max(trim_w, trim_h) \
            and abs(w - h) > 0.01 * max(w, h) and (trim_w > trim_h) != (w > h):
        w, h = h, w
    if mode == RESIZE_STRETCH:
        return w, h, (trim_w, trim_h)
    if mode == RESIZE_CROP:
        scale = max(w / trim_w, h / trim_h)
        return w, h, (w / scale, h / scale)
    if mode == RESIZE_WIDTH:
        return w, trim_h * w / trim_w, (trim_w, trim_h)
    if mode == RESIZE_HEIGHT:
        return trim_w * h / trim_h, h, (trim_w, trim_h)
    raise ValueError(f'Nieznany sposób zmiany rozmiaru: {mode}')


def apply(boxes: dict[str, list[float]], pages: list[int], box: Box | None) -> dict[str, list[float]]:
    """Nowe korekty pliku: ustaw ramkę na stronach `pages` albo (box=None) wróć do wartości z pliku."""
    result = dict(boxes)
    for page in pages:
        if box is None:
            result.pop(str(page), None)
        else:
            result[str(page)] = list(box)
    return result
