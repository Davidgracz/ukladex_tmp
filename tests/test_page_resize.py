"""Zmiana rozmiaru zaznaczonych stron — obserwacja działającego Impozycjonera (E3, zrzuty użytkownika):
tabela stron → „Zmień parametry w zaznaczonych wierszach”, Szerokość 108 / Wysokość 151 → strony A4 i A6 są
przeskalowane do 108 × 151 i tak trafiają na arkusz (użytek 105 × 148 + spad 1,5). Opcje rozmiaru jak w oknie
„Automatyczna konwersja bitmap do PDF”: niezależnie (+ kadrowanie), tylko szerokość, tylko wysokość, zachowaj
orientację, definiuj spad. H-39 (page_boxes.resize_plan).
"""
import hashlib

import pymupdf as fitz
import pytest

import page_boxes as pb
from engine import Job, Project, Settings, export_pages, export_pdf, load_project, mm, open_sources, pt, save_project

# --- czyste reguły -------------------------------------------------------------------------------

def test_resize_plan_modes():
    stretch = pb.resize_spec(108, 151)
    assert pb.resize_plan(210, 297, stretch) == (108, 151, (210, 297))
    crop = pb.resize_spec(108, 151, pb.RESIZE_CROP)
    w, h, (cw, ch) = pb.resize_plan(210, 297, crop)
    assert (w, h) == (108, 151)
    assert cw / ch == pytest.approx(108 / 151)                     # wycinek ma proporcje celu
    assert cw <= 210 + 1e-9 and ch <= 297 + 1e-9
    assert pb.resize_plan(210, 297, pb.resize_spec(105, 999, pb.RESIZE_WIDTH))[:2] == (105, pytest.approx(148.5))
    assert pb.resize_plan(210, 297, pb.resize_spec(999, 148.5, pb.RESIZE_HEIGHT))[:2] == (pytest.approx(105), 148.5)


def test_keep_orientation_swaps_for_landscape_pages():
    spec = pb.resize_spec(108, 151, keep_orientation=True)
    assert pb.resize_plan(297, 210, spec)[:2] == (151, 108)
    assert pb.resize_plan(297, 210, pb.resize_spec(108, 151, keep_orientation=False))[:2] == (108, 151)


def test_resize_spec_validation():
    for args in ((0, 10), (10, 6000), (10, 10, 'Coś'), ):
        with pytest.raises(ValueError):
            pb.resize_spec(*args)
    with pytest.raises(ValueError):
        pb.resize_spec(10, 10, bleed=-1)


# --- silnik --------------------------------------------------------------------------------------

def cards_pdf(folder):
    """2 strony A4 i 2 strony A6 z ramką do krawędzi (jak karty ze zrzutu)."""
    doc = fitz.open()
    for name, w, h in (('A4-1', 210, 297), ('A4-2', 210, 297), ('A6-1', 105, 148), ('A6-2', 105, 148)):
        page = doc.new_page(width=pt(w), height=pt(h))
        page.draw_rect(page.rect, color=None, fill=(0.85, 0.65, 0.1))
        page.insert_text((pt(5), pt(15)), name, fontsize=12)
    path = folder / 'karty.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def test_user_scenario_a4_and_a6_to_108x151_then_imposed(tmp_path):
    src = cards_pdf(tmp_path)
    before = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    sizes = {str(n): pb.resize_spec(108, 151) for n in range(1, 5)}
    job = Job(src, page_sizes=sizes)
    docs = open_sources([job])
    for page in docs[src]:
        assert (round(mm(page.trimbox.width), 2), round(mm(page.trimbox.height), 2)) == (108, 151)
    docs[src].close()
    # Montaż jak w 0.4.1: Kadruj 1:1, netto 105 × 148, spad 1,5 → brutto 108 × 151 z całej przeskalowanej strony
    s = Settings(trim_w=105, trim_h=148, bleed=1.5, scale_mode='Kadruj 1:1', auto_gross=True, auto_source=True)
    out = tmp_path / 'arkusz.pdf'
    assert export_pdf(Project(s, [job]), str(out)) == 1
    with fitz.open(out) as doc:
        text = doc[0].get_text()
    assert all(name in text for name in ('A4-1', 'A4-2', 'A6-1', 'A6-2'))
    assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == before   # plik na dysku bez zmian


def test_bleed_and_crop_modes_in_single_page_export(tmp_path):
    src = cards_pdf(tmp_path)
    # kwadrat 100 × 100 z A4 z kadrowaniem: wycinek 210 × 210 ze środka — nad i pod nim jest grafika na spad
    spec = pb.resize_spec(100, 100, pb.RESIZE_CROP, bleed=1.5)
    docs = open_sources([Job(src, page_sizes={'1': spec, '3': pb.resize_spec(105, 148, bleed=1.5)})])
    page = docs[src][0]
    assert round(mm(page.rect.width), 2) == 103 and round(mm(page.rect.height), 2) == 103
    assert [round(mm(v), 2) for v in page.trimbox] == [1.5, 1.5, 101.5, 101.5]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    assert pix.pixel(pix.width // 2, 2)[2] < 100                   # spad u góry z grafiki źródła
    assert pix.pixel(2, pix.height // 2) == (255, 255, 255)       # z boku źródło nie ma zapasu — biel, nic nie dorabiamy
    # A6 bez spadu w źródle: spad pozostaje biały (silnik nie wymyśla grafiki)
    a6 = docs[src][2].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    assert a6.pixel(1, a6.height // 2) == (255, 255, 255) and a6.pixel(10, a6.height // 2)[2] < 100
    docs[src].close()


def test_rotated_source_page_keeps_content(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=pt(210), height=pt(297))
    page.insert_text((pt(10), pt(20)), 'OBROCONA', fontsize=14)
    page.set_rotation(90)                                           # widoczna 297 × 210 (poziomo)
    doc.save(tmp_path / 'r.pdf')
    doc.close()
    src = str(tmp_path / 'r.pdf')
    docs = open_sources([Job(src, page_sizes={'1': pb.resize_spec(108, 151, keep_orientation=True)})])
    page = docs[src][0]
    assert (round(mm(page.rect.width)), round(mm(page.rect.height))) == (151, 108)   # orientacja zachowana
    assert 'OBROCONA' in page.get_text()
    docs[src].close()


def test_project_roundtrip_and_conflict(tmp_path):
    src = cards_pdf(tmp_path)
    path = tmp_path / 'p.psimp'
    spec = pb.resize_spec(108, 151)
    save_project(Project(Settings(), [Job(src, page_sizes={'2': spec})]), str(path))
    assert load_project(str(path)).jobs[0].page_sizes == {'2': spec}
    with pytest.raises(ValueError):
        open_sources([Job(src, page_sizes={'2': spec}), Job(src)])
    with pytest.raises(ValueError):
        open_sources([Job(src, page_sizes={'9': spec})])
