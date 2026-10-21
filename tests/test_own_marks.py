"""Znaczniki własne z plików PDF (U) wzorowane na oknie „Parametry znaczników własnych” Impozycjonera 4.

E1 (teksty okna): pliki U1L/U1R — lewy/prawy znacznik na stronie pierwszej (nieparzystej), U2L/U2R — na drugiej
(parzystej); brak pliku = znacznik nieaktywny; H — odległość od lewej/prawej krawędzi wynikowego PDF, V — od dolnej;
H i V wskazują górny lewy (L) albo prawy (R) narożnik znacznika; „dodaj znaczniki: tak/nie”; „rysuj” osobno dla
każdego znacznika. Decyzje własne: H-40..H-42; pytania otwarte OQ-16, OQ-17 (docs/imp4-wersja-finalna.md).
"""
import hashlib
import json
import zipfile

import pymupdf as fitz
import pytest

import marks
from engine import (Job, Project, Settings, export_pdf, load_project, own_mark_placements, own_marks_notes, preview,
                    pt, save_project, validate)
from preflight import inspect_project

# --- czyste reguły -------------------------------------------------------------------------------

def test_mark_name_by_output_page_parity():
    assert marks.own_mark_name(1, 'L') == 'U1L' and marks.own_mark_name(3, 'R') == 'U1R'
    assert marks.own_mark_name(2, 'L') == 'U2L' and marks.own_mark_name(4, 'R') == 'U2R'
    with pytest.raises(ValueError):
        marks.own_mark_name(0, 'L')
    with pytest.raises(ValueError):
        marks.own_mark_name(1, 'X')


def test_mark_rect_from_top_corner():
    # arkusz 200 × 150, znacznik 10 × 6, H = 5, V = 15: górny narożnik 15 mm nad dolną krawędzią
    assert marks.own_mark_rect('L', (10, 6), 5, 15, 200, 150) == (5, 135, 15, 141)
    assert marks.own_mark_rect('R', (10, 6), 5, 15, 200, 150) == (185, 135, 195, 141)
    with pytest.raises(ValueError):
        marks.own_mark_rect('L', (0, 6), 5, 15, 200, 150)


# --- silnik i PDF --------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=2, margin_x=10, margin_y=20, gap_x=6,
            gap_y=6, rotation='0', columns=2, rows=2, crop_marks=False)
RED, GREEN, BLUE = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def make_pdf(folder, pages=8):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40)).insert_text((10, 20), f'p{i + 1}')
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def make_mark(folder, name, size, color):
    folder.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=pt(size[0]), height=pt(size[1]))
    page.draw_rect(page.rect, color=None, fill=color)
    doc.save(folder / f'{name}.pdf')
    doc.close()


def colour_at(page, x_mm, y_mm):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return pix.pixel(int(pt(x_mm) * 2), int(pt(y_mm) * 2))


@pytest.fixture
def marks_folder(tmp_path):
    folder = tmp_path / 'znaczniki'
    make_mark(folder, 'U1L', (10, 6), RED)
    make_mark(folder, 'U1R', (8, 12), BLUE)
    make_mark(folder, 'U2L', (10, 6), GREEN)          # U2R celowo brak
    return folder


def test_marks_on_odd_and_even_output_pages(tmp_path, marks_folder):
    s = Settings(**BASE, own_marks=True, own_folder=str(marks_folder), own_h1=5, own_v1=15, own_h2=20, own_v2=30)
    out = tmp_path / 'wynik.pdf'
    assert export_pdf(Project(s, [Job(make_pdf(tmp_path))]), str(out)) == 2
    with fitz.open(out) as doc:
        first, second = doc[0], doc[1]
        assert colour_at(first, 10, 138) == (255, 0, 0)            # U1L: x 5–15, y 135–141
        assert colour_at(first, 191, 140) == (0, 0, 255)           # U1R: x 187–195, y 135–147
        assert colour_at(second, 25, 123) == (0, 255, 0)           # U2L przy H = 20, V = 30: y 120–126
        assert colour_at(second, 185, 123) == (255, 255, 255)      # U2R brak pliku — nic
        assert colour_at(second, 10, 138) == (255, 255, 255)       # na parzystej nie ma U1L
        assert len(first.get_drawings()) >= 2                      # wektorowo, nie bitmapa


def test_off_by_default_and_draw_switches(tmp_path, marks_folder):
    src = make_pdf(tmp_path)
    s_off = Settings(**BASE)
    s_folder_only = Settings(**BASE, own_folder=str(marks_folder))
    a, b = tmp_path / 'a_out.pdf', tmp_path / 'b_out.pdf'
    export_pdf(Project(s_off, [Job(src)]), str(a))
    export_pdf(Project(s_folder_only, [Job(src)]), str(b))
    with fitz.open(a) as da, fitz.open(b) as db:
        for pa, pb in zip(da, db):
            assert hashlib.sha256(pa.read_contents()).digest() == hashlib.sha256(pb.read_contents()).digest()
    s = Settings(**BASE, own_marks=True, own_folder=str(marks_folder), own_1l=False)
    assert [p.stem for p, _ in own_mark_placements(s, 1)] == ['U1R']
    assert [p.stem for p, _ in own_mark_placements(s, 2)] == ['U2L']


def test_preview_uses_real_sheet_number(tmp_path, marks_folder):
    s = Settings(**BASE, own_marks=True, own_folder=str(marks_folder), own_h1=5, own_v1=15, own_h2=5, own_v2=15)
    project = Project(s, [Job(make_pdf(tmp_path))])
    img0, _ = preview(project, pixels=1000, index=0)
    img1, _ = preview(project, pixels=1000, index=1)
    scale = img0.width / 200
    px = (int(10 * scale), int(138 * scale))
    assert img0.getpixel(px) == (255, 0, 0)          # arkusz 1 — U1L (czerwony)
    assert img1.getpixel(px) == (0, 255, 0)          # arkusz 2 — U2L (zielony)


def test_notes_for_missing_files_and_outside_sheet(tmp_path, marks_folder):
    empty = Settings(**BASE, own_marks=True, own_folder=str(tmp_path / 'pusty'))
    assert 'nie ma plików' in own_marks_notes(empty)[0]
    s = Settings(**BASE, own_marks=True, own_folder=str(marks_folder), own_v1=3)   # 6 mm znacznika, 3 mm do dołu
    notes = own_marks_notes(s)
    assert any('U2R.pdf' in n for n in notes)
    assert any('U1L wystaje poza arkusz' in n for n in notes)
    report = inspect_project(Project(s, [Job(make_pdf(tmp_path))]))
    assert any(f.code == 'ZNACZNIKI_WLASNE' for f in report.findings)


def test_invalid_values_rejected():
    for bad in (dict(own_h1='5'), dict(own_v2=float('nan')), dict(own_h2=5000), dict(own_folder=3)):
        with pytest.raises(ValueError):
            validate(Settings(**BASE, **bad))


def test_broken_mark_file_reports_error(tmp_path):
    folder = tmp_path / 'z'
    folder.mkdir()
    (folder / 'U1L.pdf').write_bytes(b'to nie jest PDF')
    s = Settings(**BASE, own_marks=True, own_folder=str(folder))
    with pytest.raises(ValueError, match='nie jest poprawnym PDF'):
        own_mark_placements(s, 1)


def test_project_roundtrip_and_old_file(tmp_path, marks_folder):
    path = tmp_path / 'p.psimp'
    s = Settings(**BASE, own_marks=True, own_folder=str(marks_folder), own_h2=7.5, own_2r=False)
    save_project(Project(s, [Job(make_pdf(tmp_path))]), str(path))
    loaded = load_project(str(path)).settings
    assert (loaded.own_marks, loaded.own_h2, loaded.own_2r, loaded.own_folder) == (True, 7.5, False, str(marks_folder))
    # stary projekt bez nowych pól → znaczniki własne wyłączone
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        payload = {n: z.read(n) for n in names}
    project_name = next(n for n in names if n.endswith('.json'))
    data = json.loads(payload[project_name])
    for key in [k for k in data['settings'] if k.startswith('own_')]:
        del data['settings'][key]
    payload[project_name] = json.dumps(data).encode('utf-8')
    old = tmp_path / 'stary.psimp'
    with zipfile.ZipFile(old, 'w') as z:
        for n in names:
            z.writestr(n, payload[n])
    assert load_project(str(old)).settings.own_marks is False
