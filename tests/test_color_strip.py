"""Pasek kontroli koloru (K) wzorowany na oknie „Parametry pasków kontroli koloru” Impozycjonera 4.

E1: 12 kostek K1–K12, co najmniej jedna z kolorem; szerokość/wysokość kostki, ilość stref, odsunięcie,
góra / dół / wycinka pozioma, pełna długość albo „pole zadruku minus X”, wyśrodkowany albo od lewej, pasek z PDF.
Pozostałe decyzje: H-32, H-33 (marks.py).
"""
from dataclasses import asdict
import json
import zipfile

import pymupdf as fitz
import pytest

import marks
from engine import (Job, Project, Settings, export_pdf, geometry, load_project, pt, save_project, strip_notes,
                    validate)


# --- czyste reguły -------------------------------------------------------------------------------

def test_parse_and_format_cmyk():
    assert marks.parse_cmyk('100/0/0/0') == (100, 0, 0, 0)
    assert marks.parse_cmyk(' 50; 40; 30; 20 ') == (50, 40, 30, 20)
    assert marks.parse_cmyk('12,5/0/0/0') == (12.5, 0, 0, 0)
    assert marks.parse_cmyk('') is None
    for bad in ('100/0/0', 'a/0/0/0', '120/0/0/0'):
        with pytest.raises(ValueError):
            marks.parse_cmyk(bad)
    assert marks.format_cmyk((12.5, 0, 0, 100)) == '12.5/0/0/100'


def test_strip_cells_cycle_centre_and_zones():
    colors = ((100, 0, 0, 0), None, (0, 100, 0, 0)) + (None,) * 9
    cells = marks.strip_cells(23, 5, colors)                      # 4 całe kostki, 3 mm luzu
    assert [c for _, c in cells] == [(100, 0, 0, 0), (0, 100, 0, 0)] * 2
    assert cells[0][0] == pytest.approx(1.5)                      # wyśrodkowany
    assert marks.strip_cells(23, 5, colors, centered=False)[0][0] == 0
    assert len(marks.strip_cells(100, 5, colors, zones=3)) == 6   # 3 powtórzenia sekwencji 2 kostek
    with pytest.raises(ValueError):
        marks.strip_cells(100, 5, (None,) * 12)


# --- silnik i PDF --------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=2, margin_x=10, margin_y=20, gap_x=6,
            gap_y=6, rotation='0', columns=2, rows=2, crop_marks=False)


def make_pdf(folder, pages=4):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40)).insert_text((10, 20), f'p{i + 1}')
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def filled_rects(path):
    with fitz.open(path) as doc:
        return [(d['rect'], tuple(round(v, 3) for v in d['fill'])) for d in doc[0].get_drawings()
                if d.get('fill') is not None]


def grid_top(s):
    g = geometry(s)
    return min(sl.y for sl in g.slots) - s.bleed


def test_strip_on_top_full_print_area(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**BASE, strip_on=True, strip_cell_w=5, strip_cell_h=4, strip_offset=1)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    cells = filled_rects(out)
    assert len(cells) == 36                                        # (200 − 2·10) / 5
    assert cells[0][1] == cells[12][1] != cells[1][1]               # sekwencja 12 kostek powtarza się
    with fitz.open(out) as doc:                                    # w PDF zapisany jest kolor CMYK (operator k)
        content = b''.join(doc.xref_stream(x) for x in doc[0].get_contents()).decode('latin-1')
    for cmyk in ('1 0 0 0 k', '0 1 0 0 k', '0 0 1 0 k', '0 0 0 1 k', '.5 0 0 0 k'):
        assert cmyk in content, cmyk
    bottom = max(r.y1 for r, _ in cells)
    assert bottom == pytest.approx(pt(grid_top(s) - 1), abs=0.01)  # odsunięcie 1 mm nad siatką
    assert min(r.x0 for r, _ in cells) == pytest.approx(pt(10), abs=0.01)
    assert strip_notes(s) == []


def test_strip_bottom_trim_left_and_zones(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**BASE, strip_on=True, strip_top=False, strip_bottom=True, strip_trim=30,
                 strip_centered=False, strip_zones=1)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    cells = filled_rects(out)
    assert len(cells) == 12                                        # jedna strefa = 12 kostek
    assert min(r.x0 for r, _ in cells) == pytest.approx(pt(10), abs=0.01)   # od lewej krawędzi pola zadruku
    g = geometry(s)
    assert min(r.y0 for r, _ in cells) == pytest.approx(pt(max(sl.y + sl.h for sl in g.slots) + 2 + 1), abs=0.01)


def test_strip_on_horizontal_gutter(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**BASE, strip_on=True, strip_top=False, strip_gutter=True, gutter_on=True, gutter_h=10,
                 strip_cell_h=5, strip_offset=1)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    cells = filled_rects(out)
    g = geometry(s)
    assert cells and all(r.y0 == pytest.approx(pt(g.gutter_y - 2.5), abs=0.01) for r, _ in cells)
    narrow = Settings(**BASE, strip_on=True, strip_top=False, strip_gutter=True, gutter_on=True, gutter_h=6)
    assert 'wycince' in strip_notes(narrow)[0]


def test_strip_from_pdf_file(tmp_path):
    src = make_pdf(tmp_path)
    strip = fitz.open()
    page = strip.new_page(width=pt(120), height=pt(6))
    page.insert_text((5, 12), 'FOGRA-STRIP', fontsize=8)
    strip.save(tmp_path / 'pasek.pdf')
    strip.close()
    s = Settings(**BASE, strip_on=True, strip_pdf=str(tmp_path / 'pasek.pdf'))
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    with fitz.open(out) as doc:
        assert 'FOGRA-STRIP' in doc[0].get_text()
    with pytest.raises(ValueError):
        export_pdf(Project(Settings(**BASE, strip_on=True, strip_pdf=str(tmp_path / 'brak.pdf')), [Job(src)]),
                   str(tmp_path / 'x.pdf'))


def test_no_room_gives_note_and_nothing_drawn(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**dict(BASE, margin_y=2, sheet_h=2 * 44 + 6 + 4), strip_on=True, strip_bottom=True)
    notes = strip_notes(s)
    assert any('górze' in n for n in notes) and any('dole' in n for n in notes)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    assert filled_rects(out) == []


def test_slug_moves_above_strip(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**dict(BASE, margin_y=30, sheet_h=164), strip_on=True, slug_on=True, slug_datetime=False)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    cells = filled_rects(out)
    with fitz.open(out) as doc:
        words = [w for w in doc[0].get_text('words') if w[4] == 'Arkusz']
    assert words and words[0][3] <= min(r.y0 for r, _ in cells) + 0.01   # tekst kończy się nad paskiem


def test_validation_and_project_roundtrip(tmp_path):
    with pytest.raises(ValueError):
        validate(Settings(strip_on=True, strip_colors=(None,) * 12))
    for bad in ({'strip_cell_w': 0}, {'strip_zones': -1}, {'strip_colors': ((100, 0, 0),) + (None,) * 11},
                {'strip_colors': ((100, 0, 0, 0),)}):
        with pytest.raises(ValueError):
            validate(Settings(**bad))
    s = Settings(**BASE, strip_on=True, strip_colors=((10, 20, 30, 40),) + (None,) * 11)
    path = tmp_path / 'p.psimp'
    save_project(Project(s, []), str(path))
    assert load_project(str(path)).settings == s                   # krotki kolorów wracają jako krotki


def test_old_project_without_strip_fields(tmp_path):
    data = asdict(Settings(**BASE))
    for key in [k for k in data if k.startswith('strip_')]:
        data.pop(key)
    path = tmp_path / 'stary.psimp'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('project.json', json.dumps({'format': 'psimp', 'version': 1, 'settings': data, 'jobs': []}))
    assert load_project(str(path)).settings == Settings(**BASE)
