"""Wielostronicowy PDF o różnych formatach stron (A4, A3, A5, A4 poziomo, A6) skalowany do A5 / A6.

Każda strona jest skalowana osobno do użytku. Opcja „obracaj strony do orientacji użytku” (H-37) obraca stronę
poziomą na pionowy użytek (i odwrotnie) o 90° — bez niej strona pozioma byłaby mała (Dopasuj) albo obcięta
o połowę (Wypełnij). Domyślnie wyłączona: stare projekty bez zmian.
"""
import pymupdf as fitz
import pytest

from engine import (FILL_GROSS, Job, Project, Settings, export_pages, export_pdf, orientation_differs, pt,
                    validate)
from job_templates import BUILTIN, apply_template, read_template
from preflight import inspect_project

PAGES = (('A4', 210, 297), ('A3', 297, 420), ('A5', 148, 210), ('A4POZIOMO', 297, 210), ('A6', 105, 148))


def mixed_pdf(folder):
    doc = fitz.open()
    for name, w, h in PAGES:
        page = doc.new_page(width=pt(w), height=pt(h))
        page.draw_rect(page.rect, color=None, fill=(0.15, 0.55, 0.85))
        page.insert_text((pt(15), pt(30)), name, fontsize=24, color=(1, 1, 1))
    path = folder / 'mieszane.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def edge_colours(path, index):
    """Kolory pikseli tuż przy czterech krawędziach i w środku strony wynikowej."""
    with fitz.open(path) as doc:
        page = doc[index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    w, h = pix.width, pix.height
    return [pix.pixel(x, y) for x, y in ((3, h // 2), (w - 4, h // 2), (w // 2, 3), (w // 2, h - 4), (w // 2, h // 2))]


def is_blue(rgb):
    return rgb[2] > 150 and rgb[0] < 100


def test_orientation_differs():
    assert orientation_differs(297, 210, 105, 148)
    assert not orientation_differs(210, 297, 105, 148)
    assert not orientation_differs(100, 100.5, 105, 148)      # prawie kwadrat — bez obrotu
    assert not orientation_differs(297, 210, 100, 100)


@pytest.mark.parametrize('target', [(105, 148), (148, 210)])
def test_every_page_fills_the_use_with_bleed(tmp_path, target):
    src = mixed_pdf(tmp_path)
    s = Settings(trim_w=target[0], trim_h=target[1], bleed=1.5, scale_mode=FILL_GROSS, auto_orient=True,
                 crop_marks=False)
    out = tmp_path / 'strony.pdf'
    assert export_pages(Project(s, [Job(src)]), str(out)) == len(PAGES)
    with fitz.open(out) as doc:
        for page in doc:
            assert page.rect.width == pytest.approx(pt(target[0] + 3), abs=0.01)
            assert page.rect.height == pytest.approx(pt(target[1] + 3), abs=0.01)
            text = page.get_text().strip()
            assert text in {name for name, *_ in PAGES}             # cały napis widoczny — strona nie obcięta
    for index in range(len(PAGES)):
        assert all(is_blue(c) for c in edge_colours(out, index)), index


def test_landscape_page_without_auto_orient_is_cut_in_half(tmp_path):
    src = mixed_pdf(tmp_path)
    s = Settings(trim_w=105, trim_h=148, bleed=1.5, scale_mode=FILL_GROSS, crop_marks=False)
    out = tmp_path / 'bez_obrotu.pdf'
    export_pages(Project(s, [Job(src)]), str(out))
    with fitz.open(out) as doc:
        assert 'A4POZIOMO' not in doc[3].get_text()                  # dotychczasowe zachowanie: strona obcięta


def test_auto_orient_in_imposition_and_preflight(tmp_path):
    src = mixed_pdf(tmp_path)
    s = Settings(trim_w=105, trim_h=148, bleed=1.5, scale_mode=FILL_GROSS, auto_orient=True)
    out = tmp_path / 'montaz.pdf'
    assert export_pdf(Project(s, [Job(src)]), str(out)) == 1
    with fitz.open(out) as doc:
        text = doc[0].get_text()
    assert all(name in text for name, *_ in PAGES)
    codes = [f.code for f in inspect_project(Project(s, [Job(src)])).findings]
    assert 'OBROT' in codes and 'MIESZANE_FORMATY' in codes


def test_no_scaling_accepts_turned_page_only_with_auto_orient(tmp_path):
    doc = fitz.open()
    doc.new_page(width=pt(148), height=pt(105)).insert_text((20, 40), 'POZIOMA')
    doc.save(tmp_path / 'a6_poziomo.pdf')
    doc.close()
    src = str(tmp_path / 'a6_poziomo.pdf')
    base = dict(trim_w=105, trim_h=148, bleed=0, scale_mode='Bez skalowania', crop_marks=False)
    with pytest.raises(ValueError):
        export_pages(Project(Settings(**base), [Job(src)]), str(tmp_path / 'x.pdf'))
    out = tmp_path / 'ok.pdf'
    export_pages(Project(Settings(**base, auto_orient=True), [Job(src)]), str(out))
    with fitz.open(out) as d:
        assert d[0].rect.width == pytest.approx(pt(105), abs=0.01) and 'POZIOMA' in d[0].get_text()


def test_crop_mode_refuses_auto_orient():
    with pytest.raises(ValueError):
        validate(Settings(scale_mode='Kadruj 1:1', auto_orient=True))


def test_templates_for_mixed_formats():
    for size in ('A6 + 1,5 mm', 'A5 + 1,5 mm'):
        name = next(n for n in BUILTIN if size in n)
        s = apply_template(Settings(), read_template(name))
        assert (s.scale_mode, s.white_trim, s.auto_orient) == (FILL_GROSS, True, True)
        validate(s)
