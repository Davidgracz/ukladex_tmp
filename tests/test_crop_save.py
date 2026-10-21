"""„Kadruj do obszaru netto / brutto (netto + 3 mm spad) i zapisz do pliku” — okno korekty obszaru netto Imp4.

E1: dwa polecenia w oknie „Korekta położenia i rozmiaru obszaru netto”. E2 (REA, wywołania bibliotek): nowy dokument,
nowe strony o wymiarach obszaru, treść strony źródłowej wstawiana z przycięciem z czterech stron, nazwa pliku z nazwy
źródła w tym samym folderze. Decyzje własne: H-43 (docs/imp4-wersja-finalna.md).
"""
import hashlib

import pymupdf as fitz
import pytest

import page_boxes as pb
from engine import (CROP_GROSS, CROP_NET, Job, crop_output_name, crop_to_file, mm, pt)

RED, GREEN = (1, 0, 0), (0, 1, 0)


def with_bleed(folder, name='ulotka.pdf', rotation=0):
    """Strona 120 × 170 mm: czerwony spad dookoła, zielony obszar netto 105 × 148 (TrimBox) od (7,5; 11)."""
    doc = fitz.open()
    page = doc.new_page(width=pt(120), height=pt(170))
    page.draw_rect(page.rect, color=None, fill=RED)
    trim = fitz.Rect(pt(7.5), pt(11), pt(112.5), pt(159))
    page.draw_rect(trim, color=None, fill=GREEN)
    page.insert_text((pt(15), pt(30)), 'TRESC', fontsize=14)
    page.set_trimbox(trim)
    if rotation:
        page.set_rotation(rotation)
    path = folder / name
    doc.save(path)
    doc.close()
    return str(path)


def size_mm(page):
    return round(mm(page.rect.width), 2), round(mm(page.rect.height), 2)


def pixel(page, x_mm, y_mm):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return pix.pixel(int(pt(x_mm) * 2), int(pt(y_mm) * 2))


def test_net_crop(tmp_path):
    src = with_bleed(tmp_path)
    before = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    out = tmp_path / 'netto.pdf'
    assert crop_to_file(Job(src), str(out), CROP_NET) == (1, 0)
    with fitz.open(out) as doc:
        page = doc[0]
        assert size_mm(page) == (105, 148)
        assert [round(mm(v), 2) for v in page.trimbox] == [0, 0, 105, 148]
        assert pixel(page, 0.3, 0.3) == (0, 255, 0) and pixel(page, 104.7, 147.7) == (0, 255, 0)   # bez czerwieni
        assert 'TRESC' in page.get_text()                                                         # wektorowo
    assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == before


def test_gross_crop_takes_bleed_from_file(tmp_path):
    out = tmp_path / 'brutto.pdf'
    assert crop_to_file(Job(with_bleed(tmp_path)), str(out), CROP_GROSS) == (1, 0)
    with fitz.open(out) as doc:
        page = doc[0]
        assert size_mm(page) == (111, 154)
        assert [round(mm(v), 2) for v in page.trimbox] == [3, 3, 108, 151]
        assert pixel(page, 1, 77) == (255, 0, 0) and pixel(page, 55, 77) == (0, 255, 0)


def test_gross_crop_without_bleed_in_file_stays_white(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=pt(105), height=pt(148))
    page.draw_rect(page.rect, color=None, fill=GREEN)
    doc.save(tmp_path / 'a6.pdf')
    doc.close()
    out = tmp_path / 'a6_brutto.pdf'
    assert crop_to_file(Job(str(tmp_path / 'a6.pdf')), str(out), CROP_GROSS) == (1, 1)
    with fitz.open(out) as result:
        assert size_mm(result[0]) == (111, 154)
        assert pixel(result[0], 1, 77) == (255, 255, 255) and pixel(result[0], 5, 77) == (0, 255, 0)


def test_rotated_page_keeps_visible_orientation(tmp_path):
    out = tmp_path / 'r.pdf'
    crop_to_file(Job(with_bleed(tmp_path, rotation=90)), str(out), CROP_NET)
    with fitz.open(out) as doc:
        assert size_mm(doc[0]) == (148, 105)
        assert 'TRESC' in doc[0].get_text()
        assert pixel(doc[0], 0.3, 0.3) == (0, 255, 0)


def test_project_corrections_and_resizes_are_applied(tmp_path):
    src = with_bleed(tmp_path)
    corrected = Job(src, page_boxes={'1': [10, 15, 90, 50]})          # ramka netto z okna korekty
    crop_to_file(corrected, str(tmp_path / 'k.pdf'), CROP_NET)
    with fitz.open(tmp_path / 'k.pdf') as doc:
        assert size_mm(doc[0]) == (90, 50)
    resized = Job(src, page_sizes={'1': pb.resize_spec(108, 151)})     # „Zmień rozmiar zaznaczonych stron”
    crop_to_file(resized, str(tmp_path / 's.pdf'), CROP_NET)
    with fitz.open(tmp_path / 's.pdf') as doc:
        assert size_mm(doc[0]) == (108, 151)


def test_refusals_and_names(tmp_path):
    src = with_bleed(tmp_path)
    with pytest.raises(ValueError, match='innego pliku'):
        crop_to_file(Job(src), src, CROP_NET)
    with pytest.raises(ValueError):
        crop_to_file(Job(src), str(tmp_path / 'x.pdf'), 'spad')
    with pytest.raises(ValueError):
        crop_to_file(Job(src), str(tmp_path / 'x.pdf'), CROP_GROSS, bleed=-1)
    assert not (tmp_path / 'x.pdf').exists()
    assert crop_output_name(src, CROP_NET).endswith('ulotka_netto.pdf')
    assert crop_output_name(src, CROP_GROSS).endswith('ulotka_brutto.pdf')


def test_overwrites_existing_output(tmp_path):
    src = with_bleed(tmp_path)
    out = tmp_path / 'wynik.pdf'
    out.write_bytes(b'stary')
    crop_to_file(Job(src), str(out), CROP_NET)
    with fitz.open(out) as doc:
        assert len(doc) == 1
    assert not (tmp_path / 'wynik.pdf.tmp').exists()
