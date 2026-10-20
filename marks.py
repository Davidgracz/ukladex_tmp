"""Reguły znaczników wzorowane na Impozycjonerze 4 — czysta logika (bez PyMuPDF i Tk).

Z tekstów okien oryginału (własne streszczenie, zob. docs/imp4-wersja-finalna.md):
  * Wycinka środkowa: szerokość pionowa i pozioma [mm], grubość znacznika [pt], znacznik o zadanej długości
    albo przez całe pole zadruku. Wycinka jest uwzględniana tylko, gdy to technicznie możliwe — pionowa wymaga
    parzystej liczby kolumn (pozioma, analogicznie, parzystej liczby wierszy).
  * Dodatkowe docięcie TrimBox („crop”): „włosowe” przycięcie o zadaną liczbę punktów — z lewej strony na stronach
    parzystych, z prawej na nieparzystych — aby ukryć skrawek sąsiedniej strony.
  * Dodatkowy odstęp znaczników od użytków [mm].

Decyzje własne (hipotezy, do sprawdzenia na działającym oryginale):
  H-22 wycinka zastępuje odstęp między środkowymi kolumnami (wierszami); przy automatycznej siatce wybieramy
       największą liczbę kolumn, która mieści się razem z wycinką — może to być liczba nieparzysta (bez wycinki);
  H-23 znacznik wycinki to linia w osi wycinki: dwa odcinki o zadanej długości od górnej i dolnej (lewej i prawej)
       krawędzi pola zadruku albo, przy długości 0, jedna linia przez całe pole zadruku;
  H-24 docięcie TrimBox usuwa z danej krawędzi strony także spad (strona jest przycięta tuż za linią cięcia);
  H-25 odstęp znaczników cięcia liczony od krawędzi spadu (brutto); domyślnie 0,8 mm jak dotąd.

Znaczniki brutto, pasery i opis impozycji (E1: okna „Parametry znaczników rozmiaru brutto”, „Parametry paserów”,
„Parametry opisu impozycji”, „Sposób oznaczania arkusza i strony”, „Informacje dodatkowe”):
  H-29 znaczniki brutto leżą na przedłużeniu krawędzi brutto, od narożnika na zewnątrz (LP poziomo, GD pionowo);
       części wchodzące na brutto innego użytku są pomijane; „strony” = numer strony w pliku wynikowym;
  H-30 pasery: środek w odległości H + promień od krawędzi brutto skrajnych użytków (H automatyczne = odstęp
       + długość znaczników cięcia + 1 mm); „X na boku” = liczba paserów rozłożonych równomiernie wzdłuż boku
       (bok dłuższy/krótszy wg arkusza); narożne: na przekątnej narożnika albo „przy narożnikach” — na obu bokach
       przy narożniku; paser na brutto użytku albo poza arkuszem jest pomijany; kolor = 100 % wszystkich farb CMYK;
  H-31 opis: jedna linia tekstu nad siatką użytków (krawędź górna) i/lub obrócona przy lewej krawędzi; gdy się
       nie mieści, stopień pisma maleje do 6 pt, a potem opis jest pomijany z uwagą; numeracja rzymska dotyczy
       oznaczenia strony arkusza.

Pasek kontroli koloru (E1: okno „Parametry pasków kontroli koloru”): 12 kostek K1–K12 o kolorach użytkownika
(co najmniej jedna musi mieć kolor), szerokość i wysokość kostki, „ilość stref”, odsunięcie paska od innych
elementów, położenie na górze / na dole arkusza / na wycince poziomej, pełna długość pola zadruku albo
„długość pola zadruku minus X”, pasek wyśrodkowany albo od lewej, alternatywnie pasek z pliku PDF.
  H-32 kostki z kolorem tworzą sekwencję powtarzaną cyklicznie na całej długości paska (tyle całych kostek,
       ile się mieści); „ilość stref” > 0 ogranicza pasek do tylu powtórzeń sekwencji; domyślne kolory K1–K12 są
       nasze (C, M, Y, K, CM, CY, MY, CMY i 50 % C, M, Y, K);
  H-33 pasek u góry leży nad znacznikami cięcia (odsunięcie od nich), u dołu — pod nimi, na wycince poziomej —
       w jej osi (gdy wycinka jest co najmniej o 2 × odsunięcie szersza od kostki); gdy nie ma miejsca, pasek
       nie jest rysowany i pojawia się uwaga; opis arkusza u góry przesuwa się nad pasek.
"""
from __future__ import annotations

from datetime import datetime
from math import floor


Rect = tuple[float, float, float, float]   # x0, y0, x1, y1 w mm
Segment = tuple[tuple[float, float], tuple[float, float]]
Cmyk = tuple[float, float, float, float]   # procenty 0–100

DEFAULT_STRIP_COLORS: tuple[Cmyk | None, ...] = (
    (100, 0, 0, 0), (0, 100, 0, 0), (0, 0, 100, 0), (0, 0, 0, 100),
    (100, 100, 0, 0), (100, 0, 100, 0), (0, 100, 100, 0), (100, 100, 100, 0),
    (50, 0, 0, 0), (0, 50, 0, 0), (0, 0, 50, 0), (0, 0, 0, 50))


def parse_cmyk(text: str) -> Cmyk | None:
    """„c/m/y/k” w procentach (np. „100/0/0/0”); puste = kostka bez koloru."""
    text = (text or '').strip()
    if not text:
        return None
    parts = text.replace(',', '.').replace(';', '/').replace(' ', '').split('/')
    if len(parts) != 4:
        raise ValueError(f'Kolor kostki „{text}”: podaj C/M/Y/K, np. 100/0/0/0')
    try:
        values = tuple(float(p) for p in parts)
    except ValueError:
        raise ValueError(f'Kolor kostki „{text}”: wartości muszą być liczbami') from None
    if any(not 0 <= v <= 100 for v in values):
        raise ValueError(f'Kolor kostki „{text}”: każda składowa 0–100 %')
    return values


def format_cmyk(color: Cmyk | None) -> str:
    return '' if color is None else '/'.join(f'{v:g}' for v in color)


def strip_cells(length: float, cell_w: float, colors, zones: int = 0,
                centered: bool = True) -> list[tuple[float, Cmyk]]:
    """Kostki paska (H-32): lista (przesunięcie od początku obszaru, kolor CMYK %)."""
    active = [c for c in colors if c is not None]
    if not active:
        raise ValueError('Sprawdź kolory kostek: przynajmniej jedna musi mieć zdefiniowany kolor.')
    if cell_w <= 0 or length <= 0:
        return []
    count = floor(length / cell_w + 1e-9)
    if zones > 0:
        count = min(count, zones * len(active))
    start = (length - count * cell_w) / 2 if centered else 0.0
    return [(start + i * cell_w, active[i % len(active)]) for i in range(count)]


def _overlaps(a: Rect, b: Rect) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6


def clip_segment(segment: Segment, blockers: list[Rect], sheet: Rect) -> list[Segment]:
    """Części poziomego/pionowego odcinka poza prostokątami `blockers` i w obrębie arkusza."""
    (x0, y0), (x1, y1) = segment
    horizontal = abs(y1 - y0) < 1e-9
    lo, hi = (min(x0, x1), max(x0, x1)) if horizontal else (min(y0, y1), max(y0, y1))
    fixed = y0 if horizontal else x0
    s_lo, s_hi = (sheet[0], sheet[2]) if horizontal else (sheet[1], sheet[3])
    if not ((sheet[1] if horizontal else sheet[0]) - 1e-9 <= fixed <= (sheet[3] if horizontal else sheet[2]) + 1e-9):
        return []
    parts = [(max(lo, s_lo), min(hi, s_hi))]
    for r in blockers:
        a, b = (r[0], r[2]) if horizontal else (r[1], r[3])
        across_lo, across_hi = (r[1], r[3]) if horizontal else (r[0], r[2])
        if not across_lo + 1e-9 < fixed < across_hi - 1e-9:
            continue
        parts = [piece for p0, p1 in parts
                 for piece in ((p0, min(p1, a)), (max(p0, b), p1)) if piece[1] - piece[0] > 1e-6]
    parts = [p for p in parts if p[1] - p[0] > 1e-6]
    return [((p0, fixed), (p1, fixed)) if horizontal else ((fixed, p0), (fixed, p1)) for p0, p1 in parts]


def gross_mark_segments(gross: Rect, lp: float, gd: float) -> list[Segment]:
    """Znaczniki brutto (H-29): z każdego narożnika brutto na zewnątrz — LP poziomo i GD pionowo."""
    x0, y0, x1, y1 = gross
    segments = []
    for cx, dx in ((x0, -1), (x1, 1)):
        for cy, dy in ((y0, -1), (y1, 1)):
            if lp > 0:
                segments.append(((cx, cy), (cx + dx * lp, cy)))
            if gd > 0:
                segments.append(((cx, cy), (cx, cy + dy * gd)))
    return segments


def page_selected(page_number: int, which: str) -> bool:
    """„Umieść na stronach”: wszystkich / nieparzystych / parzystych (numer strony pliku wynikowego, od 1)."""
    if which == 'Wszystkie':
        return True
    if which == 'Nieparzyste':
        return page_number % 2 == 1
    if which == 'Parzyste':
        return page_number % 2 == 0
    raise ValueError(f'Nieznany wybór stron: {which}')


def bounding(rects: list[Rect]) -> Rect | None:
    if not rects:
        return None
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def registration_centres(grid: Rect, sheet_w: float, sheet_h: float, diameter: float, offset: float,
                         n_long: int, n_short: int, edges_only: bool = False,
                         beside_corners: bool = False) -> list[tuple[float, float]]:
    """Środki paserów wokół siatki użytków (H-30). `grid` = obrys brutto użytków."""
    r = diameter / 2
    x0, y0, x1, y1 = grid
    top, bottom, left, right = y0 - offset - r, y1 + offset + r, x0 - offset - r, x1 + offset + r
    landscape = sheet_w >= sheet_h
    n_horizontal = n_long if landscape else n_short   # boki górny i dolny biegną wzdłuż szerokości arkusza
    n_vertical = n_short if landscape else n_long
    centres = []
    for i in range(1, n_horizontal + 1):
        x = x0 + (x1 - x0) * i / (n_horizontal + 1)
        centres += [(x, top), (x, bottom)]
    for i in range(1, n_vertical + 1):
        y = y0 + (y1 - y0) * i / (n_vertical + 1)
        centres += [(left, y), (right, y)]
    if not edges_only:
        if beside_corners:
            centres += [(x0 + r, top), (x1 - r, top), (x0 + r, bottom), (x1 - r, bottom),
                        (left, y0 + r), (left, y1 - r), (right, y0 + r), (right, y1 - r)]
        else:
            centres += [(left, top), (right, top), (left, bottom), (right, bottom)]
    return centres


def registration_visible(centre: tuple[float, float], diameter: float, blockers: list[Rect],
                         sheet_w: float, sheet_h: float) -> bool:
    """Paser rysujemy tylko w całości na arkuszu i poza brutto użytków."""
    r = diameter / 2
    box = (centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r)
    if box[0] < -1e-9 or box[1] < -1e-9 or box[2] > sheet_w + 1e-9 or box[3] > sheet_h + 1e-9:
        return False
    return not any(_overlaps(box, b) for b in blockers)


_ROMAN = ((1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),
          (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'))


def roman(number: int) -> str:
    if not 1 <= number <= 3999:
        raise ValueError('Numeracja rzymska: 1–3999')
    out = ''
    for value, letters in _ROMAN:
        while number >= value:
            out += letters
            number -= value
    return out


def slug_text(*, file_name: str | None, sheet_number: int, side: int,
              sheet_word: str = 'Arkusz', page_word: str = 'Strona', roman_pages: bool = False,
              print_area: tuple[float, float] | None = None,
              sizes: tuple[float, float, float, float, float] | None = None,
              when: datetime | None = None, extra: str = '') -> str:
    """Treść opisu impozycji (E1: nazwa pliku, oznaczenie arkusza i strony, informacje dodatkowe).

    `sizes` = (netto szer., netto wys., brutto szer., brutto wys., spad). Puste części są pomijane.
    """
    parts = []
    if file_name:
        parts.append(file_name)
    if sheet_number:
        page = side + 1
        parts.append(f'{sheet_word} {sheet_number} • {page_word} {roman(page) if roman_pages else page}'.strip())
    if print_area:
        parts.append(f'Pole zadruku {print_area[0]:g} × {print_area[1]:g} mm')
    if sizes:
        nw, nh, gw, gh, bleed = sizes
        parts.append(f'Netto {nw:g} × {nh:g} mm, brutto {gw:g} × {gh:g} mm, spad {bleed:g} mm')
    if when:
        parts.append(when.strftime('%Y-%m-%d %H:%M'))
    if extra.strip():
        parts.append(extra.strip())
    return '   •   '.join(parts)


def gutter_applies(count: int, width: float, enabled: bool = True) -> bool:
    """Czy wycinka w danej osi jest możliwa: włączona, szerokość > 0 i parzysta liczba (≥ 2) kolumn/wierszy."""
    return bool(enabled) and width > 0 and count >= 2 and count % 2 == 0


def axis_length(count: int, cell: float, gap: float, gutter: float = 0.0, enabled: bool = False) -> float:
    """Długość zajęta przez `count` użytków w jednej osi (z odstępami i ewentualną wycinką)."""
    if count < 1:
        return 0.0
    used = count * cell + (count - 1) * gap
    if gutter_applies(count, gutter, enabled):
        used += gutter - gap
    return used


def axis_offsets(count: int, cell: float, gap: float, gutter: float = 0.0, enabled: bool = False) -> list[float]:
    """Położenie początku każdego użytku względem początku siatki."""
    extra = gutter - gap if gutter_applies(count, gutter, enabled) else 0.0
    return [i * (cell + gap) + (extra if i >= count // 2 and extra else 0.0) for i in range(count)]


def auto_count(available: float, cell: float, gap: float, gutter: float = 0.0, enabled: bool = False) -> int:
    """Największa liczba użytków mieszcząca się w osi razem z wycinką (H-22)."""
    if cell <= 0:
        return 0
    upper = max(0, floor((available + gap + 1e-8) / (cell + gap))) + 1
    for count in range(upper, 0, -1):
        if axis_length(count, cell, gap, gutter, enabled) <= available + 1e-7:
            return count
    return 0


def gutter_center(start: float, count: int, cell: float, gap: float, gutter: float) -> float:
    """Oś wycinki (środek odstępu między środkowymi użytkami); `start` = początek siatki."""
    half = count // 2
    return start + half * cell + (half - 1) * gap + gutter / 2


def gutter_mark_segments(center: float, area_start: float, area_end: float,
                         length: float) -> list[tuple[float, float]]:
    """Odcinki znacznika wycinki wzdłuż osi (H-23): przy długości 0 — przez całe pole zadruku."""
    if area_end <= area_start:
        return []
    if length <= 0 or 2 * length >= area_end - area_start:
        return [(area_start, area_end)]
    return [(area_start, area_start + length), (area_end - length, area_end)]


def trim_crop_side(page_number: int) -> str:
    """Strona, z której przycina się TrimBox: parzyste — z lewej, nieparzyste — z prawej."""
    if page_number < 1:
        raise ValueError('Numer strony liczy się od 1')
    return 'left' if page_number % 2 == 0 else 'right'
