"""Rozmiar wynikowego PDF względem papieru, pola zadruku, chwytu i płyty — czysta logika (bez PyMuPDF i Tk).

Z okna głównego Impozycjonera 4 (E1, własne streszczenie): „Rozmiar wynikowego pdfa =” pole zadruku, pole zadruku
+ chwyt, rozmiar papieru, rozmiar papieru + chwyt, rozmiar płyty (oraz rozmiar poddruku i ±ZMB — tych nie ma);
płyta (maszyna): wymiary, „Punch” i chwyt („Punch”, „Grip”) liczony od dolnej krawędzi płyty; margines techniczny
(„na łapki”); „zmniejsz wynikowy rozmiar płyty o [pt]”.

Decyzje własne (H-54): krawędź chwytaków = dolna krawędź arkusza (tak jak widać go w programie); chwyt = pas pod
papierem (od krawędzi papieru do krawędzi płyty / strony PDF); na płycie papier jest wyśrodkowany w poziomie, a jego
dolna krawędź leży `chwyt` mm nad dolną krawędzią płyty; zmniejszenie płyty obcina stronę równo ze wszystkich stron;
margines „na łapki” to pas przy krawędzi chwytaków, na którym nie stawia się użytków (zmniejsza dostępną wysokość).
Wszystkie wymiary w mm, oś y w dół (jak w silniku).
"""
from __future__ import annotations

from dataclasses import dataclass

OUT_PAPER = 'Papier (arkusz)'
OUT_AREA = 'Pole zadruku'
OUT_PAPER_GRIP = 'Papier + chwyt'
OUT_AREA_GRIP = 'Pole zadruku + chwyt'
OUT_PLATE = 'Płyta'
OUTPUT_SIZES = (OUT_PAPER, OUT_AREA, OUT_PAPER_GRIP, OUT_AREA_GRIP, OUT_PLATE)
PT_MM = 25.4 / 72


@dataclass(frozen=True)
class OutputLayout:
    page_w: float
    page_h: float
    clip: tuple[float, float, float, float]      # fragment arkusza przenoszony na stronę (mm, układ arkusza)
    offset: tuple[float, float]                  # położenie lewego górnego rogu arkusza na stronie
    paper: tuple[float, float, float, float]     # papier na stronie (przycięty do strony) — na TrimBox

    @property
    def unchanged(self) -> bool:
        return self.clip[0] == 0 and self.clip[1] == 0 and self.offset == (0, 0) and \
            (self.page_w, self.page_h) == (self.clip[2], self.clip[3])


def print_area(sheet_w: float, sheet_h: float, margin_x: float, margin_y: float,
               tech_margin: float = 0.0) -> tuple[float, float, float, float]:
    """Pole zadruku na arkuszu: marginesy z każdej strony, przy dolnej krawędzi dodatkowo margines „na łapki”."""
    area = (margin_x, margin_y, sheet_w - margin_x, sheet_h - margin_y - tech_margin)
    if area[2] <= area[0] or area[3] <= area[1]:
        raise ValueError('Marginesy (z marginesem „na łapki”) są większe niż arkusz')
    return area


def layout(kind: str, sheet_w: float, sheet_h: float, margin_x: float, margin_y: float, tech_margin: float = 0.0,
           grip: float = 0.0, plate_w: float = 0.0, plate_h: float = 0.0, plate_reduce_pt: float = 0.0) -> OutputLayout:
    if kind not in OUTPUT_SIZES:
        raise ValueError(f'Rozmiar wynikowego PDF: {", ".join(OUTPUT_SIZES)}')
    for value, label in ((tech_margin, 'Margines „na łapki”'), (grip, 'Chwyt'), (plate_reduce_pt, 'Zmniejszenie płyty')):
        if not 0 <= value <= 500:
            raise ValueError(f'{label}: dozwolone 0–500')
    x0, y0, x1, y1 = print_area(sheet_w, sheet_h, margin_x, margin_y, tech_margin)   # sprawdza też „na łapki”
    if kind == OUT_PAPER:
        return OutputLayout(sheet_w, sheet_h, (0, 0, sheet_w, sheet_h), (0, 0), (0, 0, sheet_w, sheet_h))
    if kind == OUT_PAPER_GRIP:
        return OutputLayout(sheet_w, sheet_h + grip, (0, 0, sheet_w, sheet_h), (0, 0), (0, 0, sheet_w, sheet_h))
    if kind == OUT_AREA:
        return OutputLayout(x1 - x0, y1 - y0, (x0, y0, x1, y1), (-x0, -y0), (0, 0, x1 - x0, y1 - y0))
    if kind == OUT_AREA_GRIP:            # pole zadruku w poziomie, w pionie od pola zadruku do papieru + chwyt
        return OutputLayout(x1 - x0, sheet_h - y0 + grip, (x0, y0, x1, sheet_h), (-x0, -y0),
                            (0, 0, x1 - x0, sheet_h - y0))
    # płyta
    if plate_w <= 0 or plate_h <= 0:
        raise ValueError('Płyta: podaj szerokość i wysokość płyty')
    if sheet_w > plate_w + 1e-9 or sheet_h + grip > plate_h + 1e-9:
        raise ValueError(f'Papier {sheet_w:g} × {sheet_h:g} mm z chwytem {grip:g} mm nie mieści się na płycie '
                         f'{plate_w:g} × {plate_h:g} mm')
    cut = plate_reduce_pt * PT_MM / 2
    if 2 * cut >= min(plate_w, plate_h):
        raise ValueError('Zmniejszenie płyty jest większe niż płyta')
    page_w, page_h = plate_w - 2 * cut, plate_h - 2 * cut
    px, py = (plate_w - sheet_w) / 2 - cut, plate_h - grip - sheet_h - cut
    paper = (max(px, 0.0), max(py, 0.0), min(px + sheet_w, page_w), min(py + sheet_h, page_h))
    return OutputLayout(page_w, page_h, (0, 0, sheet_w, sheet_h), (px, py), paper)
