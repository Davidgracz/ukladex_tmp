"""Rozmiar wynikowego PDF: papier / pole zadruku / papier + chwyt / pole zadruku + chwyt / płyta (E1), H-54."""
import json
import zipfile

import pymupdf as fitz
import pytest

import press
from engine import (Job, Project, Settings, export_files, export_pdf, geometry, load_project, mm, pt, save_project,
                    validate)

# --- czyste reguły -------------------------------------------------------------------------------------

def test_layouts():
    paper = press.layout(press.OUT_PAPER, 450, 320, 6, 6)
    assert paper.unchanged and (paper.page_w, paper.page_h) == (450, 320)
    grip = press.layout(press.OUT_PAPER_GRIP, 450, 320, 6, 6, grip=11)
    assert (grip.page_w, grip.page_h, grip.offset, grip.paper) == (450, 331, (0, 0), (0, 0, 450, 320))
    area = press.layout(press.OUT_AREA, 450, 320, 6, 8, tech_margin=10)
    assert (area.page_w, area.page_h, area.clip, area.offset) == (438, 294, (6, 8, 444, 302), (-6, -8))
    area_grip = press.layout(press.OUT_AREA_GRIP, 450, 320, 6, 8, grip=11)
    assert (area_grip.page_w, area_grip.page_h, area_grip.paper) == (438, 323, (0, 0, 438, 312))
    plate = press.layout(press.OUT_PLATE, 450, 320, 6, 6, grip=11, plate_w=510, plate_h=400)
    assert (plate.page_w, plate.page_h, plate.offset, plate.paper) == (510, 400, (30, 69), (30, 69, 480, 389))
    reduced = press.layout(press.OUT_PLATE, 450, 320, 6, 6, grip=11, plate_w=510, plate_h=400, plate_reduce_pt=72)
    assert reduced.page_w == pytest.approx(510 - 25.4) and reduced.offset[1] == pytest.approx(69 - 12.7)


def test_layout_errors():
    for kwargs in (dict(kind='Zły'), dict(kind=press.OUT_PLATE), dict(kind=press.OUT_PLATE, plate_w=400, plate_h=400),
                   dict(kind=press.OUT_AREA, tech_margin=400), dict(kind=press.OUT_PAPER_GRIP, grip=-1)):
        kind = kwargs.pop('kind')
        with pytest.raises(ValueError):
            press.layout(kind, 450, 320, 6, 6, **{'grip': 11, **kwargs})


# --- silnik i PDF ------------------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=0, margin_x=10, margin_y=10, gap_x=5, gap_y=5,
            rotation='0', columns=2, rows=1, crop_marks=False)


def solid_pdf(folder, pages=2):
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page(width=pt(50), height=pt(40))
        page.draw_rect(page.rect, color=None, fill=(1, 0, 0))
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def red_box(path, page=0):
    """Prostokąt czerwonej grafiki na stronie (mm)."""
    with fitz.open(path) as doc:
        pix = doc[page].get_pixmap(dpi=72, alpha=False)
        size = (round(mm(doc[page].rect.width), 2), round(mm(doc[page].rect.height), 2))
        trim = [round(mm(v), 2) for v in doc[page].trimbox]
    xs, ys = [], []
    for y in range(pix.height):
        for x in range(pix.width):
            if pix.pixel(x, y) == (255, 0, 0):
                xs.append(x); ys.append(y)
    return size, trim, (round(mm(min(xs))), round(mm(min(ys))), round(mm(max(xs) + 1)), round(mm(max(ys) + 1)))


def test_plate_output_places_paper_above_grip(tmp_path):
    src = solid_pdf(tmp_path)
    s = Settings(**BASE, output_size=press.OUT_PLATE, grip=11, plate_w=260, plate_h=200)
    out = tmp_path / 'p.pdf'
    export_pdf(Project(s, [Job(src)]), str(out))
    size, trim, box = red_box(out)
    slots = geometry(s).slots
    ox, oy = (260 - 200) / 2, 200 - 11 - 150                      # papier wyśrodkowany, chwyt 11 mm pod nim
    assert size == (260, 200) and trim == [ox, oy, ox + 200, oy + 150]
    assert box == (round(ox + slots[0].x), round(oy + slots[0].y), round(ox + slots[1].x + 50),
                   round(oy + slots[0].y + 40))
    with fitz.open(out) as doc:
        assert not doc[0].get_images()                             # nadal wektor


def test_print_area_and_paper_grip(tmp_path):
    src = solid_pdf(tmp_path)
    area = tmp_path / 'area.pdf'
    export_pdf(Project(Settings(**BASE, output_size=press.OUT_AREA), [Job(src)]), str(area))
    size, trim, box = red_box(area)
    assert size == (180, 130) and trim == [0, 0, 180, 130]
    slot = geometry(Settings(**BASE)).slots[0]
    assert box[:2] == (round(slot.x - 10), round(slot.y - 10))
    grip = tmp_path / 'grip.pdf'
    export_pdf(Project(Settings(**BASE, output_size=press.OUT_PAPER_GRIP, grip=12), [Job(src)]), str(grip))
    size, trim, _ = red_box(grip)
    assert size == (200, 162) and trim == [0, 0, 200, 150]


def test_tech_margin_moves_grid_up(tmp_path):
    plain, tech = geometry(Settings(**BASE)), geometry(Settings(**BASE, tech_margin=20))
    assert tech.slots[0].y == pytest.approx(plain.slots[0].y - 10)    # siatka wyśrodkowana nad pasem „na łapki”
    with pytest.raises(ValueError):
        validate(Settings(**BASE, tech_margin=200))


def test_default_unchanged_and_sheet_files(tmp_path):
    src = solid_pdf(tmp_path, pages=4)
    a, b = tmp_path / 'wynik_a.pdf', tmp_path / 'wynik_b.pdf'
    export_pdf(Project(Settings(**BASE), [Job(src)]), str(a))
    export_pdf(Project(Settings(**BASE, output_size=press.OUT_PAPER, grip=30), [Job(src)]), str(b))
    with fitz.open(a) as da, fitz.open(b) as db:
        assert [p.read_contents() for p in da] == [p.read_contents() for p in db]
    files = export_files(Project(Settings(**BASE, output_size=press.OUT_PAPER_GRIP, output_files='Arkusze'),
                                 [Job(src)]), str(tmp_path / 'm.pdf'))
    assert len(files) == 2 and all(red_box(f)[0] == (200, 161) for f in files)


def test_validation_and_old_project(tmp_path):
    with pytest.raises(ValueError, match='nie mieści się'):
        validate(Settings(**BASE, output_size=press.OUT_PLATE, plate_w=150, plate_h=150))
    with pytest.raises(ValueError):
        validate(Settings(**BASE, output_size='A4'))
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(**BASE, output_size=press.OUT_PLATE, plate_w=260, plate_h=200), [Job(solid_pdf(tmp_path))]),
                 str(path))
    assert load_project(str(path)).settings.plate_w == 260
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read('project.json'))
    for key in ('output_size', 'grip', 'plate_w', 'plate_h', 'plate_reduce_pt', 'tech_margin'):
        del data['settings'][key]
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('project.json', json.dumps(data))
    assert load_project(str(path)).settings.output_size == press.OUT_PAPER


def test_settings_dialog_sets_plate(tmp_path):
    """Okno „Ustawienia…”: sekcja rozmiaru PDF otwiera się, wartości trafiają do ustawień i paska stanu."""
    from conftest import create_tk
    app = pytest.importorskip('app')
    window = create_tk(app.App)
    try:
        window.update()
        window.open_output_settings()
        window.update()
        window.press_vars['output_size'].set(press.OUT_PLATE)
        window.press_vars['plate_w'].set('510')
        window.press_vars['plate_h'].set('400,5')
        s = window._read_fields()
        assert (s.output_size, s.plate_w, s.plate_h, s.grip) == (press.OUT_PLATE, 510, 400.5, 11)
        window.variables['trim_w'].set('50')
        window.variables['trim_h'].set('40')
        window.scale_var.set('Bez skalowania')
        window.project.jobs.append(Job(solid_pdf(tmp_path)))
        window.refresh()
        window.update()
        assert 'PDF 510 × 400.5 mm (płyta)' in window.stats_text.get()
        window.press_vars['plate_w'].set('abc')
        with pytest.raises(ValueError):
            window._read_fields()
    finally:
        window.destroy()
