"""Korekta rozmiaru i położenia netto stron w tabeli stron (jak „Koryguj odczytane rozmiary…” w Imp4).

E1: zakres ta strona / wszystkie / nieparzyste / parzyste, w pliku albo w całej tabeli; korekta tylko na stronach
o tym samym rozmiarze co strona korygowana; powrót do wartości z pliku; plik PDF bez zmian. H-38: ramka w mm
w widocznej orientacji strony.
"""
import hashlib
import json
import zipfile

import pymupdf as fitz
import pytest

import page_boxes as pb
from engine import Job, Project, Settings, export_pages, load_project, mm, open_sources, pt, save_project

# --- czyste reguły -------------------------------------------------------------------------------

def test_check_box_and_centred():
    assert pb.check_box((10, 20, 100, 150), 210, 297) == (10, 20, 100, 150)
    assert pb.centred(210, 297, 148, 210) == (31, 43.5, 148, 210)
    for bad in ((-1, 0, 10, 10), (0, 0, 0, 10), (150, 0, 100, 10), (0, 0, 10, 300)):
        with pytest.raises(ValueError):
            pb.check_box(bad, 210, 297)


def test_plan_correction_only_same_size_pages():
    a4, a5 = (210, 297), (148, 210)
    files = [[a4, a5, a4, a4], [a4, a4]]
    targets, skipped = pb.plan_correction(files, 0, 1, pb.SCOPE_ALL, whole_table=False)
    assert targets == {0: [1, 3, 4]} and skipped == [(0, 2)]
    targets, _ = pb.plan_correction(files, 0, 1, pb.SCOPE_ODD, whole_table=True)
    assert targets == {0: [1, 3], 1: [1]}
    targets, _ = pb.plan_correction(files, 0, 3, pb.SCOPE_EVEN, whole_table=False)
    assert targets == {0: [4]}
    targets, skipped = pb.plan_correction(files, 0, 2, pb.SCOPE_PAGE, whole_table=True)
    assert targets == {0: [2]} and skipped == []


def test_apply_and_reset():
    boxes = pb.apply({}, [1, 3], (1, 2, 3, 4))
    assert boxes == {'1': [1, 2, 3, 4], '3': [1, 2, 3, 4]}
    assert pb.apply(boxes, [1], None) == {'3': [1, 2, 3, 4]}


# --- silnik --------------------------------------------------------------------------------------

def make_pdf(folder, rotate=0):
    doc = fitz.open()
    page = doc.new_page(width=pt(210), height=pt(297))
    page.insert_text((pt(15), pt(30)), 'GORA-LEWA', fontsize=14)
    page.insert_text((pt(120), pt(280)), 'DOL-PRAWA', fontsize=14)
    page.set_rotation(rotate)
    path = folder / f'a4_{rotate}.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def digest(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def test_corrected_trimbox_used_in_export_and_file_untouched(tmp_path):
    src = make_pdf(tmp_path)
    before = digest(src)
    job = Job(src, page_boxes={'1': [5, 10, 105, 148]})          # lewy górny róg A4 jako A6
    s = Settings(trim_w=105, trim_h=148, bleed=0, scale_mode='Bez skalowania', crop_marks=False)
    out = tmp_path / 'a6.pdf'
    assert export_pages(Project(s, [job]), str(out)) == 1           # bez korekty: błąd formatu A4 ≠ A6
    with fitz.open(out) as doc:
        text = doc[0].get_text()
    assert 'GORA-LEWA' in text and 'DOL-PRAWA' not in text
    assert digest(src) == before
    with pytest.raises(ValueError):
        export_pages(Project(s, [Job(src)]), str(tmp_path / 'x.pdf'))


def test_rotated_page_box_in_visible_orientation(tmp_path):
    src = make_pdf(tmp_path, rotate=90)                              # widoczna strona 297 × 210
    docs = open_sources([Job(src, page_boxes={'1': [10, 20, 200, 100]})])
    page = docs[src][0]
    visible = fitz.Rect(page.trimbox) * page.rotation_matrix
    visible.normalize()
    assert [round(mm(v), 2) for v in visible] == [10, 20, 210, 120]
    docs[src].close()


def test_invalid_and_conflicting_corrections(tmp_path):
    src = make_pdf(tmp_path)
    with pytest.raises(ValueError):
        open_sources([Job(src, page_boxes={'1': [150, 0, 100, 100]})])
    with pytest.raises(ValueError):
        open_sources([Job(src, page_boxes={'2': [0, 0, 10, 10]})])
    with pytest.raises(ValueError):
        open_sources([Job(src, page_boxes={'1': [0, 0, 10, 10]}), Job(src)])


def test_project_roundtrip_and_old_projects(tmp_path):
    src = make_pdf(tmp_path)
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(), [Job(src, page_boxes={'1': [1, 2, 100, 150]})]), str(path))
    assert load_project(str(path)).jobs[0].page_boxes == {'1': [1, 2, 100, 150]}
    save_project(Project(Settings(), [Job(src)]), str(path))
    with zipfile.ZipFile(path) as z:
        assert 'page_boxes' not in json.loads(z.read('project.json'))['jobs'][0]
    assert load_project(str(path)).jobs[0].page_boxes == {}
