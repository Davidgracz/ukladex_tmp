"""Pasery w polu brutto (S) — okno „Parametry paserów w polu brutto” Impozycjonera 4.

E1: V1 — długość znacznika pionowego nad pierwszym użytkiem, V1 + V2 — długość znacznika pionowego; H1 — odległość
pionowego znacznika od krawędzi brutto użytka, H1 + H2 — długość znacznika poziomego; grubość [pt]; kolor.
Decyzje własne: H-44 (położenie przy czterech narożnikach siatki brutto, lustrzane odbicia), OQ-18.
"""
import pymupdf as fitz
import pytest

import marks
from engine import (Job, Project, Settings, export_pdf, geometry, load_project, mm, pt, reg2_notes, save_project,
                    validate)

# --- czyste reguły -------------------------------------------------------------------------------

def test_segments_top_left_and_mirrors():
    seg = marks.gross_register_segments((20, 30, 120, 90), v1=5, v2=4, h1=3, h2=2)
    assert len(seg) == 8
    # lewy górny: pionowa 3 mm od krawędzi, 5 mm nad i 4 mm wzdłuż; pozioma od krawędzi 5 mm (H1 + H2) na zewnątrz
    assert seg[0] == ((17, 25), (17, 34)) and seg[1] == ((20, 30), (15, 30))
    assert seg[2] == ((17, 95), (17, 86)) and seg[3] == ((20, 90), (15, 90))          # lewy dolny
    assert seg[4] == ((123, 25), (123, 34)) and seg[5] == ((120, 30), (125, 30))      # prawy górny
    assert seg[6] == ((123, 95), (123, 86)) and seg[7] == ((120, 90), (125, 90))      # prawy dolny


# --- silnik i PDF --------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=2, margin_x=20, margin_y=25, gap_x=6,
            gap_y=6, rotation='0', columns=2, rows=2, crop_marks=False)


def make_pdf(folder, pages=4):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40)).insert_text((10, 20), f'p{i + 1}')
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def lines(path):
    with fitz.open(path) as doc:
        result = []
        for drawing in doc[0].get_drawings():
            for item in drawing['items']:
                if item[0] == 'l':
                    result.append((tuple(round(mm(v), 2) for v in (item[1].x, item[1].y, item[2].x, item[2].y)),
                                   drawing.get('color'), round(drawing.get('width') or 0, 2)))
        return result


def test_drawn_in_registration_colour_at_grid_corners(tmp_path):
    s = Settings(**BASE, reg2_on=True, reg2_v1=5, reg2_v2=4, reg2_h1=3, reg2_h2=2, reg2_pt=0.5)
    out = tmp_path / 'r.pdf'
    export_pdf(Project(s, [Job(make_pdf(tmp_path))]), str(out))
    found = lines(out)
    g = geometry(s)
    grid = marks.bounding([(sl.x - 2, sl.y - 2, sl.x + sl.w + 2, sl.y + sl.h + 2) for sl in g.slots])
    expected = {tuple(round(v, 2) for v in (a[0], a[1], b[0], b[1]))
                for a, b in marks.gross_register_segments(grid, 5, 4, 3, 2)}
    assert {c for c, _, _ in found} == expected
    assert all(width == 0.5 for _, _, width in found)
    with fitz.open(out) as doc:
        stream = doc[0].read_contents().decode('latin-1')
    assert '1 1 1 1 K' in stream                                     # kolor rejestracyjny CMYK 100 %


def test_off_by_default(tmp_path):
    out = tmp_path / 'o.pdf'
    export_pdf(Project(Settings(**BASE), [Job(make_pdf(tmp_path))]), str(out))
    assert lines(out) == []


def test_validation_and_notes():
    for bad in (dict(reg2_v1=-1), dict(reg2_h2=101), dict(reg2_v1=0, reg2_v2=0), dict(reg2_h1=0, reg2_h2=0),
                dict(reg2_pt=0), dict(reg2_color='zielony'), dict(reg2_v2='5')):
        with pytest.raises(ValueError):
            validate(Settings(**BASE, **bad))
    assert reg2_notes(Settings(**BASE)) == []
    assert reg2_notes(Settings(**BASE, reg2_on=True)) == []
    tight = Settings(**BASE, reg2_on=True, reg2_v1=40)              # siatka wyśrodkowana: ok. 28 mm nad nią
    assert reg2_notes(tight)


def test_project_roundtrip(tmp_path):
    path = tmp_path / 'p.psimp'
    s = Settings(**BASE, reg2_on=True, reg2_h2=7.5, reg2_color='K 100 %')
    save_project(Project(s, [Job(make_pdf(tmp_path))]), str(path))
    loaded = load_project(str(path)).settings
    assert (loaded.reg2_on, loaded.reg2_h2, loaded.reg2_color) == (True, 7.5, 'K 100 %')
