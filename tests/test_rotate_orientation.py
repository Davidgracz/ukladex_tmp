"""Strona z /Rotate w PDF trafia na arkusz tak, jak widać ją w czytniku PDF.

Błąd do 0.5.7: show_pdf_page(rotate=) obraca przeciwnie do ruchu wskazówek zegara, a /Rotate i rachunek wycinka
(_rotate_point) — zgodnie; strona z /Rotate 90 lądowała na arkuszu odwrócona o 180° względem podglądu w czytniku.
Strony bez /Rotate układają się jak dotąd (także obrócone użytki).
"""
import pymupdf as fitz
import pytest

from engine import Job, Project, Settings, export_pdf, geometry, pt


def marked_page(folder, rotation):
    """Strona 60 × 40 mm: czerwony pas u góry, niebieski z prawej (w układzie nieobróconym)."""
    doc = fitz.open()
    page = doc.new_page(width=pt(60), height=pt(40))
    page.draw_rect(fitz.Rect(0, 0, pt(60), pt(6)), color=None, fill=(1, 0, 0))
    page.draw_rect(fitz.Rect(pt(54), 0, pt(60), pt(40)), color=None, fill=(0, 0, 1))
    page.set_rotation(rotation)
    path = folder / f'r{rotation}.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def sides(page, rect):
    pix = page.get_pixmap(dpi=150, alpha=False)
    k = 150 / 72
    x0, y0, x1, y1 = (v * k for v in rect)
    probes = {'L': (x0 + 4, (y0 + y1) / 2), 'P': (x1 - 4, (y0 + y1) / 2),
              'G': ((x0 + x1) / 2, y0 + 4), 'D': ((x0 + x1) / 2, y1 - 4)}
    names = {(255, 0, 0): 'czerwony', (0, 0, 255): 'niebieski'}
    return {k: names.get(pix.pixel(int(x), int(y)), '-') for k, (x, y) in probes.items()}


@pytest.mark.parametrize('rotation', [90, 180, 270])
def test_rotated_source_matches_pdf_viewer(tmp_path, rotation):
    src = marked_page(tmp_path, rotation)
    with fitz.open(src) as doc:
        viewer = sides(doc[0], doc[0].rect)
        w, h = doc[0].rect.width / pt(1), doc[0].rect.height / pt(1)
    s = Settings(sheet_w=200, sheet_h=150, trim_w=round(w, 3), trim_h=round(h, 3), bleed=0, columns=1, rows=1,
                 crop_marks=False, rotation='0', margin_x=10, margin_y=10)
    out = tmp_path / 'm.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    slot = geometry(s).slots[0]
    with fitz.open(out) as doc:
        assert sides(doc[0], (pt(slot.x), pt(slot.y), pt(slot.x + slot.w), pt(slot.y + slot.h))) == viewer


def test_unrotated_source_on_rotated_use_unchanged(tmp_path):
    """Bez /Rotate: użytek obrócony o 90° jak w poprzednich wersjach (góra strony po lewej)."""
    src = marked_page(tmp_path, 0)
    s = Settings(sheet_w=200, sheet_h=150, trim_w=60, trim_h=40, bleed=0, columns=1, rows=1, crop_marks=False,
                 rotation='90', margin_x=10, margin_y=10)
    out = tmp_path / 'm.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    slot = geometry(s).slots[0]
    with fitz.open(out) as doc:
        assert sides(doc[0], (pt(slot.x), pt(slot.y), pt(slot.x + slot.w), pt(slot.y + slot.h))) == \
            {'L': 'czerwony', 'P': '-', 'G': 'niebieski', 'D': '-'}
