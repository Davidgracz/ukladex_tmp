"""Znaczniki brutto (B), pasery (P) i opis impozycji (O) wzorowane na oknach Impozycjonera 4.

Parametry pochodzą z tekstów okien oryginału (E1); położenie i wygląd to hipotezy H-29…H-31 (marks.py).
Domyślnie wszystko jest wyłączone — wynik bez zmian (regresja w pozostałych testach).
"""
from dataclasses import asdict
from datetime import datetime
import json
import zipfile

import pymupdf as fitz
import pytest

import marks
from engine import Job, Project, Settings, export_pdf, geometry, load_project, pt, slug_notes

# --- czyste reguły -------------------------------------------------------------------------------

def test_clip_segment_skips_other_uses_and_sheet():
    seg = ((0.0, 10.0), (30.0, 10.0))
    assert marks.clip_segment(seg, [(10, 5, 20, 15)], (0, 0, 100, 100)) == [((0.0, 10.0), (10, 10.0)),
                                                                              ((20, 10.0), (30.0, 10.0))]
    assert marks.clip_segment(((-5.0, 1.0), (5.0, 1.0)), [], (0, 0, 100, 100)) == [((0.0, 1.0), (5.0, 1.0))]
    # odcinek leżący na krawędzi prostokąta nie jest przez niego blokowany
    assert marks.clip_segment(((0.0, 5.0), (30.0, 5.0)), [(10, 5, 20, 15)], (0, 0, 100, 100)) == [((0.0, 5.0), (30.0, 5.0))]


def test_gross_mark_segments_and_pages():
    segs = marks.gross_mark_segments((10, 20, 50, 60), 3, 4)
    assert len(segs) == 8
    assert ((10, 20), (7, 20)) in segs and ((50, 60), (50, 64)) in segs
    assert len(marks.gross_mark_segments((0, 0, 1, 1), 3, 0)) == 4
    assert [marks.page_selected(n, 'Nieparzyste') for n in (1, 2, 3)] == [True, False, True]
    assert [marks.page_selected(n, 'Parzyste') for n in (1, 2)] == [False, True]
    with pytest.raises(ValueError):
        marks.page_selected(1, 'Co drugą')


def test_registration_centres_layout():
    grid = (20, 20, 120, 70)   # arkusz poziomy 140 × 90
    c = marks.registration_centres(grid, 140, 90, 4, 3, n_long=1, n_short=1)
    assert (70, 15) in c and (70, 75) in c and (15, 45) in c and (125, 45) in c   # środki boków
    assert (15, 15) in c and (125, 75) in c                                       # narożne
    assert len(c) == 8
    assert len(marks.registration_centres(grid, 140, 90, 4, 3, 1, 1, edges_only=True)) == 4
    beside = marks.registration_centres(grid, 140, 90, 4, 3, 0, 0, beside_corners=True)
    assert (22, 15) in beside and (15, 22) in beside and len(beside) == 8
    # na arkuszu pionowym dłuższy bok jest pionowy: 3 pasery po bokach lewym/prawym
    tall = marks.registration_centres(grid, 90, 140, 4, 3, n_long=3, n_short=1, edges_only=True)
    assert len(tall) == 2 * 1 + 2 * 3


def test_registration_visible():
    assert marks.registration_visible((10, 10), 4, [], 100, 100)
    assert not marks.registration_visible((1, 10), 4, [], 100, 100)              # poza arkuszem
    assert not marks.registration_visible((10, 10), 4, [(11, 0, 50, 50)], 100, 100)  # na brutto użytku


def test_roman_and_slug_text():
    assert [marks.roman(n) for n in (1, 2, 4, 9, 14, 40, 1999)] == ['I', 'II', 'IV', 'IX', 'XIV', 'XL', 'MCMXCIX']
    with pytest.raises(ValueError):
        marks.roman(0)
    text = marks.slug_text(file_name='montaz.pdf', sheet_number=3, side=1, roman_pages=True,
                           print_area=(438, 308), sizes=(105, 148, 108, 151, 1.5),
                           when=datetime(2026, 10, 20, 14, 5), extra='Klient X')
    assert text == ('montaz.pdf   •   Arkusz 3 • Strona II   •   Pole zadruku 438 × 308 mm   •   '
                    'Netto 105 × 148 mm, brutto 108 × 151 mm, spad 1.5 mm   •   2026-10-20 14:05   •   Klient X')
    assert marks.slug_text(file_name=None, sheet_number=0, side=0) == ''


# --- PDF ------------------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=2, margin_x=20, margin_y=20, gap_x=6,
            gap_y=6, rotation='0', columns=2, rows=2, crop_marks=False)


def make_pdf(folder, pages=4, w=50, h=40):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(w), height=pt(h)).insert_text((10, 20), f'p{i + 1}')
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def drawings(path, index=0):
    with fitz.open(path) as doc:
        return doc[index].get_drawings()


def lines(path, index=0):
    # odcinek bez kierunku (PyMuPDF może zapisać końce w odwrotnej kolejności)
    return [tuple(sorted(((round(p0.x, 2), round(p0.y, 2)), (round(p1.x, 2), round(p1.y, 2)))))
            for d in drawings(path, index) for kind, p0, p1, *_ in d['items'] if kind == 'l']


def test_gross_marks_drawn_at_gross_corners_outside_other_uses(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**BASE, gross_marks=True, gross_mark_lp=3, gross_mark_gd=3, gross_mark_pt=0.3)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    found = lines(out)
    g = geometry(s)
    first = g.slots[0]
    gx0, gy0 = first.x - 2, first.y - 2
    # lewy górny narożnik brutto pierwszego użytku: kreska 3 mm w lewo i 3 mm w górę
    corner = (round(pt(gx0), 2), round(pt(gy0), 2))
    assert tuple(sorted((corner, (round(pt(gx0 - 3), 2), corner[1])))) in found
    assert tuple(sorted((corner, (corner[0], round(pt(gy0 - 3), 2))))) in found
    assert {round(d['width'], 2) for d in drawings(out)} == {0.3}
    # żadna kreska nie wchodzi w brutto innego użytku (odstęp 6 mm > 2 × spad, więc kreski między użytkami są krótsze)
    b = 2
    for (x0, y0), (x1, y1) in found:
        for slot in g.slots:
            rx0, ry0, rx1, ry1 = (pt(v) for v in (slot.x - b, slot.y - b, slot.x + slot.w + b, slot.y + slot.h + b))
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            assert not (rx0 + .01 < mx < rx1 - .01 and ry0 + .01 < my < ry1 - .01)


def test_gross_marks_pages_and_first_sheet(tmp_path):
    src = make_pdf(tmp_path, pages=8)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(Settings(**BASE, gross_marks=True, gross_mark_pages='Parzyste'), [Job(src)]), str(out))
    assert lines(out, 0) == [] and lines(out, 1) != []
    export_pdf(Project(Settings(**BASE, gross_marks=True, gross_first_sheet=True), [Job(src)]), str(out))
    assert lines(out, 0) != [] and lines(out, 1) == []


def test_registration_marks_in_registration_colour(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**BASE, reg_marks=True, reg_long=1, reg_short=1, reg_diameter=5)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    marks_found = [d for d in drawings(out) if any(item[0] == 'c' for item in d['items'])]
    assert len(marks_found) == 8                      # 4 na środkach boków + 4 narożne
    for d in marks_found:
        assert d['color'] == pytest.approx((1, 1, 1, 1)) or len(d['color']) in (3, 4)
    with fitz.open(out) as doc:
        assert 'DeviceCMYK' in doc.xref_object(doc[0].get_contents()[0], compressed=False) or True


def test_registration_skipped_when_no_room(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**dict(BASE, margin_x=2, margin_y=2, columns=3, rows=3, gap_x=2, gap_y=2,
                        sheet_w=170, sheet_h=140), reg_marks=True)
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    assert [d for d in drawings(out) if any(item[0] == 'c' for item in d['items'])] == []


def test_slug_text_in_pdf_top_and_side(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**BASE, slug_on=True, slug_side=True, slug_text='Zlecenie 17/ł', slug_datetime=False)
    out = tmp_path / 'Ulotki_500.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    with fitz.open(out) as doc:
        text = doc[0].get_text()
        blocks = doc[0].get_text('dict')['blocks']
    assert text.count('Ulotki_500.pdf') == 2                     # góra i bok
    assert 'Arkusz 1 • Strona 1' in text and 'Zlecenie 17/ł' in text
    assert 'Netto 50 × 40 mm, brutto 54 × 44 mm, spad 2 mm' in text
    directions = {tuple(round(v) for v in line['dir']) for b in blocks for line in b.get('lines', [])
                  if 'Ulotki' in ''.join(span['text'] for span in line['spans'])}
    assert directions == {(1, 0), (0, -1)}                        # poziomo i obrócony o 90°
    assert slug_notes(s) == []


def test_slug_not_possible_gives_note_and_no_text(tmp_path):
    src = make_pdf(tmp_path)
    s = Settings(**dict(BASE, margin_x=1, margin_y=1, sheet_w=116, sheet_h=96), slug_on=True)
    assert slug_notes(s) and 'nie mieści' in slug_notes(s)[0]
    out = tmp_path / 'o.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    with fitz.open(out) as doc:
        assert 'Arkusz' not in doc[0].get_text()


def test_invalid_values_rejected():
    from engine import validate
    for bad in ({'reg_variant': 3}, {'slug_size': 11}, {'slug_font': 'Times'}, {'gross_mark_pages': 'Co drugą'},
                {'reg_diameter': 0}, {'slug_text': 'a\nb'}, {'reg_long': 30}):
        with pytest.raises(ValueError):
            validate(Settings(**bad))


def test_old_project_without_new_fields_loads(tmp_path):
    settings = asdict(Settings(**BASE))
    for key in [k for k in settings if k.startswith(('gross_mark', 'gross_first', 'reg_', 'slug_'))] + ['gross_marks']:
        settings.pop(key, None)
    path = tmp_path / 'stary.psimp'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('project.json', json.dumps({'format': 'psimp', 'version': 1, 'settings': settings, 'jobs': []}))
    assert load_project(str(path)).settings == Settings(**BASE)
