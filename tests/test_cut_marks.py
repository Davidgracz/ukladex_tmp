"""Znaczniki cięcia netto (gilotyna) — pełne okno „Parametry znaczników rozmiaru netto” Impozycjonera 4.

E1: długości LP i GD (przełącznik GD=LP), grubość, kolor, strony wszystkie/nieparzyste/parzyste, tylko pierwszy
arkusz, „zaznaczaj narożniki” LG/LD/PG/PD z długością obcinaną do połowy wymiaru użytku, „zaznacz środek netto”.
H-34, H-35 (marks.py). Domyślne ustawienia: kreski dokładnie jak dotąd.
"""
import pymupdf as fitz
import pytest

import marks
from engine import Job, Project, Settings, export_pdf, geometry, pt, validate

# --- czyste reguły -------------------------------------------------------------------------------

NET = (10.0, 20.0, 60.0, 50.0)   # użytek 50 × 30 mm


def test_cut_marks_lp_and_gd_lengths():
    segs = marks.cut_mark_segments(NET, 3, 4, 6, 200, 200)
    horizontal = [s for s in segs if s[0][1] == s[1][1]]
    vertical = [s for s in segs if s[0][0] == s[1][0]]
    assert len(horizontal) == 4 and len(vertical) == 4
    assert ((7, 20.0), (3, 20.0)) in horizontal                   # z lewej krawędzi: od 3 do 7 mm przed nią
    assert {abs(b[0] - a[0]) for a, b in horizontal} == {4}
    assert {abs(b[1] - a[1]) for a, b in vertical} == {6}
    assert ((60.0, 53), (60.0, 59)) in vertical


def test_cut_marks_outside_sheet_are_skipped_whole():
    segs = marks.cut_mark_segments((2.0, 20.0, 52.0, 50.0), 1, 3, 3, 200, 200)
    assert all(min(a[0], b[0]) >= 0 for a, b in segs)
    assert len(segs) == 6                                          # obie kreski LP z lewej poza arkuszem


def test_corner_segments_clamped_to_half_the_use():
    segs = marks.corner_segments(NET, 40, {'LG'})
    assert segs == [((10.0, 20.0), (35.0, 20.0)), ((10.0, 20.0), (10.0, 35.0))]   # ½ z 50 i ½ z 30
    both = marks.corner_segments(NET, 5, {'PD', 'LD'})
    assert ((60.0, 50.0), (55.0, 50.0)) in both and ((10.0, 50.0), (10.0, 45.0)) in both
    assert len(both) == 4
    assert marks.corner_segments(NET, 5, set()) == []


def test_center_segments():
    segs = marks.center_segments(NET, 3, 4, 5, 200, 200)
    assert ((7, 35.0), (3, 35.0)) in segs and ((35.0, 53), (35.0, 58)) in segs
    assert len(segs) == 4


# --- PDF ------------------------------------------------------------------------------------------

BASE = dict(sheet_w=160, sheet_h=110, trim_w=50, trim_h=30, bleed=2, margin_x=10, margin_y=10, gap_x=10,
            gap_y=10, rotation='0', columns=2, rows=2)


def make_pdf(folder, pages=4):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=pt(50), height=pt(30))
        page.draw_rect(page.rect, color=None, fill=(0.8, 0.9, 1))
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def lines(path, index=0):
    with fitz.open(path) as doc:
        return [(d, item) for d in doc[index].get_drawings() for item in d['items'] if item[0] == 'l']


def export(tmp_path, pages=4, **extra):
    out = tmp_path / 'o.pdf'
    export_pdf(Project(Settings(**{**BASE, **extra}), [Job(make_pdf(tmp_path, pages))]), str(out))
    return out


def test_default_marks_unchanged_count_and_style(tmp_path):
    found = lines(export(tmp_path))
    assert len(found) == 4 * 8                                     # 8 kresek na użytek, 4 użytki
    assert {round(d['width'], 2) for d, _ in found} == {0.25}
    assert {tuple(d['color']) for d, _ in found} == {(0.0, 0.0, 0.0)}


def test_gd_differs_from_lp(tmp_path):
    found = lines(export(tmp_path, mark_length=3, mark_gd_eq_lp=False, mark_length_gd=6))
    lengths = sorted({round(abs(p1.x - p0.x) + abs(p1.y - p0.y), 2) for _, (_, p0, p1) in found})
    assert lengths == [round(pt(3), 2), round(pt(6), 2)]


def test_pages_and_first_sheet(tmp_path):
    out = export(tmp_path, pages=8, mark_pages='Nieparzyste')
    assert lines(out, 0) and not lines(out, 1)
    out = export(tmp_path, pages=8, mark_first_sheet=True)
    assert lines(out, 0) and not lines(out, 1)


def test_corner_and_centre_marks(tmp_path):
    base = len(lines(export(tmp_path)))
    corners = lines(export(tmp_path, mark_corners_on=True, mark_corner_len=5, mark_corner_pg=False))
    assert len(corners) == base + 4 * 3 * 2                        # 3 narożniki × 2 kreski × 4 użytki
    centre = lines(export(tmp_path, mark_center=True))
    assert len(centre) == base + 4 * 4


def test_registration_colour_option_writes_cmyk(tmp_path):
    out = export(tmp_path, mark_color='Rejestracyjny (100 % CMYK)')
    with fitz.open(out) as doc:
        content = b''.join(doc.xref_stream(x) for x in doc[0].get_contents()).decode('latin-1')
    assert '1 1 1 1 K' in content                                 # kolor kreski CMYK (operator K)


def test_skip_uses_removes_marks_over_neighbours(tmp_path):
    # odstęp 3 mm < spad 2 mm + odstęp 0,8 + długość 3 → kreski wchodzą na brutto sąsiada
    tight = dict(gap_x=3, gap_y=3)
    s = Settings(**{**BASE, **tight})
    g = geometry(s)
    gross = [(sl.x - 2, sl.y - 2, sl.x + sl.w + 2, sl.y + sl.h + 2) for sl in g.slots]

    def on_neighbour(found):
        hits = 0
        for _, (_, p0, p1) in found:   # próbki co 1/20 długości kreski, nie tylko jej środek
            for t in (i / 20 for i in range(21)):
                mx = (p0.x + (p1.x - p0.x) * t) * 25.4 / 72
                my = (p0.y + (p1.y - p0.y) * t) * 25.4 / 72
                hits += any(r[0] + .02 < mx < r[2] - .02 and r[1] + .02 < my < r[3] - .02 for r in gross)
        return hits
    assert on_neighbour(lines(export(tmp_path, **tight))) > 0
    assert on_neighbour(lines(export(tmp_path, **tight, mark_skip_uses=True))) == 0


def test_invalid_values():
    for bad in ({'mark_pages': 'Co drugą'}, {'mark_color': 'Złoty'}, {'mark_length_gd': 0},
                {'mark_corner_len': 0}):
        with pytest.raises(ValueError):
            validate(Settings(**bad))
