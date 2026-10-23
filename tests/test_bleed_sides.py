"""Spady osobno L / P / G / D „dla obrotu 0°” (E1: grupa „Spady (dla obrotu 0°) [mm]” z przełącznikiem „=”).

Strona testowa ma każdy spad w innym kolorze (lewy czerwony, prawy zielony, górny niebieski, dolny żółty), więc po
pikselach widać, który spad trafił na którą krawędź użytku — także po obrocie użytku o 90°. H-53.
"""
import json
import zipfile

import pymupdf as fitz
import pytest

import marks
from engine import (Job, Project, Settings, bleed_duplex_notes, export_pages, export_pdf, geometry, gross_rect,
                    load_project, mm, open_sources, project_sides, pt, save_project, validate)

RED, GREEN, BLUE, YELLOW = (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)


def coloured_page(folder, pages=1):
    """Strona 60 × 50 mm, TrimBox 50 × 40 mm (5 mm zapasu z każdej strony), spady w kolorach, środek biały."""
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page(width=pt(60), height=pt(50))
        page.draw_rect(fitz.Rect(0, 0, pt(5), pt(50)), color=None, fill=(1, 0, 0))            # lewy
        page.draw_rect(fitz.Rect(pt(55), 0, pt(60), pt(50)), color=None, fill=(0, 1, 0))      # prawy
        page.draw_rect(fitz.Rect(pt(5), 0, pt(55), pt(5)), color=None, fill=(0, 0, 1))        # górny
        page.draw_rect(fitz.Rect(pt(5), pt(45), pt(55), pt(50)), color=None, fill=(1, 1, 0))  # dolny
        page.set_trimbox(fitz.Rect(pt(5), pt(5), pt(55), pt(45)))
    path = folder / 'spady.pdf'
    doc.save(path)
    doc.close()
    return str(path)


BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, margin_x=10, margin_y=10, gap_x=10, gap_y=10,
            columns=1, rows=1, crop_marks=False, bleed_equal=False, bleed_l=1, bleed_r=3, bleed_t=2, bleed_b=4)


def pixel(path, x_mm, y_mm, page=0):
    with fitz.open(path) as doc:
        pix = doc[page].get_pixmap(dpi=200, alpha=False)
    return pix.pixel(int(x_mm / 25.4 * 200), int(y_mm / 25.4 * 200))


# --- reguły -------------------------------------------------------------------------------------------

def test_rotate_bleeds():
    assert marks.rotate_bleeds((1, 3, 2, 4), 0) == (1, 3, 2, 4)
    assert marks.rotate_bleeds((1, 3, 2, 4), 90) == (2, 4, 3, 1)       # górny spad strony → lewa krawędź użytku
    assert marks.rotate_bleeds((1, 3, 2, 4), 180) == (3, 1, 4, 2)
    assert marks.rotate_bleeds((1, 3, 2, 4), 270) == (4, 2, 1, 3)
    for angle in (0, 90, 180, 270):
        assert marks.rotate_bleeds(marks.rotate_bleeds((1, 3, 2, 4), angle), (360 - angle) % 360) == (1, 3, 2, 4)


def test_cut_marks_start_per_side():
    segs = marks.cut_mark_segments((10, 10, 60, 50), (1, 3, 2, 4), 5, 5, 200, 200)
    assert ((9, 10), (4, 10)) in segs and ((63, 10), (68, 10)) in segs          # LP: lewy 1, prawy 3
    assert ((10, 8), (10, 3)) in segs and ((10, 54), (10, 59)) in segs          # GD: górny 2, dolny 4
    assert marks.cut_mark_segments((10, 10, 60, 50), 2, 5, 5, 200, 200) == \
        marks.cut_mark_segments((10, 10, 60, 50), (2, 2, 2, 2), 5, 5, 200, 200)


# --- silnik ---------------------------------------------------------------------------------------------

def test_geometry_and_gross_rect_unrotated():
    s = Settings(**BASE, rotation='0')
    slot = geometry(s).slots[0]
    x0, y0, x1, y1 = gross_rect(s, slot)
    assert (round(slot.x - x0, 6), round(x1 - slot.x - slot.w, 6), round(slot.y - y0, 6),
            round(y1 - slot.y - slot.h, 6)) == (1, 3, 2, 4)


@pytest.mark.parametrize('rotation', ['0', '90'])
def test_each_side_gets_its_own_bleed_colour(tmp_path, rotation):
    src = coloured_page(tmp_path)
    s = Settings(**BASE, rotation=rotation)
    out = tmp_path / f'r{rotation}.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    slot = geometry(s).slots[0]
    l, r, t, b = marks.rotate_bleeds((1, 3, 2, 4), slot.rotation)
    cx, cy = slot.x + slot.w / 2, slot.y + slot.h / 2
    left = pixel(out, slot.x - l / 2, cy)
    right = pixel(out, slot.x + slot.w + r / 2, cy)
    top = pixel(out, cx, slot.y - t / 2)
    bottom = pixel(out, cx, slot.y + slot.h + b / 2)
    if rotation == '0':
        assert (left, right, top, bottom) == (RED, GREEN, BLUE, YELLOW)
    else:   # grafika i spady obracają się razem: krawędź z dolnym spadem strony (4 mm) ma żółty spad
        expected = {1: RED, 3: GREEN, 2: BLUE, 4: YELLOW}
        assert (left, right, top, bottom) == (expected[l], expected[r], expected[t], expected[b])
    # poza spadem jest już biało (spad ma dokładnie swoją szerokość)
    assert pixel(out, slot.x - l - 0.4, cy) == (255, 255, 255)
    assert pixel(out, slot.x + slot.w + r + 0.4, cy) == (255, 255, 255)


def test_single_page_export_uses_bleeds_at_0deg(tmp_path):
    src = coloured_page(tmp_path)
    out = tmp_path / 'strony.pdf'
    export_pages(Project(Settings(**BASE), [Job(src)]), str(out))
    with fitz.open(out) as doc:
        page = doc[0]
        assert (round(mm(page.rect.width), 2), round(mm(page.rect.height), 2)) == (54, 46)
        assert [round(mm(v), 2) for v in page.trimbox] == [1, 2, 51, 42]


def test_equal_switch_keeps_old_behaviour(tmp_path):
    src = coloured_page(tmp_path)
    old = Settings(**{**BASE, 'bleed_equal': True}, bleed=2)
    assert geometry(old) == geometry(Settings(**{k: v for k, v in BASE.items() if not k.startswith('bleed_')},
                                              bleed=2))


def test_validation_and_duplex_note():
    for bad in (dict(bleed_l=-1), dict(bleed_t=60), dict(mode='Broszura'),
                dict(scale_mode='Kadruj 1:1', auto_gross=False, gross_w=60, gross_h=50)):
        with pytest.raises(ValueError):
            validate(Settings(**{**BASE, **bad}))
    duplex = Settings(**BASE, rotation='0', mode='Dwustronnie', flip='Długa krawędź')   # arkusz poziomy
    assert bleed_duplex_notes(duplex) and 'górny i dolny' in bleed_duplex_notes(duplex)[0]
    even = Settings(**{**BASE, 'bleed_t': 3, 'bleed_b': 3}, rotation='0', mode='Dwustronnie', flip='Długa krawędź')
    assert bleed_duplex_notes(even) == []
    assert bleed_duplex_notes(Settings(**BASE)) == []


def test_project_roundtrip_and_old_file(tmp_path):
    src = coloured_page(tmp_path)
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(**BASE), [Job(src)]), str(path))
    s = load_project(str(path)).settings
    assert (s.bleed_equal, s.bleed_l, s.bleed_r, s.bleed_t, s.bleed_b) == (False, 1, 3, 2, 4)
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read('project.json'))
    for key in [k for k in data['settings'] if k.startswith('bleed_')]:
        del data['settings'][key]
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('project.json', json.dumps(data))
    assert load_project(str(path)).settings.bleed_equal is True
