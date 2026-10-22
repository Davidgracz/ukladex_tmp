"""Łączenie plików wynikowych: jeden plik / arkusze / każda strona osobno i ich kombinacje (7 wariantów).

E1: okno „Łączenie plików wynikowych” Impozycjonera 4 (siedem przełączników); komunikat o błędzie łączenia mówi, że
pliki z pojedynczymi stronami zostają na dysku. Nazwy plików arkuszy i stron — H-48.
"""
import json
import zipfile

import pymupdf as fitz
import pytest

import naming
from engine import Job, Project, Settings, export_files, load_project, pt, save_project, validate

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=0, margin_x=10, margin_y=10, gap_x=5, gap_y=5,
            rotation='0', columns=2, rows=1, crop_marks=False)


def test_parts_and_names():
    assert [naming.output_parts(m) for m in naming.OUTPUT_MODES] == [
        (True, False, False), (True, True, False), (True, True, True), (True, False, True),
        (False, True, False), (False, True, True), (False, False, True)]
    with pytest.raises(ValueError):
        naming.output_parts('w kawałkach')
    assert naming.sheet_file_name('montaz.pdf', 2, 9) == 'montaz--arkusz-02.pdf'
    assert naming.sheet_file_name('m.PDF', 12, 120) == 'm--arkusz-012.pdf'
    assert naming.page_file_name('montaz.pdf', 7, 10) == 'montaz--07.pdf'


def make_pdf(folder, pages=6):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40)).insert_text((10, 20), f'p{i + 1}')
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def names_and_pages(paths):
    result = {}
    for path in paths:
        with fitz.open(path) as doc:
            result[path.rsplit('\\', 1)[-1].rsplit('/', 1)[-1]] = len(doc)
    return result


@pytest.mark.parametrize('mode', naming.OUTPUT_MODES)
def test_every_mode_single_sided(tmp_path, mode):
    src = make_pdf(tmp_path)                                            # 6 stron po 2 = 3 arkusze
    out = tmp_path / 'wynik' / 'montaz.pdf'
    written = export_files(Project(Settings(**BASE, output_files=mode), [Job(src)]), str(out))
    one, sheets, pages = naming.output_parts(mode)
    expected = {}
    if one:
        expected['montaz.pdf'] = 3
    if sheets:
        expected.update({f'montaz--arkusz-0{n}.pdf': 1 for n in (1, 2, 3)})
    if pages:
        expected.update({f'montaz--0{n}.pdf': 1 for n in (1, 2, 3)})
    assert names_and_pages(written) == expected
    assert sorted(p.name for p in (tmp_path / 'wynik').iterdir()) == sorted(expected)   # bez plików tymczasowych


def test_duplex_sheet_files_hold_front_and_back(tmp_path):
    src = make_pdf(tmp_path, 8)                                         # 4 pary, 2 pary na arkusz → 2 arkusze
    s = Settings(**BASE, mode='Dwustronnie', output_files='Arkusze + każda strona osobno')
    written = export_files(Project(s, [Job(src)]), str(tmp_path / 'd.pdf'))
    counts = names_and_pages(written)
    assert counts['d--arkusz-01.pdf'] == 2 and counts['d--arkusz-02.pdf'] == 2
    assert [k for k in counts if k.startswith('d--0')] == ['d--01.pdf', 'd--02.pdf', 'd--03.pdf', 'd--04.pdf']
    assert not (tmp_path / 'd.pdf').exists()
    with fitz.open(tmp_path / 'd--arkusz-02.pdf') as doc:
        assert 'p5' in doc[0].get_text() and 'p6' in doc[1].get_text()


def test_slug_uses_real_output_name_not_temporary(tmp_path):
    src = make_pdf(tmp_path, 2)
    s = Settings(**{**BASE, 'margin_y': 25}, slug_on=True, output_files='Jeden plik + arkusze')
    export_files(Project(s, [Job(src)]), str(tmp_path / 'opis.pdf'))
    with fitz.open(tmp_path / 'opis--arkusz-01.pdf') as doc:
        text = doc[0].get_text()
    assert 'opis.pdf' in text and 'tmp' not in text


def test_default_and_old_project(tmp_path):
    assert Settings().output_files == naming.OUTPUT_ONE
    with pytest.raises(ValueError):
        validate(Settings(**BASE, output_files='każdy po trochu'))
    src = make_pdf(tmp_path, 2)
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(**BASE, output_files='Arkusze'), [Job(src)]), str(path))
    assert load_project(str(path)).settings.output_files == 'Arkusze'
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read('project.json'))
    del data['settings']['output_files']
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('project.json', json.dumps(data))
    assert load_project(str(path)).settings.output_files == naming.OUTPUT_ONE      # stary projekt = jeden plik
