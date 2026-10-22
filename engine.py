"""ImpoCraft (dawniej Impozycjoner Studio) - vector PDF imposition engine.

Uses PDF form XObjects via PyMuPDF. No source pages are rasterized during export.
Units exposed to the operator are millimetres; PyMuPDF operates in points.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import islice
from math import floor, isfinite
from pathlib import Path
from collections import Counter
from typing import Iterator
import json
import zipfile

import marks as marks_rules
from app_info import APP_NAME, TITLE as APP_TITLE

import pymupdf as fitz

# Role labels are persisted in project files; keep them stable across releases.
ROLE_AUTO = 'Normalnie'
ROLE_FRONT = 'Przód'
ROLE_BACK = 'Tył sparowany'
ROLE_SHARED = 'Tył wspólny'
ROLE_SKIP = 'Pomiń'
PAGE_ROLES = (ROLE_AUTO, ROLE_FRONT, ROLE_BACK, ROLE_SHARED, ROLE_SKIP)

PT_PER_MM = 72.0 / 25.4


def pt(mm: float) -> float:
    return mm * PT_PER_MM


def mm(points: float) -> float:
    return points / PT_PER_MM


def media_rect(page: fitz.Page) -> fitz.Rect:
    """MediaBox in the same (unrotated MuPDF) coordinates as Trim/BleedBox.

    PyMuPDF exposes `Page.mediabox` in *PDF* coordinates, with the original
    vertical origin. CropBox, TrimBox and BleedBox use MuPDF coordinates where
    y=0 corresponds to the MediaBox's upper edge. Comparing them without
    normalising causes false TRIMBOX errors for non-zero MediaBox origins.

    The horizontal coordinates are already in the same space; only y shifts.
    This normalised rect can also be passed to Page.set_cropbox().
    """
    media = fitz.Rect(page.mediabox)
    return fitz.Rect(media.x0, 0, media.x1, media.height)


@dataclass
class Job:
    path: str
    copies: int = 1
    role: str = ROLE_AUTO
    page_roles: dict[str, str] = field(default_factory=dict)  # 1-based page numbers
    crop_x: float = 0.0  # mm: desired crop-centre displacement in source visual X
    crop_y: float = 0.0  # mm: desired crop-centre displacement in source visual Y
    # Korekta rozmiaru/położenia netto stron (page_boxes.py): {"nr strony": [z lewej, od góry, szer., wys.] mm}
    page_boxes: dict[str, list[float]] = field(default_factory=dict)
    # Zmiana rozmiaru stron (page_boxes.resize_spec): {"nr strony": {"w", "h", "mode", "keep_orientation", "bleed"}}
    page_sizes: dict[str, dict] = field(default_factory=dict)
    # Kolejność wierszy tabeli (page_rows.py, H-45): numery stron od 1, None = wakat; None = cały plik po kolei.
    pages: list[int | None] | None = None

    def role_for(self, zero_based_page: int) -> str:
        return self.page_roles.get(str(zero_based_page + 1), self.role)


@dataclass
class Settings:
    sheet_w: float = 450
    sheet_h: float = 320
    trim_w: float = 90
    trim_h: float = 50
    bleed: float = 2  # legacy/non-crop projects; crop derives it from gross and net
    source_w: float = 0  # 0 = automatically use PDF source TrimBox dimensions
    source_h: float = 0
    gross_w: float = 0   # 0 = legacy trim + 2 * bleed
    gross_h: float = 0
    auto_gross: bool = False  # legacy projects keep manually entered gross
    auto_source: bool = False  # legacy projects keep manually entered source dimensions
    margin_x: float = 6
    margin_y: float = 6
    gap_x: float = 5
    gap_y: float = 5
    rotation: str = "Auto"  # Auto, 0, 90
    columns: int = 0          # 0 = automatic
    rows: int = 0
    mode: str = "Jednostronnie"  # Jednostronnie | Dwustronnie | Broszura | Ekonomiczny
    flip: str = "Długa krawędź"
    verso_shift_x: float = 0.0  # mm in physical (unflipped) back PDF coordinates
    verso_shift_y: float = 0.0
    crop_marks: bool = True
    show_page_labels: bool = False
    scale_mode: str = "Bez skalowania"  # Bez skalowania | Kadruj 1:1 | Dopasuj | Wypełnij
    # Znaczniki wzorowane na Impozycjonerze 4 (marks.py). Wartości domyślne = zachowanie sprzed zmiany.
    mark_offset: float = 0.8      # mm: odstęp znaczników cięcia od krawędzi spadu
    mark_length: float = 3.0      # mm: długość kreski znacznika cięcia
    mark_width_pt: float = 0.25   # pt: grubość kreski znacznika cięcia
    # Pełne okno „Znaczniki netto” (marks.py, H-34, H-35); domyślnie wynik jak dotąd.
    mark_gd_eq_lp: bool = True    # GD = LP (mark_length dotyczy obu)
    mark_length_gd: float = 3.0   # mm: kreski pionowe, gdy GD ≠ LP
    mark_pages: str = 'Wszystkie'  # Wszystkie | Nieparzyste | Parzyste (strony pliku wynikowego)
    mark_first_sheet: bool = False
    mark_color: str = 'Czarny (dotychczasowy)'  # zob. marks.MARK_COLORS
    mark_skip_uses: bool = False  # nie rysuj kresek na brutto sąsiednich użytków
    mark_corners_on: bool = False  # zaznaczaj narożniki (kreski na linii cięcia, do środka użytku)
    mark_corner_len: float = 5.0  # mm, obcinane do połowy wymiaru użytku
    mark_corner_lg: bool = True
    mark_corner_pg: bool = True
    mark_corner_ld: bool = True
    mark_corner_pd: bool = True
    mark_center: bool = False     # zaznacz środek netto
    gutter_on: bool = False       # wycinka środkowa
    gutter_v: float = 0.0         # mm: szerokość wycinki pionowej (parzysta liczba kolumn)
    gutter_h: float = 0.0         # mm: szerokość wycinki poziomej (parzysta liczba wierszy)
    gutter_marks: bool = True     # rysuj znacznik w osi wycinki
    gutter_mark_length: float = 5.0  # mm; 0 = przez całe pole zadruku
    gutter_mark_pt: float = 0.25
    trim_crop: bool = False       # dodatkowe docięcie TrimBox („crop”)
    trim_crop_pt: float = 0.5     # pt: z lewej na stronach parzystych, z prawej na nieparzystych
    # Skalowanie z docinaniem (whitecrop.py): białe marginesy źródła nie są częścią grafiki.
    white_trim: bool = False      # przytnij białe marginesy wokół grafiki źródła przed skalowaniem
    white_level: int = 250        # próg bieli 1–255 (piksel jaśniejszy = biały)
    auto_orient: bool = False     # obracaj stronę o 90°, gdy jej orientacja różni się od użytku (H-37)
    # Znaczniki brutto (B), pasery (P) i opis impozycji (O) — marks.py, H-29…H-31.
    gross_marks: bool = False
    gross_mark_lp: float = 3.0    # mm: kreska pozioma
    gross_mark_gd: float = 3.0    # mm: kreska pionowa
    gross_mark_pt: float = 0.25
    gross_mark_pages: str = 'Wszystkie'  # Wszystkie | Nieparzyste | Parzyste
    gross_first_sheet: bool = False
    reg_marks: bool = False
    reg_variant: int = 1          # 1 = okrąg z krzyżem, 2 = dwa okręgi z krzyżem
    reg_diameter: float = 5.0
    reg_pt: float = 0.25
    reg_long: int = 1             # liczba paserów wzdłuż dłuższego boku arkusza
    reg_short: int = 1            # … wzdłuż krótszego boku
    reg_offset: float = 0.0       # mm od brutto użytków; 0 = automatycznie
    reg_edges_only: bool = False
    reg_beside_corners: bool = False
    slug_on: bool = False
    slug_file: bool = True
    slug_sheet: bool = True
    slug_print_area: bool = False
    slug_sizes: bool = True
    slug_datetime: bool = True
    slug_text: str = ''
    slug_size: int = 10           # 10 | 12 | 14 pt (zmniejszany do 6 pt, gdy się nie mieści)
    slug_font: str = 'Arial'      # Arial | Courier
    slug_top: bool = True
    slug_side: bool = False
    slug_sheet_word: str = 'Arkusz'
    slug_page_word: str = 'Strona'
    slug_roman: bool = False
    # Pasek kontroli koloru (K) — marks.py, H-32, H-33.
    strip_on: bool = False
    strip_top: bool = True
    strip_bottom: bool = False
    strip_gutter: bool = False
    strip_cell_w: float = 5.0
    strip_cell_h: float = 5.0
    strip_zones: int = 0          # 0 = cała dostępna długość
    strip_offset: float = 1.0     # mm od innych elementów (znaczników, użytków)
    strip_centered: bool = True
    strip_trim: float = 0.0       # 0 = pełna długość pola zadruku; X = pole zadruku minus X mm
    strip_colors: tuple = marks_rules.DEFAULT_STRIP_COLORS
    strip_pdf: str = ''           # pasek z pliku PDF zamiast rysowanego przez program
    # Znaczniki własne z plików U1L/U1R/U2L/U2R.pdf (U) — marks.own_mark_rect, H-40..H-42.
    own_marks: bool = False       # „dodaj znaczniki”
    own_folder: str = ''          # folder z plikami; puste = folder „znaczniki” w danych użytkownika
    own_1l: bool = True           # rysuj lewy / prawy na stronach nieparzystych (gdy plik istnieje)
    own_1r: bool = True
    own_2l: bool = True           # … na stronach parzystych
    own_2r: bool = True
    own_h1: float = 5.0           # mm od lewej/prawej krawędzi arkusza (strony nieparzyste)
    own_v1: float = 15.0          # mm od dolnej krawędzi do górnego narożnika znacznika
    own_h2: float = 5.0
    own_v2: float = 15.0
    # Pasery w polu brutto (S) — marks.gross_register_segments, H-44.
    reg2_on: bool = False
    reg2_v1: float = 5.0          # mm nad krawędzią brutto (długość kreski pionowej poza użytkami)
    reg2_v2: float = 5.0          # mm wzdłuż użytku (V1 + V2 = długość kreski pionowej)
    reg2_h1: float = 3.0          # mm od krawędzi brutto użytka do kreski pionowej
    reg2_h2: float = 3.0          # H1 + H2 = długość kreski poziomej
    reg2_pt: float = 0.25
    reg2_color: str = 'Rejestracyjny (100 % CMYK)'   # zob. marks.MARK_COLORS
    # Łączenie plików wynikowych (naming.OUTPUT_MODES, H-48): domyślnie jeden plik, jak dotąd.
    output_files: str = 'Jeden plik'
    # Autowypełnianie arkusza (autofill.py, H-49) — wartości domyślne = dotychczasowe wypełnianie.
    fill_pages: str = 'Wszystkimi'
    fill_corner: str = 'LG'
    fill_columns: bool = False
    fill_stack: bool = False
    fill_repeat: int = 1
    fill_even_last: bool = False

    def __post_init__(self):
        # JSON zapisuje krotki jako listy — wracamy do niezmiennej postaci (porównania, wartości domyślne).
        if isinstance(self.strip_colors, list):
            self.strip_colors = tuple(None if c is None else tuple(c) for c in self.strip_colors)


FILL_GROSS = 'Wypełnij ze spadem'  # grafika pokrywa netto + spad; spad powstaje z grafiki, nadmiar jest docinany
SCALE_MODES = ('Bez skalowania', 'Kadruj 1:1', 'Dopasuj', 'Wypełnij', FILL_GROSS)


@dataclass
class Project:
    settings: Settings = field(default_factory=Settings)
    jobs: list[Job] = field(default_factory=list)
    overrides: dict[str, dict] = field(default_factory=dict)  # "sheet:side:slot" -> source or blank


@dataclass(frozen=True)
class SourcePage:
    path: str
    index: int


@dataclass(frozen=True)
class Slot:
    x: float
    y: float
    w: float
    h: float
    rotation: int
    col: int
    row: int


@dataclass(frozen=True)
class Placement:
    source: SourcePage | None
    slot: Slot
    side: int


@dataclass(frozen=True)
class SheetSide:
    sheet_number: int
    side: int  # 0 recto / 1 verso
    placements: tuple[Placement, ...]


@dataclass(frozen=True)
class Geometry:
    cols: int
    rows: int
    rotation: int
    slots: tuple[Slot, ...]
    capacity: int
    gutter_x: float | None = None  # mm: oś wycinki pionowej, gdy została uwzględniona
    gutter_y: float | None = None  # mm: oś wycinki poziomej


def gross_dimensions(s: Settings) -> tuple[float, float]:
    """Physical size of a single imposed use, including symmetric bleed."""
    if s.scale_mode == 'Kadruj 1:1' and s.auto_gross:
        return s.trim_w + 2*s.bleed, s.trim_h + 2*s.bleed
    if s.scale_mode == 'Kadruj 1:1' and s.gross_w > 0 and s.gross_h > 0:
        return s.gross_w, s.gross_h
    return s.trim_w + 2*s.bleed, s.trim_h + 2*s.bleed


def bleed_for(s: Settings) -> float:
    """For three-size crop workflow, derive bleed from gross minus net."""
    if s.scale_mode == 'Kadruj 1:1' and s.auto_gross:
        return s.bleed
    if s.scale_mode == 'Kadruj 1:1' and s.gross_w > 0 and s.gross_h > 0:
        return (s.gross_w-s.trim_w)/2
    return s.bleed


def validate(settings: Settings):
    for key in ('sheet_w', 'sheet_h', 'trim_w', 'trim_h'):
        if not isfinite(getattr(settings, key)) or getattr(settings, key) <= 0:
            raise ValueError(f'{key}: wymiar musi być większy od zera')
    for key in ('source_w', 'source_h', 'gross_w', 'gross_h'):
        value = getattr(settings, key)
        if not isfinite(value) or value < 0:
            raise ValueError(f'{key}: wymiar musi być nieujemny')
    if (settings.source_w == 0) != (settings.source_h == 0):
        raise ValueError('Wprowadź oba wymiary oryginału PDF albo pozostaw oba jako automatyczne.')
    if (settings.gross_w == 0) != (settings.gross_h == 0):
        raise ValueError('Wprowadź szerokość i wysokość użytku ze spadami.')
    if settings.scale_mode == 'Kadruj 1:1' and not settings.auto_gross and settings.gross_w > 0:
        bx = (settings.gross_w - settings.trim_w)/2
        by = (settings.gross_h - settings.trim_h)/2
        if bx < -.001 or by < -.001:
            raise ValueError('Użytek ze spadami nie może być mniejszy niż format netto.')
        if abs(bx-by) > .02:
            raise ValueError('Spad ma być jednakowy z każdej strony: różnica użytek–netto musi być taka sama w obu wymiarach.')
    for key in ('bleed', 'margin_x', 'margin_y', 'gap_x', 'gap_y'):
        if not isfinite(getattr(settings, key)) or getattr(settings, key) < 0:
            raise ValueError(f'{key}: wartość nie może być ujemna')
    if settings.columns < 0 or settings.rows < 0:
        raise ValueError('Liczba kolumn/wierszy musi być dodatnia')
    if settings.rotation not in ('Auto', '0', '90', '180', '270'):
        raise ValueError('Nieznana orientacja')
    if settings.mode not in ('Jednostronnie', 'Dwustronnie', 'Broszura', 'Ekonomiczny'):
        raise ValueError('Nieznany tryb montażu')
    if settings.flip not in ('Długa krawędź', 'Krótka krawędź'):
        raise ValueError('Nieznana metoda odwracania')
    for key in ('verso_shift_x', 'verso_shift_y'):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError(f'{key}: nieprawidłowe przesunięcie rewersu')
        if abs(value * 10 - round(value * 10)) > 1e-6:
            raise ValueError('Kalibracja rewersu musi być ustawiona co 0,1 mm.')
        if abs(value) > 20.0:
            raise ValueError('Kalibracja rewersu może wynosić maksymalnie ±20 mm.')
    if settings.scale_mode not in SCALE_MODES:
        raise ValueError('Nieznany sposób skalowania PDF')
    if settings.white_trim and settings.scale_mode in ('Bez skalowania', 'Kadruj 1:1'):
        raise ValueError('Przycinanie białych marginesów działa tylko ze skalowaniem: '
                         'Dopasuj, Wypełnij albo Wypełnij ze spadem.')
    if settings.auto_orient and settings.scale_mode == 'Kadruj 1:1':
        raise ValueError('Obracanie stron do orientacji użytku nie działa z „Kadruj 1:1” — '
                         'wybierz Bez skalowania, Dopasuj, Wypełnij albo Wypełnij ze spadem.')
    if type(settings.white_level) is not int or not 1 <= settings.white_level <= 255:
        raise ValueError('Próg bieli musi być liczbą całkowitą 1–255.')
    for key, low, high, label in (('gross_mark_lp', 0, 50, 'Długość LP znacznika brutto [mm]'),
                                  ('gross_mark_gd', 0, 50, 'Długość GD znacznika brutto [mm]'),
                                  ('gross_mark_pt', 0.05, 5, 'Grubość znacznika brutto [pt]'),
                                  ('reg_diameter', 1, 30, 'Średnica pasera [mm]'),
                                  ('reg_pt', 0.05, 5, 'Grubość kreski pasera [pt]'),
                                  ('reg_offset', 0, 100, 'Odsunięcie pasera od brutto [mm]')):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
            raise ValueError(f'{label}: dozwolone {low:g}–{high:g}')
    if settings.gross_mark_pages not in ('Wszystkie', 'Nieparzyste', 'Parzyste'):
        raise ValueError('Znaczniki brutto: strony wszystkie, nieparzyste albo parzyste')
    for key, allowed, label in (('reg_variant', (1, 2), 'Wariant pasera'), ('reg_long', range(0, 21), 'Pasery na dłuższym boku'),
                                ('reg_short', range(0, 21), 'Pasery na krótszym boku'),
                                ('slug_size', (10, 12, 14), 'Stopień pisma opisu [pt]')):
        value = getattr(settings, key)
        if type(value) is not int or value not in allowed:
            raise ValueError(f'{label}: niedozwolona wartość {value!r}')
    for key, low, high, label in (('strip_cell_w', 1, 50, 'Szerokość kostki [mm]'),
                                  ('strip_cell_h', 1, 50, 'Wysokość kostki [mm]'),
                                  ('strip_offset', 0, 50, 'Odsunięcie paska [mm]'),
                                  ('strip_trim', 0, 3000, 'Skrócenie paska [mm]')):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
            raise ValueError(f'{label}: dozwolone {low:g}–{high:g}')
    if type(settings.strip_zones) is not int or not 0 <= settings.strip_zones <= 500:
        raise ValueError('Ilość stref paska: liczba całkowita 0–500 (0 = cała długość)')
    colors = settings.strip_colors
    if not isinstance(colors, (tuple, list)) or len(colors) != 12:
        raise ValueError('Pasek kontroli: potrzeba 12 kostek K1–K12')
    for color in colors:
        if color is not None and (len(color) != 4 or any(
                type(v) not in (int, float) or not 0 <= v <= 100 for v in color)):
            raise ValueError('Kolor kostki: cztery składowe CMYK 0–100 %')
    if settings.strip_on and not settings.strip_pdf and all(c is None for c in colors):
        raise ValueError('Sprawdź kolory kostek! Przynajmniej jedna powinna mieć zdefiniowany kolor.')
    if not isinstance(settings.strip_pdf, str):
        raise ValueError('Pasek z pliku PDF: ścieżka musi być tekstem')
    for key, label in (('reg2_v1', 'V1'), ('reg2_v2', 'V2'), ('reg2_h1', 'H1'), ('reg2_h2', 'H2')):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f'Pasery w polu brutto, {label} [mm]: dozwolone 0–100')
    if settings.reg2_v1 + settings.reg2_v2 <= 0 or settings.reg2_h1 + settings.reg2_h2 <= 0:
        raise ValueError('Pasery w polu brutto: V1 + V2 i H1 + H2 muszą być większe od 0')
    if type(settings.reg2_pt) not in (int, float) or not isfinite(settings.reg2_pt) or not 0.05 <= settings.reg2_pt <= 5:
        raise ValueError('Pasery w polu brutto, grubość [pt]: dozwolone 0,05–5')
    if settings.reg2_color not in marks_rules.MARK_COLORS:
        raise ValueError(f'Kolor paserów w polu brutto: {", ".join(marks_rules.MARK_COLORS)}')
    import naming
    naming.output_parts(settings.output_files)
    import autofill
    autofill.check(settings.fill_pages, settings.fill_corner, settings.fill_repeat)
    if not autofill_default(settings) and settings.mode not in ('Jednostronnie', 'Dwustronnie'):
        raise ValueError('Autowypełnianie działa w montażu jednostronnym i dwustronnym — przywróć ustawienia domyślne.')
    if settings.mode == 'Dwustronnie' and (settings.fill_pages != autofill.PAGES_ALL or settings.fill_even_last):
        raise ValueError('W montażu dwustronnym autowypełnianie bierze wszystkie strony w parach przód/tył — '
                         'wybór parzystych/nieparzystych i „parzyste na końcu” rozbiłyby pary.')
    if not isinstance(settings.own_folder, str):
        raise ValueError('Znaczniki własne: folder musi być tekstem')
    for key, label in (('own_h1', 'H strony nieparzystej'), ('own_v1', 'V strony nieparzystej'),
                       ('own_h2', 'H strony parzystej'), ('own_v2', 'V strony parzystej')):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value) or not -1000 <= value <= 3000:
            raise ValueError(f'Znaczniki własne, {label} [mm]: dozwolone -1000–3000')
    if settings.slug_font not in ('Arial', 'Courier'):
        raise ValueError('Krój pisma opisu: Arial albo Courier')
    for key in ('slug_text', 'slug_sheet_word', 'slug_page_word'):
        value = getattr(settings, key)
        if not isinstance(value, str) or len(value) > 200 or any(ord(c) < 32 for c in value):
            raise ValueError('Tekst opisu: do 200 znaków, bez znaków sterujących')
    if settings.mark_pages not in ('Wszystkie', 'Nieparzyste', 'Parzyste'):
        raise ValueError('Znaczniki cięcia: strony wszystkie, nieparzyste albo parzyste')
    if settings.mark_color not in marks_rules.MARK_COLORS:
        raise ValueError(f'Kolor znaczników cięcia: {", ".join(marks_rules.MARK_COLORS)}')
    for key, low, high, label in (('mark_length_gd', 0.1, 50, 'Długość GD znacznika cięcia [mm]'),
                                  ('mark_corner_len', 0.1, 500, 'Długość kreski narożnej [mm]')):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
            raise ValueError(f'{label}: dozwolone {low:g}–{high:g}')
    for key, low, high, label in (('mark_offset', 0, 50, 'Odstęp znaczników od użytków [mm]'),
                                  ('mark_length', 0.1, 50, 'Długość znacznika cięcia [mm]'),
                                  ('mark_width_pt', 0.05, 5, 'Grubość znacznika cięcia [pt]'),
                                  ('gutter_v', 0, 500, 'Szerokość wycinki pionowej [mm]'),
                                  ('gutter_h', 0, 500, 'Szerokość wycinki poziomej [mm]'),
                                  ('gutter_mark_length', 0, 500, 'Długość znacznika wycinki [mm]'),
                                  ('gutter_mark_pt', 0.05, 5, 'Grubość znacznika wycinki [pt]'),
                                  ('trim_crop_pt', 0, 20, 'Szerokość docięcia TrimBox [pt]')):
        value = getattr(settings, key)
        if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
            raise ValueError(f'{label}: dozwolone {low:g}–{high:g}')


def geometry(s: Settings) -> Geometry:
    """Find the most productive regular grid. Cell size includes bleed.

    Crop marks are an annotation outside trim and may be suppressed by clip at
    the edges of the sheet; gap and margins should allow for their length.
    """
    validate(s)
    available_w = s.sheet_w - 2 * s.margin_x
    available_h = s.sheet_h - 2 * s.margin_y
    if available_w <= 0 or available_h <= 0:
        raise ValueError('Marginesy są większe niż arkusz')
    candidates = []
    for angle in ([0, 90] if s.rotation == 'Auto' else [int(s.rotation)]):
        w, h = (s.trim_w, s.trim_h) if angle in (0, 180) else (s.trim_h, s.trim_w)
        cell_w, cell_h = w + 2*bleed_for(s), h + 2*bleed_for(s)
        on = s.gutter_on
        if on and (s.gutter_v or s.gutter_h):
            auto_cols = marks_rules.auto_count(available_w, cell_w, s.gap_x, s.gutter_v, on)
            auto_rows = marks_rules.auto_count(available_h, cell_h, s.gap_y, s.gutter_h, on)
        else:  # dokładnie dotychczasowy rachunek
            auto_cols = max(0, floor((available_w+s.gap_x+1e-8)/(cell_w+s.gap_x)))
            auto_rows = max(0, floor((available_h+s.gap_y+1e-8)/(cell_h+s.gap_y)))
        cols = s.columns if s.columns else auto_cols
        rows = s.rows if s.rows else auto_rows
        used_w = marks_rules.axis_length(cols, cell_w, s.gap_x, s.gutter_v, on)
        used_h = marks_rules.axis_length(rows, cell_h, s.gap_y, s.gutter_h, on)
        if cols < 1 or rows < 1 or used_w > available_w+1e-7 or used_h > available_h+1e-7:
            continue
        slots = []
        grid_x = s.margin_x + (available_w-used_w)/2
        grid_y = s.margin_y + (available_h-used_h)/2
        left = grid_x + bleed_for(s)
        top = grid_y + bleed_for(s)
        xs = marks_rules.axis_offsets(cols, cell_w, s.gap_x, s.gutter_v, on)
        ys = marks_rules.axis_offsets(rows, cell_h, s.gap_y, s.gutter_h, on)
        for row in range(rows):
            for col in range(cols):
                slots.append(Slot(left+xs[col], top+ys[row], w, h, angle, col, row))
        gutter_x = (marks_rules.gutter_center(grid_x, cols, cell_w, s.gap_x, s.gutter_v)
                    if marks_rules.gutter_applies(cols, s.gutter_v, on) else None)
        gutter_y = (marks_rules.gutter_center(grid_y, rows, cell_h, s.gap_y, s.gutter_h)
                    if marks_rules.gutter_applies(rows, s.gutter_h, on) else None)
        candidates.append(Geometry(cols, rows, angle, tuple(slots), cols*rows, gutter_x, gutter_y))
    if not candidates:
        raise ValueError('Użytki nie mieszczą się na arkuszu: zmniejsz wymiary/marginesy lub siatkę')
    return max(candidates, key=lambda g: (g.capacity, -(g.rotation == 90)))


def validate_job_roles(jobs: list[Job], documents: dict[str, fitz.Document]):
    """Validate page assignment even when the operator only requested preflight."""
    for job in jobs:
        if job.copies < 1:
            raise ValueError('Nakład musi być >= 1')
        if job.role not in PAGE_ROLES:
            raise ValueError(f'Nieznana rola pliku {Path(job.path).name}: {job.role}')
        count = len(documents[job.path])
        for number, role in job.page_roles.items():
            try:
                number_int = int(number)
            except (ValueError, TypeError):
                raise ValueError(f'Nieprawidłowy numer strony: {number!r}') from None
            if str(number_int) != number or number_int < 1 or number_int > count:
                raise ValueError(f'{Path(job.path).name}: strona {number!r} poza zakresem 1–{count}')
            if role not in PAGE_ROLES:
                raise ValueError(f'{Path(job.path).name}, strona {number}: nieznana rola {role!r}')
        try:
            job_rows(job, count)
        except ValueError as exc:
            raise ValueError(f'{Path(job.path).name}: {exc}') from None


def job_rows(job: Job, count: int) -> list[int | None]:
    """Wiersze pozycji: strony od 0 w kolejności tabeli, None = wakat (puste pole użytku)."""
    import page_rows
    return page_rows.sequence(job.pages, count)


def _page_refs(jobs: list[Job], documents: dict[str, fitz.Document]) -> Iterator[SourcePage]:
    """Single-sided and standalone export: only Pomiń changes source order."""
    validate_job_roles(jobs, documents)
    for job in jobs:
        rows = job_rows(job, len(documents[job.path]))
        for _ in range(job.copies):
            for i in rows:
                if i is None:
                    yield None                      # wakat — puste pole użytku
                elif job.role_for(i) != ROLE_SKIP:
                    yield SourcePage(job.path, i)


def _duplex_pairs(jobs: list[Job], documents: dict[str, fitz.Document]):
    """Build logical recto/verso pairs before putting them into sheet slots.

    - Normalnie: legacy consecutive pairs within each job/copy.
    - Przód: next Tył sparowany in global file/page order.
    - Tył wspólny: one PDF page repeated under all explicit fronts; any
      Normalnie pages are also interpreted as fronts when it exists.
    - Pomiń: excluded from both sides.

    Explicit backs never jump into a legacy Normalnie pair. Missing explicit
    backs are only allowed when *no* explicit backs were supplied (blank verso).
    """
    validate_job_roles(jobs, documents)
    shared_refs: set[SourcePage] = set()
    for job in jobs:
        for i in job_rows(job, len(documents[job.path])):
            if i is not None and job.role_for(i) == ROLE_SHARED:
                shared_refs.add(SourcePage(job.path, i))
    if len(shared_refs) > 1:
        raise ValueError('Może być tylko jedna strona oznaczona „Tył wspólny”.')
    shared = next(iter(shared_refs), None)

    pending: list[tuple[SourcePage, SourcePage | None] | SourcePage] = []
    explicit_fronts: list[SourcePage] = []
    explicit_backs: list[SourcePage] = []
    for job in jobs:
        for _ in range(job.copies):
            legacy: list[SourcePage] = []
            def flush_legacy():
                for k in range(0, len(legacy), 2):
                    pending.append((legacy[k], legacy[k+1] if k+1 < len(legacy) else None))
                legacy.clear()
            for i in job_rows(job, len(documents[job.path])):
                if i is None:                       # wakat: pusta strona w kolejnej parze przód/tył
                    if shared is None:
                        legacy.append(None)
                    else:
                        flush_legacy()
                        pending.append((None, None))
                    continue
                source = SourcePage(job.path, i)
                role = job.role_for(i)
                if role == ROLE_AUTO and shared is None:
                    legacy.append(source)
                    continue
                flush_legacy()
                if role == ROLE_SKIP or role == ROLE_SHARED:
                    continue
                if role == ROLE_BACK:
                    explicit_backs.append(source)
                elif role in (ROLE_FRONT, ROLE_AUTO):
                    pending.append(source)  # fill verso only after all files are read
                    explicit_fronts.append(source)
            flush_legacy()

    if shared is not None and not explicit_fronts:
        raise ValueError('Ustawiono wspólny tył, ale nie ma żadnych przodów do wydruku.')
    if explicit_backs and not explicit_fronts:
        raise ValueError('Są przypisane tyły, ale brakuje stron oznaczonych jako przody.')
    if len(explicit_backs) > len(explicit_fronts):
        raise ValueError(f'Za dużo sparowanych tyłów: {len(explicit_backs)} na {len(explicit_fronts)} przodów.')
    if 0 < len(explicit_backs) < len(explicit_fronts) and shared is None:
        raise ValueError(f'Tyłów jest {len(explicit_backs)}, przodów {len(explicit_fronts)}. '
                         'Dodaj brakujące tyły albo użyj „Tył wspólny”.')
    number = 0
    for pair in pending:
        if isinstance(pair, tuple):
            yield pair
        else:
            back = explicit_backs[number] if number < len(explicit_backs) else shared
            number += 1
            yield (pair, back)


def _flip_slot(slot: Slot, s: Settings) -> Slot:
    """Reorder back-side slots to match the physical sheet after a duplex flip."""
    landscape = s.sheet_w >= s.sheet_h
    flip_horizontal = (s.flip == 'Długa krawędź') != landscape
    if flip_horizontal:
        return Slot(s.sheet_w-slot.x-slot.w, slot.y, slot.w, slot.h,
                    slot.rotation, slot.col, slot.row)
    return Slot(slot.x, s.sheet_h-slot.y-slot.h, slot.w, slot.h,
                slot.rotation, slot.col, slot.row)


def _booklet_sides(jobs: list[Job], documents: dict[str, fitz.Document], s: Settings):
    """Saddle-stitched 2-up signature with blank-page padding to a multiple of 4."""
    if len(jobs) != 1:
        raise ValueError('Broszura 2-up: użyj jednego pliku PDF na raz')
    job = jobs[0]
    validate_job_roles(jobs, documents)
    if job.copies < 1:
        raise ValueError('Nakład musi być >= 1')
    refs = [None if i is None else SourcePage(job.path, i) for i in job_rows(job, len(documents[job.path]))
            if i is None or job.role_for(i) != ROLE_SKIP]
    if not refs:
        raise ValueError('Brak stron broszury po wykluczeniu stron z montażu')
    refs += [None]*((-len(refs)) % 4)
    n = len(refs)
    required_w = 2*(s.trim_w+2*bleed_for(s)) + s.gap_x
    required_h = s.trim_h+2*bleed_for(s)
    if required_w > s.sheet_w - 2*s.margin_x or required_h > s.sheet_h - 2*s.margin_y:
        raise ValueError('Broszura 2-up nie mieści się: zmień arkusz albo format strony')
    left = (s.sheet_w - required_w)/2 + bleed_for(s)
    top = (s.sheet_h - required_h)/2 + bleed_for(s)
    slots = [Slot(left, top, s.trim_w, s.trim_h, 0, 0, 0),
             Slot(left+s.trim_w+2*bleed_for(s)+s.gap_x, top,
                  s.trim_w, s.trim_h, 0, 1, 0)]
    for _ in range(job.copies):
        for i in range(n//4):
            # Outside of folded sheet: last/first, inside: second/penultimate.
            front = (refs[n-1-2*i], refs[2*i])
            back = (refs[2*i+1], refs[n-2-2*i])
            yield SheetSide(i+1, 0, tuple(Placement(p, slot, 0) for p, slot in zip(front, slots)))
            yield SheetSide(i+1, 1, tuple(Placement(p, slot, 1) for p, slot in zip(back, slots)))


ECONOMIC_MAX_SHEETS = 10000


def economic_demands(jobs: list[Job], documents: dict[str, fitz.Document]) -> dict[SourcePage, int]:
    """Requested physical impressions per individual PDF page (not per file).

    A multipage PDF with copies=100 means 100 of EACH non-skipped page.
    Multiple entries referencing the same page are combined deterministically.
    Duplex-only role markers are deliberately rejected for this single-sided mode.
    """
    validate_job_roles(jobs, documents)
    quantities: dict[SourcePage, int] = {}
    for job in jobs:
        for page in job_rows(job, len(documents[job.path])):
            if page is None:
                continue                            # wakat nie ma nakładu (H-45)
            role = job.role_for(page)
            if role not in (ROLE_AUTO, ROLE_SKIP):
                raise ValueError('Montaż ekonomiczny jest jednostronny. Usuń role przód/tył lub zmień tryb.')
            if role != ROLE_SKIP:
                ref = SourcePage(job.path, page)
                quantities[ref] = quantities.get(ref, 0) + job.copies
    if not quantities:
        raise ValueError('Brak stron do montażu ekonomicznego po pominięciu stron.')
    return quantities


def _economic_sides(jobs: list[Job], documents: dict[str, fitz.Document],
                    s: Settings) -> Iterator[SheetSide]:
    """Proportionally mix artworks with exact quantities and zero forced surplus.

    Each sheet is packed to capacity (except the last). We apportion the
    remaining quantity across the next sheet using largest remainders.
    This is a *single-gross-size, single-sided* layout, not mixed-size nesting.
    """
    remaining = economic_demands(jobs, documents)
    g = geometry(s)
    refs = tuple(remaining)  # keep input order for deterministic placements
    total = sum(remaining.values())
    minimum_sheets = (total + g.capacity - 1) // g.capacity
    if minimum_sheets > ECONOMIC_MAX_SHEETS:
        raise ValueError(f'Montaż ekonomiczny wymaga {minimum_sheets} arkuszy PDF. '
                         f'Limit bezpiecznego eksportu to {ECONOMIC_MAX_SHEETS}. '
                         'Podziel nakład na mniejsze partie.')
    sheet = 0
    while total:
        count = min(total, g.capacity)
        base = [count * remaining[ref] // total for ref in refs]
        # Hamilton apportionment; extra slots awarded by fractional remainder.
        unassigned = count - sum(base)
        ranked = sorted(range(len(refs)),
                        key=lambda i: (-(count * remaining[refs[i]] % total), i))
        for idx in ranked:
            if not unassigned:
                break
            if base[idx] < remaining[refs[idx]]:
                base[idx] += 1
                unassigned -= 1
        if unassigned or not sum(base) == count:
            raise RuntimeError('Nie udało się podzielić arkusza według nakładów.')
        placements = []
        for i, ref in enumerate(refs):
            placements.extend(ref for _ in range(base[i]))
            remaining[ref] -= base[i]
        sheet += 1
        yield SheetSide(sheet, 0, tuple(
            Placement(ref, g.slots[i], 0) for i, ref in enumerate(placements)))
        total -= count


@dataclass(frozen=True)
class EconomicLine:
    source: SourcePage
    requested: int
    planned: int

    @property
    def shortage(self) -> int:
        return max(0, self.requested-self.planned)

    @property
    def surplus(self) -> int:
        return max(0, self.planned-self.requested)


@dataclass(frozen=True)
class EconomicPattern:
    signature: tuple[SourcePage | None, ...]
    sheet_count: int
    first_sheet: int


@dataclass(frozen=True)
class EconomicReport:
    physical_sheets: int
    capacity: int
    filled_slots: int
    empty_slots: int
    lines: tuple[EconomicLine, ...]
    patterns: tuple[EconomicPattern, ...]

    @property
    def overproduction(self) -> int:
        return sum(line.surplus for line in self.lines)

    @property
    def shortage(self) -> int:
        return sum(line.shortage for line in self.lines)


def economic_report(project: Project, docs: dict[str, fitz.Document]) -> EconomicReport:
    """Audit ACTUAL final placements, including manual edits and blanks.

    The same project_sides iterator drives export, preview and this audit.
    """
    if project.settings.mode != 'Ekonomiczny':
        raise ValueError('Raport nakładów jest dostępny tylko w trybie Ekonomiczny.')
    expected = economic_demands(project.jobs, docs)
    actual: Counter[SourcePage] = Counter()
    patterns: dict[tuple[tuple, ...], list] = {}
    sheets = 0
    occupied = 0
    cap = geometry(project.settings).capacity
    for side in project_sides(project, docs):
        sheets += 1
        # Keep individual turns/displacements in the pattern key. Two sheets
        # with identical artworks but different manual geometry are NOT one template.
        pattern = tuple((p.source, round(p.slot.x, 4), round(p.slot.y, 4),
                         round(p.slot.w, 4), round(p.slot.h, 4), p.slot.rotation)
                        for p in side.placements)
        pattern += ((None,),)*(cap-len(pattern))
        if pattern not in patterns:
            refs = tuple(p.source for p in side.placements) + (None,)*(cap-len(side.placements))
            patterns[pattern] = [0, sheets, refs]
        patterns[pattern][0] += 1
        for p in side.placements:
            if p.source is not None:
                actual[p.source] += 1
                occupied += 1
    unexpected = [ref for ref in actual if ref not in expected]
    ordered = list(expected) + unexpected
    lines = tuple(EconomicLine(ref, expected.get(ref, 0), actual.get(ref, 0)) for ref in ordered)
    return EconomicReport(sheets, cap, occupied, sheets*cap-occupied, lines,
                          tuple(EconomicPattern(v[2], v[0], v[1]) for v in patterns.values()))

def autofill_default(s: Settings) -> bool:
    import autofill
    return autofill.is_default(s.fill_pages, s.fill_corner, s.fill_columns, s.fill_stack, s.fill_repeat,
                               s.fill_even_last)


def fill_slots(s: Settings, g: Geometry | None = None) -> list[Slot]:
    """Pola siatki w kolejności wypełniania (narożnik startowy, wiersze/kolumny); domyślnie jak dotąd."""
    import autofill
    g = g or geometry(s)
    order = autofill.slot_order([(slot.col, slot.row) for slot in g.slots], s.fill_corner, s.fill_columns)
    return [g.slots[i] for i in order]


def _filled_groups(units, s: Settings, capacity: int, page_number):
    import autofill
    if autofill_default(s):
        iterator = iter(units)
        while group := tuple(islice(iterator, capacity)):
            yield group
        return
    ordered = autofill.sequence(list(units), page_number, s.fill_pages, s.fill_even_last, s.fill_repeat)
    for group in autofill.sheets(ordered, capacity, s.fill_stack):
        yield tuple(group)


def plan_sides(jobs: list[Job], documents: dict[str, fitz.Document], s: Settings) -> Iterator[SheetSide]:
    if not jobs:
        return
    if s.mode == 'Broszura':
        yield from _booklet_sides(jobs, documents, s)
        return
    if s.mode == 'Ekonomiczny':
        yield from _economic_sides(jobs, documents, s)
        return
    g = geometry(s)
    slots = fill_slots(s, g)
    if s.mode == 'Jednostronnie':
        groups = _filled_groups(_page_refs(jobs, documents), s, g.capacity,
                                lambda ref: None if ref is None else ref.index + 1)
        for sheet_no, group in enumerate(groups, start=1):
            yield SheetSide(sheet_no, 0, tuple(Placement(p, slots[i], 0)
                                                for i, p in enumerate(group)))
    else:
        groups = _filled_groups(_duplex_pairs(jobs, documents), s, g.capacity,
                                lambda pair: None if pair[0] is None else pair[0].index + 1)
        for sheet_no, group in enumerate(groups, start=1):
            yield SheetSide(sheet_no, 0, tuple(Placement(pair[0], slots[i], 0)
                                                for i, pair in enumerate(group)))
            yield SheetSide(sheet_no, 1, tuple(Placement(pair[1], _flip_slot(slots[i], s), 1)
                                                for i, pair in enumerate(group)))


def _manual_key(side: SheetSide, index: int) -> str:
    return f'{side.sheet_number}:{side.side}:{index}'


def _slot_from_edit(base: Slot, entry: dict, settings: Settings) -> Slot:
    """Apply a rigid 0.1-mm transform to a single use, retaining its centre on rotation.

    Rotation is relative to automatic layout; 90/270 swap its net width/height.
    Only coordinates change: PDF source vectors and print size are preserved.
    """
    angle = entry.get('rotate', 0)
    dx = entry.get('dx', 0.0)
    dy = entry.get('dy', 0.0)
    if type(angle) is not int or angle not in (0, 90, 180, 270):
        raise ValueError('Ręczny obrót musi wynosić 0, 90, 180 lub 270°.')
    for name, value in (('X', dx), ('Y', dy)):
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError(f'Niepoprawne przesunięcie {name} użytku.')
        if abs(value * 10 - round(value * 10)) > 1e-6:
            raise ValueError(f'Przesunięcie {name} musi być wielokrotnością 0,1 mm.')
    w, h = (base.h, base.w) if angle in (90, 270) else (base.w, base.h)
    x = base.x + (base.w - w) / 2 + dx
    y = base.y + (base.h - h) / 2 + dy
    bleed = bleed_for(settings)
    if x < bleed - 1e-5 or y < bleed - 1e-5 or (x+w+bleed > settings.sheet_w+1e-5
            or y+h+bleed > settings.sheet_h+1e-5):
        raise ValueError('Użytek ze spadami wychodzi poza arkusz. Zmniejsz przesunięcie lub obrót.')
    return Slot(x, y, w, h, (base.rotation + angle) % 360, base.col, base.row)


def _complete_side(side: SheetSide, s: Settings, needed: int) -> SheetSide:
    """Add addressable empty slots to a partially filled sheet, without new pages."""
    if s.mode == 'Broszura':
        if needed > 2:
            raise ValueError('Broszura pozwala na dwa użytki w jednym arkuszu.')
        return side  # booklet already includes two cells (also when blank)
    g = geometry(s)
    if needed > g.capacity:
        raise ValueError(f'Pole ręcznego montażu {needed} wykracza poza siatkę {g.capacity}.')
    items = list(side.placements)
    slots = fill_slots(s, g)
    for i in range(len(items), needed):
        slot = slots[i]
        if side.side == 1 and s.mode == 'Dwustronnie':
            slot = _flip_slot(slot, s)
        items.append(Placement(None, slot, side.side))
    return SheetSide(side.sheet_number, side.side, tuple(items))


def apply_overrides(side: SheetSide, project: Project, sources: dict[str, fitz.Document],
                    *, full_grid: bool = False) -> SheetSide:
    """Apply identical layout edits to preview and export, even in initially empty cells."""
    prefix = f'{side.sheet_number}:{side.side}:'
    used_indices = []
    for key in project.overrides:
        if key.startswith(prefix):
            try:
                i = int(key[len(prefix):])
            except ValueError:
                raise ValueError(f'Niepoprawny klucz ręcznej pozycji: {key}') from None
            if i < 0:
                raise ValueError(f'Niepoprawny klucz ręcznej pozycji: {key}')
            used_indices.append(i)
    capacity = 2 if project.settings.mode == 'Broszura' else geometry(project.settings).capacity
    wanted = capacity if full_grid else max(len(side.placements), max(used_indices, default=-1)+1)
    side = _complete_side(side, project.settings, wanted)
    if not project.overrides:
        return side
    items = list(side.placements)
    for i, placement in enumerate(items):
        entry = project.overrides.get(_manual_key(side, i))
        if entry is None:
            continue
        if not isinstance(entry, dict):
            raise ValueError('Niepoprawne ręczne ustawienia użytku.')
        ref = placement.source
        if entry.get('blank', False):
            ref = None
        elif 'path' in entry or 'page' in entry:
            path = entry.get('path')
            page = entry.get('page')
            if path not in sources or type(page) is not int or not (0 <= page < len(sources[path])):
                raise ValueError(f'Ręcznie wybrana strona nie istnieje: {path}, {page}')
            ref = SourcePage(path, page)
        slot = _slot_from_edit(placement.slot, entry, project.settings)
        items[i] = Placement(ref, slot, placement.side)
    return SheetSide(side.sheet_number, side.side, tuple(items))


def calibrate_verso(side: SheetSide, s: Settings) -> SheetSide:
    """Move back-side content/marks in *physical sheet coordinates*.

    Slots have already been flipped and manually transformed. Apply calibration
    last and only once to the output geometry; source PDF vectors stay intact.
    Recto, booklet and standalone exports are intentionally unaffected.
    """
    if side.side != 1 or s.mode != 'Dwustronnie':
        return side
    x, y = s.verso_shift_x, s.verso_shift_y
    if not x and not y:
        return side
    b = bleed_for(s)
    items = []
    for p in side.placements:
        slot = p.slot
        shifted = Slot(slot.x + x, slot.y + y, slot.w, slot.h,
                       slot.rotation, slot.col, slot.row)
        if p.source is not None and (shifted.x-b < -1e-5 or shifted.y-b < -1e-5 or
                shifted.x+shifted.w+b > s.sheet_w+1e-5 or
                shifted.y+shifted.h+b > s.sheet_h+1e-5):
            raise ValueError('Kalibracja verso przesuwa użytek ze spadami poza arkusz. Zmniejsz offset X/Y.')
        items.append(Placement(p.source, shifted, p.side))
    return SheetSide(side.sheet_number, side.side, tuple(items))


def project_sides(project: Project, sources: dict[str, fitz.Document]):
    for side in plan_sides(project.jobs, sources, project.settings):
        edited = apply_overrides(side, project, sources)
        yield calibrate_verso(edited, project.settings)


def _edit_entry(project: Project, side: SheetSide, index: int) -> dict:
    if not 0 <= index < len(side.placements):
        raise IndexError('Nieprawidłowy numer użytku')
    return project.overrides.setdefault(_manual_key(side, index), {})


def assign_slot(project: Project, side: SheetSide, index: int, source: SourcePage | None):
    """Replace only the artwork; preserve per-cell rotation and movement."""
    entry = _edit_entry(project, side, index)
    entry.pop('path', None)
    entry.pop('page', None)
    entry.pop('blank', None)
    if source is None:
        entry['blank'] = True
    else:
        entry.update(path=source.path, page=source.index)


def swap_slots(project: Project, side: SheetSide, a: int, b: int):
    """Swap contents between two cells, keeping each cell's own transforms."""
    if not 0 <= a < len(side.placements) or not 0 <= b < len(side.placements):
        raise IndexError('Nieprawidłowy numer użytku')
    if a == b:
        return
    assign_slot(project, side, a, side.placements[b].source)
    assign_slot(project, side, b, side.placements[a].source)


def set_slot_transform(project: Project, side: SheetSide, index: int, *,
                       dx: float | None = None, dy: float | None = None,
                       rotate: int | None = None):
    """Set absolute displacement (0.1 mm grid) and relative right-angle rotation.

    Values replace existing transforms rather than accumulate; this prevents
    pointer-drag rounding drift. The active, unedited slot is not the transform
    origin: the original regular-grid slot is always the origin.
    """
    entry = _edit_entry(project, side, index)
    updated = dict(entry)
    if dx is not None:
        updated['dx'] = float(dx)
    if dy is not None:
        updated['dy'] = float(dy)
    if rotate is not None:
        updated['rotate'] = rotate
    # Validate the exact transform against the original regular grid.
    sources = None
    base = None
    if project.settings.mode == 'Broszura':
        # Booklet base uses the same relative rotation, but different base slots.
        # Recover the original from a per-cell editor's already-adjusted slot.
        base = _undo_slot_edit(side.placements[index].slot, entry)
    else:
        normal = fill_slots(project.settings)[index]   # indeks pola = kolejność wypełniania (autowypełnianie)
        if side.side == 1 and project.settings.mode == 'Dwustronnie':
            normal = _flip_slot(normal, project.settings)
        base = normal
    _slot_from_edit(base, updated, project.settings)
    project.overrides[_manual_key(side, index)] = updated


def _undo_slot_edit(slot: Slot, entry: dict) -> Slot:
    """Recover booklet's unmodified cell from its currently edited geometry."""
    rotate = entry.get('rotate', 0)
    w, h = (slot.h, slot.w) if rotate in (90, 270) else (slot.w, slot.h)
    x = slot.x - (w-slot.w)/2 - entry.get('dx', 0)
    y = slot.y - (h-slot.h)/2 - entry.get('dy', 0)
    return Slot(x, y, w, h, (slot.rotation-rotate) % 360, slot.col, slot.row)


def reset_slot(project: Project, side: SheetSide, index: int):
    """Restore fully automatic contents AND unmodified geometry for one cell."""
    if not 0 <= index < len(side.placements):
        raise IndexError('Nieprawidłowy numer użytku')
    project.overrides.pop(_manual_key(side, index), None)


def overlapping_uses(side: SheetSide, s: Settings) -> list[tuple[int, int]]:
    """Detect collisions of PRINTED gross rectangles (net use plus bleed)."""
    b = bleed_for(s)
    result = []
    for i, a in enumerate(side.placements):
        if a.source is None: continue
        ra = (a.slot.x-b,a.slot.y-b,a.slot.x+a.slot.w+b,a.slot.y+a.slot.h+b)
        for j in range(i+1,len(side.placements)):
            q=side.placements[j]
            if q.source is None: continue
            rb=(q.slot.x-b,q.slot.y-b,q.slot.x+q.slot.w+b,q.slot.y+q.slot.h+b)
            if min(ra[2],rb[2])-max(ra[0],rb[0]) > 1e-5 and min(ra[3],rb[3])-max(ra[1],rb[1]) > 1e-5:
                result.append((i,j))
    return result


def cut_marks_apply(s: Settings, page_number: int, sheet_number: int) -> bool:
    """Znaczniki cięcia na tej stronie pliku wynikowego? (E1: strony wszystkie/nieparzyste/parzyste, pierwszy arkusz)."""
    return (s.crop_marks and marks_rules.page_selected(page_number, s.mark_pages)
            and (not s.mark_first_sheet or sheet_number == 1))


def _draw_marks(page: fitz.Page, slot: Slot, s: Settings, blockers=()):
    """Create slim vector trim marks separated from bleed when space permits."""
    net = (slot.x, slot.y, slot.x + slot.w, slot.y + slot.h)
    # Do not print black into bleed. Each mark begins `mark_offset` (default 0.8 mm) after bleed.
    start = bleed_for(s) + s.mark_offset
    lp = s.mark_length
    gd = s.mark_length if s.mark_gd_eq_lp else s.mark_length_gd
    color = marks_rules.MARK_COLORS[s.mark_color]
    sheet = (0.0, 0.0, s.sheet_w, s.sheet_h)
    segments = marks_rules.cut_mark_segments(net, start, lp, gd, s.sheet_w, s.sheet_h)
    if s.mark_center:
        segments += marks_rules.center_segments(net, start, lp, gd, s.sheet_w, s.sheet_h)
    for segment in segments:
        # opcjonalnie: bez kresek na brutto sąsiednich użytków (pozostałe części kreski zostają)
        for (x0, y0), (x1, y1) in (marks_rules.clip_segment(segment, blockers, sheet) if blockers else [segment]):
            page.draw_line((pt(x0), pt(y0)), (pt(x1), pt(y1)), color=color, width=s.mark_width_pt)
    if s.mark_corners_on:
        corners = {name for name, on in zip(marks_rules.CORNERS, (s.mark_corner_lg, s.mark_corner_pg,
                                                                  s.mark_corner_ld, s.mark_corner_pd)) if on}
        for (x0, y0), (x1, y1) in marks_rules.corner_segments(net, s.mark_corner_len, corners):
            page.draw_line((pt(x0), pt(y0)), (pt(x1), pt(y1)), color=color, width=s.mark_width_pt)


def gutter_mark_lines(s: Settings) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Odcinki znaczników wycinki w mm ((x0, y0), (x1, y1)); pusta lista, gdy wycinki nie ma (H-23)."""
    if not (s.gutter_on and s.gutter_marks) or s.mode == 'Broszura':
        return []
    g = geometry(s)
    lines = []
    if g.gutter_x is not None:
        for a, b in marks_rules.gutter_mark_segments(g.gutter_x, s.margin_y, s.sheet_h - s.margin_y,
                                                     s.gutter_mark_length):
            lines.append(((g.gutter_x, a), (g.gutter_x, b)))
    if g.gutter_y is not None:
        for a, b in marks_rules.gutter_mark_segments(g.gutter_y, s.margin_x, s.sheet_w - s.margin_x,
                                                     s.gutter_mark_length):
            lines.append(((a, g.gutter_y), (b, g.gutter_y)))
    return lines


def gutter_notes(s: Settings) -> list[str]:
    """Wyjaśnienie, dlaczego włączona wycinka nie została uwzględniona (zamiast cichego pominięcia)."""
    if not s.gutter_on or s.mode == 'Broszura':
        return ['Wycinka nie dotyczy trybu Broszura.'] if s.gutter_on and (s.gutter_v or s.gutter_h) else []
    g = geometry(s)
    notes = []
    if s.gutter_v > 0 and g.gutter_x is None:
        notes.append(f'Wycinka pionowa pominięta: liczba kolumn ({g.cols}) nie jest parzysta.')
    if s.gutter_h > 0 and g.gutter_y is None:
        notes.append(f'Wycinka pozioma pominięta: liczba wierszy ({g.rows}) nie jest parzysta.')
    return notes


def _rotate_point(x: float, y: float, width: float, height: float,
                  angle: int) -> tuple[float, float]:
    """Coordinates relative to TrimBox; positive angles follow PDF view rotation."""
    if angle == 0:
        return x, y
    if angle == 90:
        return height-y, x
    if angle == 180:
        return width-x, height-y
    if angle == 270:
        return y, width-x
    raise ValueError('Obrót musi być wielokrotnością 90°')


def scaling_layout(source_w: float, source_h: float, target_w: float,
                   target_h: float, mode: str) -> tuple[float, float, float]:
    """Return uniform source-to-target scale and centered displacement.

    Arguments must use the same unit, e.g. all mm or all PDF points.
    The output is (scale, x_offset, y_offset) in those units. Positive
    offsets indicate letterboxing; negative offsets indicate cropping.
    """
    if min(source_w, source_h, target_w, target_h) <= 0:
        raise ValueError('Nieprawidłowy rozmiar strony do skalowania')
    if mode == 'Dopasuj':
        scale = min(target_w/source_w, target_h/source_h)
    elif mode in ('Wypełnij', FILL_GROSS):
        scale = max(target_w/source_w, target_h/source_h)
    elif mode in ('Bez skalowania', 'Kadruj 1:1'):
        scale = 1.0
    else:
        raise ValueError('Nieznany sposób skalowania PDF')
    return scale, (target_w-source_w*scale)/2, (target_h-source_h*scale)/2


def _inverse_rotate_point(x: float, y: float, width: float,
                          height: float, angle: int) -> tuple[float, float]:
    """Undo _rotate_point, all in unrotated source coordinates."""
    if angle == 0:
        return x, y
    if angle == 90:
        return y, height-x
    if angle == 180:
        return width-x, height-y
    if angle == 270:
        return width-y, x
    raise ValueError('Obrót musi być wielokrotnością 90°')


def crop_offsets(jobs: list[Job]) -> dict[str, tuple[float, float]]:
    """Shared per-path crop positions, including safety for duplicate source paths."""
    offsets = {}
    for job in jobs:
        x, y = float(job.crop_x), float(job.crop_y)
        if not isfinite(x) or not isfinite(y):
            raise ValueError(f'{Path(job.path).name}: niepoprawne przesunięcie kadru')
        if abs(x)>10000 or abs(y)>10000:
            raise ValueError(f'{Path(job.path).name}: przesunięcie kadru poza limitem')
        if job.path in offsets and offsets[job.path] != (x, y):
            raise ValueError(f'{Path(job.path).name}: ten sam PDF ma różne kadry w kilku pozycjach listy')
        offsets[job.path] = (x, y)
    return offsets


def crop_centre(source_w: float, source_h: float, gross_w: float, gross_h: float,
                x: float, y: float) -> None:
    """Reject missing real bleed caused by moving the crop out of source boundaries."""
    if abs(x) > (source_w-gross_w)/2 + .02 or abs(y) > (source_h-gross_h)/2 + .02:
        raise ValueError(f'Kadr + spad {gross_w:g} × {gross_h:g} mm wychodzi poza oryginał '
                         f'{source_w:.2f} × {source_h:.2f} mm przy X={x:g}, Y={y:g} mm.')


def orientation_differs(w: float, h: float, target_w: float, target_h: float, tolerance: float = 0.01) -> bool:
    """Czy strona i użytek mają różną orientację (pozioma/pionowa)? Prawie kwadratowe = bez obrotu (H-37)."""
    def kind(a: float, b: float) -> int:
        if abs(a - b) <= tolerance * max(a, b):
            return 0
        return 1 if a > b else -1
    page, use = kind(w, h), kind(target_w, target_h)
    return page != 0 and use != 0 and page != use


def _place_pdf(target: fitz.Page, p: SourcePage, slot: Slot, s: Settings,
               sources: dict[str, fitz.Document],
               offsets: dict[str, tuple[float, float]] | None = None):
    original = sources[p.path][p.index]
    trim = fitz.Rect(original.trimbox)
    media = media_rect(original)
    original_angle = original.rotation
    apparent_w, apparent_h = ((mm(trim.height), mm(trim.width))
                              if original_angle in (90, 270)
                              else (mm(trim.width), mm(trim.height)))
    if s.scale_mode == 'Kadruj 1:1' and not s.auto_source and s.source_w > 0:
        if abs(apparent_w - s.source_w) > .5 or abs(apparent_h - s.source_h) > .5:
            raise ValueError(
                f'{Path(p.path).name}, strona {p.index+1}: rzeczywisty oryginał '
                f'{apparent_w:.2f} × {apparent_h:.2f} mm różni się od ustawionego '
                f'{s.source_w:g} × {s.source_h:g} mm. Popraw rozmiar oryginału.')
    fits = abs(apparent_w-s.trim_w) <= 0.5 and abs(apparent_h-s.trim_h) <= 0.5
    if s.auto_orient:  # strona obrócona o 90° też pasuje (obrót nastąpi niżej)
        fits = fits or (abs(apparent_h-s.trim_w) <= 0.5 and abs(apparent_w-s.trim_h) <= 0.5)
    if s.scale_mode == 'Bez skalowania' and not fits:
        raise ValueError(
            f'{Path(p.path).name}, strona {p.index+1}: TrimBox {apparent_w:.2f} × '
            f'{apparent_h:.2f} mm nie odpowiada {s.trim_w:g} × {s.trim_h:g} mm. '
            'Wybierz skalowanie PDF (Dopasuj / Wypełnij) albo ustaw poprawny format.')
    if trim.is_empty or any(abs(a-b) > .05 for a,b in zip(trim, trim & media)):
        raise ValueError(f'{Path(p.path).name}: TrimBox poza MediaBox')

    if s.scale_mode == 'Kadruj 1:1':
        # The selected physical source PDF dimensions are NOT its finished dimensions.
        # Crop the centered target net rectangle at 100% with no geometric scaling.
        # The existing bleed-placement code below requests the margin outside it.
        target_w = pt(s.trim_h if original_angle in (90, 270) else s.trim_w)
        target_h = pt(s.trim_w if original_angle in (90, 270) else s.trim_h)
        gross_w, gross_h = gross_dimensions(s)
        if apparent_w + .02 < gross_w or apparent_h + .02 < gross_h:
            raise ValueError(
                f'{Path(p.path).name}, strona {p.index+1}: oryginał jest za mały '
                f'na użytek ze spadami {gross_w:g} × {gross_h:g} mm. '
                'Kadrowanie nie może utworzyć brakującej grafiki.')
        if target_w > trim.width + .02 or target_h > trim.height + .02:
            raise ValueError(
                f'{Path(p.path).name}, strona {p.index+1}: oryginał jest za mały '
                f'na kadrowanie 1:1 do {s.trim_w:g} × {s.trim_h:g} mm.')
        shift_x, shift_y = (offsets or {}).get(p.path, (0.0, 0.0))
        crop_centre(apparent_w, apparent_h, gross_w, gross_h, shift_x, shift_y)
        source_w, source_h = mm(trim.width), mm(trim.height)
        new_x, new_y = _inverse_rotate_point(
            apparent_w/2 + shift_x, apparent_h/2 + shift_y,
            source_w, source_h, original_angle)
        cx = trim.x0 + pt(new_x)
        cy = trim.y0 + pt(new_y)
        trim = fitz.Rect(cx-target_w/2, cy-target_h/2, cx+target_w/2, cy+target_h/2)

    if s.white_trim:
        # Białe marginesy wokół grafiki nie są częścią pracy: źródłem jest wykryty obszar treści.
        import whitecrop
        trim = whitecrop.content_rect(original, trim, s.white_level)
    bleedbox = fitz.Rect(original.bleedbox)
    limit = media
    if (s.scale_mode != 'Kadruj 1:1' and bleedbox.contains(trim)
            and bleedbox != trim and bleedbox != original.cropbox):
        limit = bleedbox & media
    angle = (original_angle + slot.rotation) % 360
    final_width = trim.width if angle in (0, 180) else trim.height
    final_height = trim.height if angle in (0, 180) else trim.width
    dest_w, dest_h = pt(slot.w), pt(slot.h)
    if s.auto_orient and orientation_differs(final_width, final_height, dest_w, dest_h):
        # Strona pozioma na pionowym użytku (lub odwrotnie): dodatkowe 90° (H-37), zamiast małej strony
        # z białymi polami (Dopasuj) albo obcięcia połowy grafiki (Wypełnij).
        angle = (angle + 90) % 360
        final_width, final_height = final_height, final_width
    if s.scale_mode == FILL_GROSS:
        # Grafika pokrywa cały użytek brutto (netto + spad): spad powstaje z samej grafiki,
        # nadmiar jest docinany do komórki — bez białych krawędzi.
        b = pt(bleed_for(s))
        factor, dx, dy = scaling_layout(final_width, final_height, dest_w + 2*b, dest_h + 2*b, FILL_GROSS)
        base_x = pt(slot.x) - b + dx
        base_y = pt(slot.y) - b + dy
        needed = 0.0
    else:
        factor, dx, dy = scaling_layout(final_width, final_height, dest_w, dest_h,
                                        ('Bez skalowania' if s.scale_mode == 'Kadruj 1:1' else s.scale_mode))
        # For exact-size source PDFs tolerate printer/export rounding <=0.5mm
        # without stretching artwork in opposite dimensions.
        base_x = pt(slot.x) + dx
        base_y = pt(slot.y) + dy

        # Required source bleed becomes larger when shrinking a source (e.g. A4
        # -> A6 needs 4mm source bleed to supply 2mm at output). Missing areas
        # stay white: the engine never invents an extended image.
        needed = pt(bleed_for(s))/factor
    desired = fitz.Rect(trim.x0-needed, trim.y0-needed,
                        trim.x1+needed, trim.y1+needed)

    # The 'Wypełnij' mode enlarges and crops to the target cell. Transform
    # target cell limits backwards, then clip the source to that range, so
    # content never bleeds into neighboring imposition cells.
    allowed_x0 = (pt(slot.x-bleed_for(s))-base_x)/factor
    allowed_y0 = (pt(slot.y-bleed_for(s))-base_y)/factor
    allowed_x1 = (pt(slot.x+slot.w+bleed_for(s))-base_x)/factor
    allowed_y1 = (pt(slot.y+slot.h+bleed_for(s))-base_y)/factor
    orig_corners = [_inverse_rotate_point(x, y, trim.width, trim.height, angle)
                    for x, y in ((allowed_x0, allowed_y0),
                                 (allowed_x0, allowed_y1),
                                 (allowed_x1, allowed_y0),
                                 (allowed_x1, allowed_y1))]
    bounds = fitz.Rect(trim.x0 + min(x for x, _ in orig_corners),
                       trim.y0 + min(y for _, y in orig_corners),
                       trim.x0 + max(x for x, _ in orig_corners),
                       trim.y0 + max(y for _, y in orig_corners))
    visible = desired & limit & bounds
    if s.trim_crop and s.trim_crop_pt > 0:
        # Docięcie TrimBox: krawędź liczona w orientacji strony widocznej dla operatora (po /Rotate).
        side_name = marks_rules.trim_crop_side(p.index + 1)
        tw, th = trim.width, trim.height
        aw, ah = (th, tw) if original_angle in (90, 270) else (tw, th)
        big = 1e6
        x0a, x1a = (s.trim_crop_pt, big) if side_name == 'left' else (-big, aw - s.trim_crop_pt)
        kept = [_inverse_rotate_point(xa, ya, tw, th, original_angle)
                for xa, ya in ((x0a, -big), (x1a, -big), (x0a, ah + big), (x1a, ah + big))]
        visible = visible & fitz.Rect(trim.x0 + min(x for x, _ in kept), trim.y0 + min(y for _, y in kept),
                                      trim.x0 + max(x for x, _ in kept), trim.y0 + max(y for _, y in kept))
    if visible.is_empty or visible.width <= 0 or visible.height <= 0:
        raise ValueError(f'{Path(p.path).name}: nieprawidłowy obszar po skalowaniu i kadrowaniu')

    corners = [(visible.x0, visible.y0), (visible.x1, visible.y0),
               (visible.x0, visible.y1), (visible.x1, visible.y1)]
    rotated = [_rotate_point(x-trim.x0, y-trim.y0, trim.width, trim.height, angle)
               for x, y in corners]
    box = fitz.Rect(base_x + min(x for x, _ in rotated)*factor,
                    base_y + min(y for _, y in rotated)*factor,
                    base_x + max(x for x, _ in rotated)*factor,
                    base_y + max(y for _, y in rotated)*factor)
    old_crop = fitz.Rect(original.cropbox)
    try:
        original.set_rotation(0)
        original.set_cropbox(media)
        target.show_pdf_page(box, sources[p.path], p.index,
                             clip=visible, rotate=angle, keep_proportion=True)
    finally:
        original.set_cropbox(old_crop)
        original.set_rotation(original_angle)


def render_side(side: SheetSide, sources: dict[str, fitz.Document], s: Settings,
                destination: fitz.Document | None = None,
                offsets: dict[str, tuple[float, float]] | None = None,
                output_name: str | None = 'montaz.pdf', page_number: int | None = None) -> fitz.Document:
    """page_number — numer strony w pliku wynikowym (podgląd renderuje pojedynczy arkusz do nowego dokumentu)."""
    out = destination if destination is not None else fitz.open()
    target = out.new_page(width=pt(s.sheet_w), height=pt(s.sheet_h))
    marks_here = cut_marks_apply(s, target.number + 1, side.sheet_number)
    blockers = _gross_rects(side, s, placed_only=True) if marks_here and s.mark_skip_uses else ()
    for item in side.placements:
        if item.source is not None:
            _place_pdf(target, item.source, item.slot, s, sources, offsets)
        if marks_here and item.source is not None:
            _draw_marks(target, item.slot, s, blockers)
        if s.show_page_labels:
            txt = f'{item.source.index+1}  ' if item.source else 'PUSTA  '
            target.insert_text((pt(item.slot.x+1), pt(item.slot.y+item.slot.h-1)),
                               txt, fontsize=6, color=(.3,.3,.3), overlay=True)
    for (x0, y0), (x1, y1) in gutter_mark_lines(s):
        target.draw_line((pt(x0), pt(y0)), (pt(x1), pt(y1)), color=(0, 0, 0), width=s.gutter_mark_pt)
    draw_sheet_marks(target, side, s, output_name=output_name)
    draw_own_marks(target, s, page_number or target.number + 1)
    return out


REGISTRATION = (1, 1, 1, 1)   # 100 % wszystkich farb CMYK (H-30)


def _gross_rects(side: SheetSide, s: Settings, placed_only: bool) -> list[tuple[float, float, float, float]]:
    """Prostokąty brutto: tylko zajęte użytki albo cała siatka arkusza (także puste pola ostatniego arkusza)."""
    b = bleed_for(s)
    slots = [p.slot for p in side.placements if p.source is not None or not placed_only]
    if not placed_only and s.mode != 'Broszura':
        slots += list(geometry(s).slots)
    return list(dict.fromkeys((sl.x - b, sl.y - b, sl.x + sl.w + b, sl.y + sl.h + b) for sl in slots))


def _marks_extent(s: Settings) -> float:
    """Jak daleko od brutto sięgają znaczniki cięcia (miejsce zajęte, którego nie zasłania opis)."""
    return s.mark_offset + s.mark_length if s.crop_marks else 0.0


def registration_offset(s: Settings) -> float:
    return s.reg_offset if s.reg_offset > 0 else _marks_extent(s) + 1.0


SLUG_FONTS = {'Arial': 'helv', 'Courier': 'cour'}


def slug_layout(s: Settings, grid, text: str):
    """Położenie opisu (H-31): lista (punkt bazowy mm, obrót, stopień pt); pusta, gdy opis się nie mieści."""
    if not text or grid is None:
        return []
    font = fitz.Font(SLUG_FONTS[s.slug_font])
    gap = 1.0
    reserved = _marks_extent(s) + gap
    if any(where == 'top' for where, *_ in strip_bands(s, grid)[0]):
        reserved += strip_size(s)[0] + s.strip_offset   # opis nad paskiem kontroli koloru (H-33)
    placements = []
    for where in (('top',) if s.slug_top else ()) + (('side',) if s.slug_side else ()):
        band = grid[1] - reserved if where == 'top' else grid[0] - reserved
        start = grid[0] if where == 'top' else grid[3]
        length = s.sheet_w - grid[0] - gap if where == 'top' else grid[3] - gap
        for size in range(s.slug_size, 5, -1):
            height = mm(size) * 1.2
            if band >= height and mm(font.text_length(text, fontsize=size)) <= length:
                baseline = grid[1] - reserved - mm(size) * 0.25 if where == 'top' else grid[0] - reserved - mm(size) * 0.25
                point = (start, baseline) if where == 'top' else (baseline, start)
                placements.append((point, 0 if where == 'top' else 90, size))
                break
    return placements


_strip_pdf_cache: dict[tuple, tuple[float, float]] = {}


def strip_size(s: Settings) -> tuple[float, float | None]:
    """(wysokość, szerokość albo None) paska w mm; dla paska z PDF — rozmiar pierwszej strony pliku."""
    if not s.strip_pdf:
        return s.strip_cell_h, None
    path = Path(s.strip_pdf)
    if not path.is_file():
        raise ValueError(f'Brak pliku paska kontroli: {s.strip_pdf}')
    key = (str(path), path.stat().st_mtime)
    if key not in _strip_pdf_cache:
        try:
            with fitz.open(str(path)) as doc:
                rect = doc[0].rect
        except Exception as exc:
            raise ValueError(f'Plik paska kontroli nie jest poprawnym PDF: {path.name}') from exc
        _strip_pdf_cache[key] = (mm(rect.height), mm(rect.width))
    return _strip_pdf_cache[key]


def strip_bands(s: Settings, grid) -> tuple[list[tuple[str, float, float, float]], list[str]]:
    """Położenia paska kontroli (H-33): [(gdzie, y0, x0, długość mm)] oraz uwagi, gdzie się nie zmieścił."""
    if not s.strip_on or grid is None or s.mode == 'Broszura':
        return [], []
    height, pdf_width = strip_size(s)
    length = s.sheet_w - 2*s.margin_x - s.strip_trim
    x0 = s.margin_x + (s.strip_trim / 2 if s.strip_centered else 0.0)
    if length <= 0 or (pdf_width is not None and pdf_width > length + 1e-6):
        return [], ['Pasek kontroli koloru jest dłuższy niż dostępne pole zadruku.']
    if pdf_width is not None:  # pasek z PDF: jedna kopia, wyśrodkowana albo od lewej
        x0, length = (x0 + (length - pdf_width) / 2 if s.strip_centered else x0), pdf_width
    reserved = _marks_extent(s) + s.strip_offset
    bands, notes = [], []
    if s.strip_top:
        y0 = grid[1] - reserved - height
        (bands.append(('top', y0, x0, length)) if y0 >= -1e-6
         else notes.append('Pasek kontroli koloru nie mieści się na górze arkusza.'))
    if s.strip_bottom:
        y0 = grid[3] + reserved
        (bands.append(('bottom', y0, x0, length)) if y0 + height <= s.sheet_h + 1e-6
         else notes.append('Pasek kontroli koloru nie mieści się na dole arkusza.'))
    if s.strip_gutter:
        g = geometry(s)
        if g.gutter_y is not None and s.gutter_h + 1e-6 >= height + 2*s.strip_offset:
            bands.append(('gutter', g.gutter_y - height/2, x0, length))
        else:
            notes.append('Pasek na wycince poziomej wymaga włączonej wycinki poziomej szerszej niż '
                         'kostka + 2 × odsunięcie (i parzystej liczby wierszy).')
    return bands, notes


def draw_color_strip(target: fitz.Page, s: Settings, grid):
    bands, _ = strip_bands(s, grid)
    height, pdf_width = strip_size(s)
    for _where, y0, x0, length in bands:
        if pdf_width is not None:
            with fitz.open(s.strip_pdf) as strip_doc:
                target.show_pdf_page(fitz.Rect(pt(x0), pt(y0), pt(x0 + length), pt(y0 + height)), strip_doc, 0)
            continue
        for offset, (c, m, y, k) in marks_rules.strip_cells(length, s.strip_cell_w, s.strip_colors,
                                                            s.strip_zones, s.strip_centered):
            target.draw_rect(fitz.Rect(pt(x0 + offset), pt(y0), pt(x0 + offset + s.strip_cell_w), pt(y0 + height)),
                             color=None, fill=(c / 100, m / 100, y / 100, k / 100), width=0)


OWN_MARKS_SUBFOLDER = 'znaczniki'
_own_mark_cache: dict[tuple, tuple[float, float]] = {}


def own_marks_folder(s: Settings) -> Path:
    """Folder z plikami U1L/U1R/U2L/U2R.pdf; domyślnie „znaczniki” w danych użytkownika (H-41)."""
    if s.own_folder:
        return Path(s.own_folder)
    import user_data
    return user_data.data_dir() / OWN_MARKS_SUBFOLDER


def own_mark_files(s: Settings) -> dict[str, Path]:
    """Pliki znaczników, które istnieją (brak pliku = znacznik nieaktywny, jak przełącznik w Imp4)."""
    folder = own_marks_folder(s)
    return {name: folder / f'{name}.pdf' for name in marks_rules.OWN_MARK_NAMES if (folder / f'{name}.pdf').is_file()}


def own_mark_size(path: Path) -> tuple[float, float]:
    key = (str(path), path.stat().st_mtime)
    if key not in _own_mark_cache:
        try:
            with fitz.open(str(path)) as doc:
                rect = doc[0].rect
        except Exception as exc:
            raise ValueError(f'Plik znacznika własnego nie jest poprawnym PDF: {path.name}') from exc
        _own_mark_cache[key] = (mm(rect.width), mm(rect.height))
    return _own_mark_cache[key]


def own_mark_placements(s: Settings, page_number: int) -> list[tuple[Path, tuple[float, float, float, float]]]:
    """[(plik, prostokąt mm)] znaczników własnych na stronie pliku wynikowego o danym numerze (od 1)."""
    if not s.own_marks:
        return []
    files = own_mark_files(s)
    odd = page_number % 2 == 1
    h, v = (s.own_h1, s.own_v1) if odd else (s.own_h2, s.own_v2)
    result = []
    for side in ('L', 'R'):
        name = marks_rules.own_mark_name(page_number, side)
        if not getattr(s, f'own_{name[1]}{side.lower()}') or name not in files:
            continue
        rect = marks_rules.own_mark_rect(side, own_mark_size(files[name]), h, v, s.sheet_w, s.sheet_h)
        result.append((files[name], rect))
    return result


def draw_own_marks(target: fitz.Page, s: Settings, page_number: int):
    for path, (x0, y0, x1, y1) in own_mark_placements(s, page_number):
        with fitz.open(str(path)) as doc:
            target.show_pdf_page(fitz.Rect(pt(x0), pt(y0), pt(x1), pt(y1)), doc, 0, keep_proportion=False)


def own_marks_notes(s: Settings) -> list[str]:
    """Uwagi preflight: brak plików, znacznik poza arkuszem."""
    if not s.own_marks:
        return []
    files = own_mark_files(s)
    folder = own_marks_folder(s)
    if not files:
        return [f'Znaczniki własne włączone, ale w folderze {folder} nie ma plików U1L/U1R/U2L/U2R.pdf.']
    notes = []
    wanted = [n for n in marks_rules.OWN_MARK_NAMES if getattr(s, f'own_{n[1]}{n[2].lower()}')]
    missing = [n for n in wanted if n not in files]
    if missing:
        notes.append(f'Znaczniki własne: brak plików {", ".join(m + ".pdf" for m in missing)} — nie będą rysowane.')
    for page in (1, 2):
        for path, (x0, y0, x1, y1) in own_mark_placements(s, page):
            if x0 < 0 or y0 < 0 or x1 > s.sheet_w or y1 > s.sheet_h:
                notes.append(f'Znacznik własny {path.stem} wystaje poza arkusz — sprawdź H i V.')
    return notes


def reg2_notes(s: Settings) -> list[str]:
    """Uwaga, gdy pasery w polu brutto wychodzą poza arkusz przy obecnej siatce."""
    if not s.reg2_on:
        return []
    g = geometry(s)
    b = bleed_for(s)
    slots = list(g.slots)
    if not slots:
        return []
    grid = marks_rules.bounding([(sl.x - b, sl.y - b, sl.x + sl.w + b, sl.y + sl.h + b) for sl in slots])
    for (x0, y0), (x1, y1) in marks_rules.gross_register_segments(grid, s.reg2_v1, s.reg2_v2, s.reg2_h1, s.reg2_h2):
        if min(x0, x1) < 0 or min(y0, y1) < 0 or max(x0, x1) > s.sheet_w or max(y0, y1) > s.sheet_h:
            return ['Pasery w polu brutto wychodzą poza arkusz — zmniejsz V1/H1/H2 albo zwiększ marginesy.']
    return []


def strip_notes(s: Settings) -> list[str]:
    if not s.strip_on or s.mode == 'Broszura':
        return []
    g = geometry(s)
    b = bleed_for(s)
    grid = marks_rules.bounding([(sl.x - b, sl.y - b, sl.x + sl.w + b, sl.y + sl.h + b) for sl in g.slots])
    bands, notes = strip_bands(s, grid)
    if not (s.strip_top or s.strip_bottom or s.strip_gutter):
        notes.append('Pasek kontroli koloru włączony, ale nie wybrano położenia (góra / dół / wycinka).')
    return notes


def _slug_for(side: SheetSide, s: Settings, output_name: str | None, when=None) -> str:
    from datetime import datetime
    gw, gh = gross_dimensions(s)
    return marks_rules.slug_text(
        file_name=output_name if s.slug_file else None,
        sheet_number=side.sheet_number if s.slug_sheet else 0, side=side.side,
        sheet_word=s.slug_sheet_word, page_word=s.slug_page_word, roman_pages=s.slug_roman,
        print_area=(s.sheet_w - 2*s.margin_x, s.sheet_h - 2*s.margin_y) if s.slug_print_area else None,
        sizes=(s.trim_w, s.trim_h, gw, gh, bleed_for(s)) if s.slug_sizes else None,
        when=(when or datetime.now()) if s.slug_datetime else None, extra=s.slug_text)


def draw_sheet_marks(target: fitz.Page, side: SheetSide, s: Settings, output_name: str | None = None, when=None):
    """Znaczniki brutto, pasery i opis impozycji na stronie arkusza (wszystkie domyślnie wyłączone)."""
    if not (s.gross_marks or s.reg_marks or s.reg2_on or s.slug_on or s.strip_on) or not side.placements:
        return
    sheet = (0.0, 0.0, s.sheet_w, s.sheet_h)
    all_gross = _gross_rects(side, s, placed_only=False)
    grid = marks_rules.bounding(all_gross)
    if s.strip_on:
        draw_color_strip(target, s, grid)
    if s.gross_marks and marks_rules.page_selected(target.number + 1, s.gross_mark_pages) and (
            not s.gross_first_sheet or side.sheet_number == 1):
        placed = _gross_rects(side, s, placed_only=True)
        for rect in placed:
            for segment in marks_rules.gross_mark_segments(rect, s.gross_mark_lp, s.gross_mark_gd):
                for (x0, y0), (x1, y1) in marks_rules.clip_segment(segment, placed, sheet):
                    target.draw_line((pt(x0), pt(y0)), (pt(x1), pt(y1)), color=(0, 0, 0, 1), width=s.gross_mark_pt)
    if s.reg_marks and grid is not None:
        r = s.reg_diameter / 2
        for cx, cy in marks_rules.registration_centres(grid, s.sheet_w, s.sheet_h, s.reg_diameter,
                                                        registration_offset(s), s.reg_long, s.reg_short,
                                                        s.reg_edges_only, s.reg_beside_corners):
            if not marks_rules.registration_visible((cx, cy), s.reg_diameter, all_gross, s.sheet_w, s.sheet_h):
                continue
            shape = target.new_shape()
            shape.draw_circle((pt(cx), pt(cy)), pt(r * (0.7 if s.reg_variant == 1 else 0.85)))
            if s.reg_variant == 2:
                shape.draw_circle((pt(cx), pt(cy)), pt(r * 0.45))
            shape.draw_line((pt(cx - r), pt(cy)), (pt(cx + r), pt(cy)))
            shape.draw_line((pt(cx), pt(cy - r)), (pt(cx), pt(cy + r)))
            shape.finish(color=REGISTRATION, fill=None, width=s.reg_pt)
            shape.commit()
    if s.reg2_on and grid is not None:
        color = marks_rules.MARK_COLORS[s.reg2_color]
        for (x0, y0), (x1, y1) in marks_rules.gross_register_segments(grid, s.reg2_v1, s.reg2_v2, s.reg2_h1,
                                                                       s.reg2_h2):
            target.draw_line((pt(x0), pt(y0)), (pt(x1), pt(y1)), color=color, width=s.reg2_pt)
    if s.slug_on:
        text = _slug_for(side, s, output_name, when)
        font = fitz.Font(SLUG_FONTS[s.slug_font])
        for (x, y), angle, size in slug_layout(s, grid, text):
            writer = fitz.TextWriter(target.rect)
            writer.append((pt(x), pt(y)), text, font=font, fontsize=size)
            morph = (fitz.Point(pt(x), pt(y)), fitz.Matrix(angle)) if angle else None  # od dołu do góry
            writer.write_text(target, color=(0, 0, 0, 1), morph=morph)


def slug_notes(s: Settings) -> list[str]:
    """Uwaga, gdy opis jest włączony, ale nie mieści się przy obecnych ustawieniach (jak komunikat Imp4)."""
    if not s.slug_on or s.mode == 'Broszura':
        return []
    if not (s.slug_top or s.slug_side):
        return ['Opis arkusza włączony, ale nie wybrano położenia (krawędź górna / boczna).']
    g = geometry(s)
    b = bleed_for(s)
    grid = marks_rules.bounding([(sl.x - b, sl.y - b, sl.x + sl.w + b, sl.y + sl.h + b) for sl in g.slots])
    sample = _slug_for(SheetSide(1, 0, ()), s, 'montaz.pdf')
    if not slug_layout(s, grid, sample):
        return ['Przy obecnych ustawieniach opis arkusza się nie mieści (za mały margines nad lub obok użytków).']
    return []


def visible_box_to_trimbox(page: fitz.Page, box) -> fitz.Rect:
    """Ramka (mm, widoczna strona po /Rotate, od lewego górnego rogu) → TrimBox w układzie MuPDF strony."""
    left, top, width, height = box
    visible = fitz.Rect(pt(left), pt(top), pt(left + width), pt(top + height))
    unrotated = visible * page.derotation_matrix
    unrotated.normalize()
    origin = fitz.Rect(page.cropbox).tl
    return unrotated + (origin.x, origin.y, origin.x, origin.y)


def apply_page_boxes(jobs: list[Job], sources: dict[str, fitz.Document]):
    """Korekty rozmiaru stron z projektu (H-38): TrimBox ustawiany tylko w pamięci — plik na dysku bez zmian."""
    seen: dict[str, dict] = {}
    for job in jobs:
        boxes = job.page_boxes or {}
        if job.path in seen and seen[job.path] != boxes:
            raise ValueError(f'{Path(job.path).name}: ten sam PDF ma różne korekty rozmiaru stron w kilku pozycjach listy')
        seen[job.path] = boxes
    import page_boxes as pb
    for path, boxes in seen.items():
        doc = sources[path]
        for key, box in boxes.items():
            number = int(key)
            if not 1 <= number <= len(doc):
                raise ValueError(f'{Path(path).name}: korekta dla nieistniejącej strony {key}')
            page = doc[number - 1]
            pb.check_box(box, mm(page.rect.width), mm(page.rect.height))
            trim = visible_box_to_trimbox(page, box) & fitz.Rect(page.mediabox)
            page.set_trimbox(trim)


def resized_document(doc: fitz.Document, sizes: dict[str, dict]) -> fitz.Document:
    """Kopia dokumentu w pamięci, w której wskazane strony są przeskalowane wektorowo (H-39).

    Nowa strona: TrimBox = zadany rozmiar, dookoła spad `bleed` wypełniony grafiką źródła spoza wycinka (jeśli jest);
    MediaBox = BleedBox = TrimBox + 2 × spad. Pozostałe strony są kopiowane bez zmian.
    """
    import page_boxes as pb
    out = fitz.open()
    for index, page in enumerate(doc):
        spec = sizes.get(str(index + 1))
        if not spec:
            out.insert_pdf(doc, from_page=index, to_page=index)
            continue
        origin = fitz.Rect(page.cropbox).tl
        to_page = (-origin.x, -origin.y, -origin.x, -origin.y)
        visible_trim = (fitz.Rect(page.trimbox) + to_page) * page.rotation_matrix
        visible_trim.normalize()
        visible_media = (fitz.Rect(page.mediabox) & fitz.Rect(page.cropbox)) + to_page
        visible_media = visible_media * page.rotation_matrix
        visible_media.normalize()
        new_w, new_h, (cut_w, cut_h) = pb.resize_plan(mm(visible_trim.width), mm(visible_trim.height), spec)
        sx, sy = pt(new_w) / pt(cut_w), pt(new_h) / pt(cut_h)
        bleed = pt(spec.get('bleed', 0.0))
        cx, cy = (visible_trim.x0 + visible_trim.x1) / 2, (visible_trim.y0 + visible_trim.y1) / 2
        cut = fitz.Rect(cx - pt(cut_w) / 2, cy - pt(cut_h) / 2, cx + pt(cut_w) / 2, cy + pt(cut_h) / 2)
        # Spad: tyle grafiki źródła poza wycinkiem, ile mieści się w spadzie po skalowaniu (nie więcej niż strona).
        shown = fitz.Rect(cut.x0 - bleed / sx, cut.y0 - bleed / sy, cut.x1 + bleed / sx, cut.y1 + bleed / sy)
        shown &= visible_media
        target = out.new_page(width=pt(new_w) + 2 * bleed, height=pt(new_h) + 2 * bleed)
        place = fitz.Rect(bleed + (shown.x0 - cut.x0) * sx, bleed + (shown.y0 - cut.y0) * sy,
                          bleed + (shown.x1 - cut.x0) * sx, bleed + (shown.y1 - cut.y0) * sy)
        clip = shown * page.derotation_matrix   # clip w nieobróconych współrzędnych strony źródłowej
        clip.normalize()
        target.show_pdf_page(place, doc, index, clip=clip, keep_proportion=False)
        r = target.rect  # od samej strony — bez błędów zaokrągleń przy spadzie 0
        target.set_trimbox(fitz.Rect(r.x0 + bleed, r.y0 + bleed, r.x1 - bleed, r.y1 - bleed))
        target.set_bleedbox(r)
    return out


def apply_page_sizes(jobs: list[Job], sources: dict[str, fitz.Document]):
    """Zmiana rozmiaru stron z projektu (tabela stron → „Zmień rozmiar zaznaczonych stron”), w pamięci."""
    seen: dict[str, dict] = {}
    for job in jobs:
        sizes = job.page_sizes or {}
        if job.path in seen and seen[job.path] != sizes:
            raise ValueError(f'{Path(job.path).name}: ten sam PDF ma różne zmiany rozmiaru stron w kilku pozycjach listy')
        seen[job.path] = sizes
    import page_boxes as pb
    for path, sizes in seen.items():
        if not sizes:
            continue
        doc = sources[path]
        for key, spec in sizes.items():
            if not 1 <= int(key) <= len(doc):
                raise ValueError(f'{Path(path).name}: zmiana rozmiaru dla nieistniejącej strony {key}')
            pb.resize_spec(spec['w'], spec['h'], spec.get('mode', pb.RESIZE_STRETCH),
                           spec.get('keep_orientation', True), spec.get('bleed', 0.0))
        resized = resized_document(doc, sizes)
        doc.close()
        sources[path] = resized


def open_sources(jobs: list[Job]) -> dict[str, fitz.Document]:
    sources = {}
    try:
        for job in jobs:
            if job.path not in sources:
                if not Path(job.path).is_file():
                    raise FileNotFoundError(f'Brak pliku: {job.path}')
                try:
                    doc = fitz.open(job.path)
                except Exception as exc:  # FileDataError itp. — plik nie jest PDF albo jest uszkodzony
                    raise ValueError(f'Plik nie jest poprawnym PDF albo jest uszkodzony: {job.path}') from exc
                if not doc.is_pdf or doc.needs_pass or len(doc) == 0:
                    doc.close()
                    raise ValueError(f'Nieobsługiwany lub zabezpieczony PDF: {job.path}')
                sources[job.path] = doc
        apply_page_boxes(jobs, sources)
        apply_page_sizes(jobs, sources)
        return sources
    except Exception:
        for doc in sources.values():
            doc.close()
        raise


CROP_NET = 'netto'
CROP_GROSS = 'brutto'
CROP_BLEED = 3.0   # „netto + 3 mm spad” (E1, okno korekty obszaru netto)


def crop_output_name(path: str, area: str) -> str:
    """Domyślna nazwa pliku po kadrowaniu: obok źródła, z dopiskiem _netto / _brutto (H-43)."""
    source = Path(path)
    return str(source.with_name(f'{source.stem}_{area}.pdf'))


def crop_to_file(job: Job, output: str, area: str = CROP_NET, bleed: float = CROP_BLEED) -> tuple[int, int]:
    """„Kadruj i zapisz do pliku” (E1/E2, H-43): nowy PDF, w którym każda strona ma rozmiar obszaru netto
    (TrimBox) albo netto + spad z każdej strony; treść wstawiana wektorowo z przycięciem.

    Uwzględnia korekty i zmiany rozmiaru stron z projektu (jak montaż). Grafiki poza stroną nie dorabia: brak spadu
    w pliku zostaje białym spadem. Zwraca (liczba stron, liczba stron bez pełnego spadu). Plik źródłowy bez zmian.
    """
    if area not in (CROP_NET, CROP_GROSS):
        raise ValueError('Kadrowanie: netto albo brutto')
    if type(bleed) not in (int, float) or not isfinite(bleed) or not 0 <= bleed <= 50:
        raise ValueError('Spad przy kadrowaniu: 0–50 mm')
    if Path(output).resolve() == Path(job.path).resolve():
        raise ValueError('Zapisz wynik do innego pliku niż źródłowy')
    extra = pt(bleed) if area == CROP_GROSS else 0.0
    sources = open_sources([Job(job.path, page_boxes=job.page_boxes, page_sizes=job.page_sizes)])
    doc = sources[job.path]
    out = fitz.open()
    short = 0
    try:
        for index, page in enumerate(doc):
            origin = fitz.Rect(page.cropbox).tl
            to_page = (-origin.x, -origin.y, -origin.x, -origin.y)
            trim = (fitz.Rect(page.trimbox) + to_page) * page.rotation_matrix
            trim.normalize()
            media = ((fitz.Rect(page.mediabox) & fitz.Rect(page.cropbox)) + to_page) * page.rotation_matrix
            media.normalize()
            wanted = fitz.Rect(trim.x0 - extra, trim.y0 - extra, trim.x1 + extra, trim.y1 + extra)
            shown = wanted & media
            if extra and not media.contains(wanted):
                short += 1
            target = out.new_page(width=wanted.width, height=wanted.height)
            place = shown - (wanted.x0, wanted.y0, wanted.x0, wanted.y0)
            clip = shown * page.derotation_matrix
            clip.normalize()
            target.show_pdf_page(place, doc, index, clip=clip, keep_proportion=False)
            r = target.rect
            target.set_trimbox(fitz.Rect(r.x0 + extra, r.y0 + extra, r.x1 - extra, r.y1 - extra))
            target.set_bleedbox(r)
        out.set_metadata({'title': f'{Path(job.path).stem} — kadrowanie {area}', 'creator': APP_TITLE})
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(output).with_name(Path(output).name + '.tmp')
        out.save(str(temporary), garbage=3, deflate=True)
        out.close()
        temporary.replace(output)
        return len(doc), short
    finally:
        if not out.is_closed:
            out.close()
        doc.close()


# „Wykonaj impozycję” w Impozycjonerze 4: wszystkie arkusze, tylko aktywny albo wszystkie oprócz aktywnego.
RUN_ALL = 'Wszystkie arkusze'
RUN_ACTIVE = 'Tylko aktywny arkusz'
RUN_EXCEPT_ACTIVE = 'Wszystkie oprócz aktywnego'
RUN_MODES = (RUN_ALL, RUN_ACTIVE, RUN_EXCEPT_ACTIVE)


def select_sides(sides, run_mode: str = RUN_ALL, active_sheet: int | None = None):
    """Filtruj strony arkuszy wg trybu wykonania. Arkusz = numer arkusza (recto i verso razem)."""
    if run_mode not in RUN_MODES:
        raise ValueError(f'Nieznany tryb wykonania impozycji: {run_mode}')
    if run_mode == RUN_ALL:
        yield from sides
        return
    if active_sheet is None or active_sheet < 1:
        raise ValueError('Wybierz aktywny arkusz w podglądzie')
    keep = (lambda n: n == active_sheet) if run_mode == RUN_ACTIVE else (lambda n: n != active_sheet)
    yield from (side for side in sides if keep(side.sheet_number))


METADATA_FIELDS = ('author', 'title', 'subject', 'keywords')


def output_metadata(output: str, fields: dict[str, str]) -> dict[str, str]:
    """Metadane wyniku jak w Ustawieniach Impozycjonera 4: Autor, Tytuł, Temat, Słowa kluczowe;
    puste pole = nazwa pliku wynikowego."""
    unknown = set(fields) - set(METADATA_FIELDS)
    if unknown:
        raise ValueError(f'Nieznane pole metadanych: {", ".join(sorted(unknown))}')
    name = Path(output).stem
    result = {key: (str(fields.get(key) or '').strip() or name) for key in METADATA_FIELDS}
    result['creator'] = APP_TITLE
    return result


def export_pdf(project: Project, output: str, metadata: dict[str, str] | None = None,
               run_mode: str = RUN_ALL, active_sheet: int | None = None, sheet_numbers: list | None = None,
               display_name: str | None = None):
    """Domyślnie (bez metadanych, wszystkie arkusze) zachowanie jest takie jak w 0.4.1.

    `sheet_numbers` (opcjonalnie) dostaje numer arkusza każdej zapisanej strony — dla podziału na pliki;
    `display_name` — nazwa pliku w opisie arkusza i metadanych, gdy zapis idzie do pliku tymczasowego.
    """
    shown = display_name or output
    validate(project.settings)
    if not project.jobs:
        raise ValueError('Dodaj co najmniej jeden plik PDF')
    sources = open_sources(project.jobs)
    offsets = crop_offsets(project.jobs)
    out = fitz.open()
    try:
        if project.settings.mode == 'Ekonomiczny':
            audit = economic_report(project, sources)
            if audit.overproduction or audit.shortage:
                raise ValueError(f'Ręczne zmiany naruszają nakłady: nadprodukcja {audit.overproduction}, '
                                 f'brakuje {audit.shortage}. Przywróć przypisania lub zamień użytki.')
        count = 0
        for side in select_sides(project_sides(project, sources), run_mode, active_sheet):
            render_side(side, sources, project.settings, out, offsets, Path(shown).name)
            if sheet_numbers is not None:
                sheet_numbers.append(side.sheet_number)
            count += 1
        if count == 0:
            raise ValueError('Brak stron do montażu' if run_mode == RUN_ALL
                             else f'Brak arkuszy do wykonania w trybie „{run_mode}”')
        out.set_metadata(output_metadata(shown, metadata) if metadata is not None else
                         {'title':f'{APP_NAME} - montaż PDF',
                          'creator':APP_TITLE})
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        out.save(output, garbage=3, deflate=True)
        return count
    finally:
        out.close()
        for doc in sources.values():
            doc.close()


def export_files(project: Project, output: str, metadata: dict[str, str] | None = None,
                 run_mode: str = RUN_ALL, active_sheet: int | None = None) -> list[str]:
    """Montaż zapisany wg „Łączenie plików wynikowych” (Settings.output_files, H-48).

    Jeden plik = `output` (jak dotąd); arkusze = `<nazwa>--arkusz-NN.pdf` (przód i tył arkusza razem);
    każda strona = `<nazwa>--NN.pdf`. Pliki obok `output`. Zwraca listę zapisanych plików.
    """
    import naming
    one, sheets, pages = naming.output_parts(project.settings.output_files)
    if one and not (sheets or pages):
        export_pdf(project, output, metadata, run_mode, active_sheet)
        return [output]
    target = Path(output)
    inputs = [job.path for job in project.jobs]
    numbers: list[int] = []
    combined = target.with_name(target.stem + '.tmp-montaz.pdf')
    export_pdf(project, str(combined), metadata, run_mode, active_sheet, sheet_numbers=numbers,
               display_name=str(target))
    written: list[str] = []
    try:
        with fitz.open(str(combined)) as doc:
            meta = doc.metadata

            def save(page_indexes: list[int], name: str):
                problem = naming.output_name_problem(name, inputs)
                if problem:
                    raise ValueError(problem)
                part = fitz.open()
                try:
                    for index in page_indexes:
                        part.insert_pdf(doc, from_page=index, to_page=index)
                    part.set_metadata(meta)
                    path = target.with_name(name)
                    part.save(str(path), garbage=3, deflate=True)
                finally:
                    part.close()
                written.append(str(path))

            if sheets:
                order = list(dict.fromkeys(numbers))
                for n, sheet in enumerate(order, start=1):
                    save([i for i, s in enumerate(numbers) if s == sheet],
                         naming.sheet_file_name(target.name, n, len(order)))
            if pages:
                for i in range(len(doc)):
                    save([i], naming.page_file_name(target.name, i + 1, len(doc)))
        if one:
            combined.replace(target)
            written.insert(0, str(target))
    finally:
        combined.unlink(missing_ok=True)
    return written


def export_pages(project: Project, output: str, metadata: dict[str, str] | None = None) -> int:
    """Produce one original logical page per output page at target net size.

    When bleed > 0, the physical MediaBox includes bleed and TrimBox is
    precisely the requested net format. No crop marks are added.
    """
    validate(project.settings)
    if not project.jobs:
        raise ValueError('Dodaj co najmniej jeden plik PDF')
    s = project.settings
    sources = open_sources(project.jobs)
    offsets = crop_offsets(project.jobs)
    out = fitz.open()
    try:
        for source in _page_refs(project.jobs, sources):
            w = s.trim_w + 2*bleed_for(s)
            h = s.trim_h + 2*bleed_for(s)
            page = out.new_page(width=pt(w), height=pt(h))
            slot = Slot(bleed_for(s), bleed_for(s), s.trim_w, s.trim_h, 0, 0, 0)
            if source is not None:          # wakat = pusta strona (numeracja kolejnych stron bez zmian)
                _place_pdf(page, source, slot, s, sources, offsets)
            if bleed_for(s):
                page.set_trimbox(fitz.Rect(pt(bleed_for(s)), pt(bleed_for(s)),
                                           pt(bleed_for(s)+s.trim_w), pt(bleed_for(s)+s.trim_h)))
                page.set_bleedbox(page.rect)
        if len(out) == 0:
            raise ValueError('Brak stron do eksportu')
        out.set_metadata(output_metadata(output, metadata) if metadata is not None else
                         {'title':f'{APP_NAME} - strony w formacie docelowym',
                          'creator':APP_TITLE})
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        out.save(output, garbage=3, deflate=True)
        return len(out)
    finally:
        out.close()
        for doc in sources.values():
            doc.close()


def preview(project: Project, pixels: int = 1200, index: int = 0):
    """Returns (PIL.Image, number represented). Lazy: only the requested sheet."""
    from PIL import Image
    validate(project.settings)
    sources = open_sources(project.jobs)
    offsets = crop_offsets(project.jobs)
    try:
        sides = project_sides(project, sources)
        selected = next(islice(sides, index, index+1), None)
        out = fitz.open()
        try:
            if selected is None:
                out.new_page(width=pt(project.settings.sheet_w), height=pt(project.settings.sheet_h))
            else:
                render_side(selected, sources, project.settings, out, offsets, page_number=index + 1)
            page = out[0]
            zoom = min(pixels/page.rect.width, pixels/page.rect.height, 2)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom,zoom), alpha=False)
            return Image.frombytes('RGB', (pix.width,pix.height),pix.samples), selected
        finally:
            out.close()
    finally:
        for doc in sources.values():
            doc.close()


def editor_preview(project: Project, pixels: int = 1200, index: int = 0):
    """Renders a full empty-cell grid for mouse editing, without adding blank sheets."""
    from PIL import Image
    validate(project.settings)
    sources = open_sources(project.jobs)
    offsets = crop_offsets(project.jobs)
    try:
        selected = next(islice(plan_sides(project.jobs, sources, project.settings), index, index+1), None)
        if selected is None:
            return None, None
        selected = calibrate_verso(apply_overrides(selected, project, sources, full_grid=True), project.settings)
        out = fitz.open()
        try:
            render_side(selected, sources, project.settings, out, offsets, page_number=index + 1)
            page = out[0]
            zoom = min(pixels/page.rect.width, pixels/page.rect.height, 2)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False)
            return Image.frombytes('RGB', (pix.width,pix.height),pix.samples), selected
        finally:
            out.close()
    finally:
        for d in sources.values(): d.close()


def save_project(project: Project, path: str):
    """.psimp = zip project. Original input PDFs are linked, not embedded."""
    root = Path(path).resolve().parent
    jobs = []
    for j in project.jobs:
        f = Path(j.path).resolve()
        try:
            file_path = str(f.relative_to(root))
        except ValueError:
            file_path = str(f)
        entry = {'path':file_path,'copies':j.copies,
                 'role':j.role,'page_roles':j.page_roles,
                 'crop_x':j.crop_x,'crop_y':j.crop_y}
        if j.page_boxes:  # pole opcjonalne: projekty bez korekt zapisują się jak dotąd
            entry['page_boxes'] = j.page_boxes
        if j.page_sizes:  # pole opcjonalne
            entry['page_sizes'] = j.page_sizes
        if j.pages is not None:  # pole opcjonalne: kolejność wierszy / wakaty
            entry['pages'] = list(j.pages)
        jobs.append(entry)
    relative_overrides = {}
    for key, entry in project.overrides.items():
        copied = dict(entry)
        if copied.get('path'):
            absolute = Path(copied['path']).resolve()
            try:
                copied['path'] = str(absolute.relative_to(root))
            except ValueError:
                copied['path'] = str(absolute)
        relative_overrides[key] = copied
    payload = {'format':'psimp','version':2, 'settings':asdict(project.settings), 'jobs':jobs, 'overrides':relative_overrides}
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('project.json', json.dumps(payload,ensure_ascii=False,indent=2))


def _load_pages(value):
    if value is None:
        return None
    if not isinstance(value, list) or any(v is not None and type(v) is not int for v in value):
        raise ValueError('Niepoprawna kolejność stron w projekcie')
    return list(value)


def load_project(path: str) -> Project:
    with zipfile.ZipFile(path, 'r') as z:
        data = json.loads(z.read('project.json'))
    if data.get('format') != 'psimp':
        raise ValueError('Nieznany format projektu')
    base = Path(path).resolve().parent
    settings = Settings(**data['settings'])
    jobs = [Job(path=str((base / j['path']).resolve()) if not Path(j['path']).is_absolute()
                else str(Path(j['path']).resolve()), copies=int(j['copies']),
                role=j.get('role', ROLE_AUTO), page_roles=dict(j.get('page_roles', {})),
                crop_x=float(j.get('crop_x', 0)), crop_y=float(j.get('crop_y', 0)),
                page_boxes={str(k): [float(v) for v in box] for k, box in dict(j.get('page_boxes', {})).items()},
                page_sizes={str(k): dict(spec) for k, spec in dict(j.get('page_sizes', {})).items()},
                pages=_load_pages(j.get('pages')))
            for j in data.get('jobs', [])]
    overrides = data.get('overrides', {})
    if not isinstance(overrides, dict):
        raise ValueError('Niepoprawny format ręcznych zmian arkusza')
    # Stored paths follow the same relative-path convention as source jobs.
    for entry in overrides.values():
        if isinstance(entry, dict) and entry.get('path') and not Path(entry['path']).is_absolute():
            entry['path'] = str((base / entry['path']).resolve())
    return Project(settings, jobs, overrides)


def source_summary(path: str) -> tuple[int, float, float]:
    with fitz.open(path) as doc:
        if not doc.is_pdf or doc.needs_pass or not len(doc):
            raise ValueError('Plik nie jest poprawnym niezabezpieczonym PDF')
        b = doc[0].trimbox
        return (len(doc), round(mm(b.height), 2), round(mm(b.width), 2)) if doc[0].rotation in (90,270) else (len(doc), round(mm(b.width),2), round(mm(b.height),2))
