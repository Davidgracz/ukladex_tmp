"""Odwracanie przez markę: pełny i niepełny przez markę boczną (MB, work-and-turn) i czołową (MC, work-and-tumble).

E1: rodzaje arkuszy „Dwustronny pełny / niepełny przez markę boczną (MB) / czołową (MC)”; przy niepełnym MB liczba
kolumn musi być parzysta, przy niepełnym MC — liczba wierszy. Decyzje: H-55.

Test fizyczny: strona arkusza B po odwróceniu ma punkt (x, y) za punktem strony A — MB: (W − x, y), MC: (x, H − y).
Każdy przód ma czerwony pas u góry (głowa), każdy tył — niebieski pas u góry; tył musi leżeć dokładnie za swoim
przodem i mieć głowę po tej samej stronie co przód (karta odwracana „jak książka”).
"""
import pymupdf as fitz
import pytest

from engine import (FLIP_MB, FLIP_MC, TURN_MB, TURN_MC, Job, Project, Settings, export_pdf, geometry, open_sources,
                    project_sides, pt, validate)

RED, BLUE, WHITE = (255, 0, 0), (0, 0, 255), (255, 255, 255)
BASE = dict(sheet_w=200, sheet_h=150, trim_w=40, trim_h=30, bleed=0, margin_x=10, margin_y=10, gap_x=5, gap_y=5,
            rotation='0', crop_marks=False)


def pairs_pdf(folder, pairs):
    """Strony: przód 1, tył 1, przód 2, tył 2… Przód: czerwony pas u góry; tył: niebieski pas u góry."""
    doc = fitz.open()
    for i in range(pairs):
        for colour in ((1, 0, 0), (0, 0, 1)):
            page = doc.new_page(width=pt(40), height=pt(30))
            page.draw_rect(fitz.Rect(0, 0, pt(40), pt(6)), color=None, fill=colour)
            page.insert_text((pt(15), pt(20)), str(i + 1), fontsize=20)
    path = folder / 'pary.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def placements(project):
    sources = open_sources(project.jobs)
    try:
        return [side for side in project_sides(project, sources)]
    finally:
        for doc in sources.values():
            doc.close()


def head(img, slot, k):
    """Kolor przy górnej i dolnej krawędzi użytku na obrazie."""
    cx = int((slot.x + slot.w / 2) * k)
    return img.pixel(cx, int((slot.y + 1.5) * k)), img.pixel(cx, int((slot.y + slot.h - 1.5) * k))


@pytest.mark.parametrize('mode', [TURN_MB, TURN_MC])
def test_back_lies_behind_front_with_head_aligned(tmp_path, mode):
    s = Settings(**BASE, mode=mode, columns=4, rows=2)
    src = pairs_pdf(tmp_path, 4)                                   # 4 pary = jedna płyta (4 przody + 4 tyły)
    out = tmp_path / 'plyta.pdf'
    assert export_pdf(Project(s, [Job(src)]), str(out)) == 1        # jedna strona = jedna płyta
    with fitz.open(out) as doc:
        img = doc[0].get_pixmap(dpi=100, alpha=False)
        text_blocks = doc[0].get_text('words')
    k = 100 / 25.4
    side = placements(Project(s, [Job(src)]))[0]
    fronts = side.placements[0::2]
    backs = side.placements[1::2]
    for f, b in zip(fronts, backs):
        assert f.source.index % 2 == 0 and b.source.index == f.source.index + 1    # para przód/tył
        # tył leży dokładnie za przodem po odwróceniu arkusza
        if mode == TURN_MB:
            assert b.slot.x == pytest.approx(s.sheet_w - f.slot.x - f.slot.w) and b.slot.y == pytest.approx(f.slot.y)
        else:
            assert b.slot.y == pytest.approx(s.sheet_h - f.slot.y - f.slot.h) and b.slot.x == pytest.approx(f.slot.x)
        top, bottom = head(img, f.slot, k)
        assert top == RED and bottom == WHITE                       # przód: głowa u góry płyty
        top, bottom = head(img, b.slot, k)
        if mode == TURN_MB:
            assert top == BLUE and bottom == WHITE                  # odwrócenie na boki: głowa bez zmian
        else:
            assert top == WHITE and bottom == BLUE                  # przez markę czołową: tył obrócony o 180°
    assert len({w[4] for w in text_blocks}) == 4


def test_front_halves_and_partial_plate(tmp_path):
    src = pairs_pdf(tmp_path, 5)                                    # 5 par na płytach po 4 → 2 płyty, druga niepełna
    s = Settings(**BASE, mode=TURN_MB, columns=4, rows=2)
    sides = placements(Project(s, [Job(src)]))
    assert len(sides) == 2
    fronts = sides[0].placements[0::2]
    assert {p.slot.col for p in fronts} == {0, 1}                   # przody w lewej połowie
    last = sides[1].placements
    assert len(last) == 8 and sum(p.source is not None for p in last) == 2


def test_odd_columns_or_rows_refused(tmp_path):
    src = pairs_pdf(tmp_path, 2)
    with pytest.raises(ValueError, match='kolumn.*parzysta'):
        placements(Project(Settings(**BASE, mode=TURN_MB, columns=3, rows=2), [Job(src)]))
    with pytest.raises(ValueError, match='wierszy.*parzysta'):
        placements(Project(Settings(**BASE, mode=TURN_MC, columns=4, rows=1), [Job(src)]))
    with pytest.raises(ValueError, match='spady'):
        placements(Project(Settings(**{**BASE, 'sheet_w': 260, 'sheet_h': 200}, mode=TURN_MB, columns=4, rows=2, bleed_equal=False,
                                    bleed_l=1, bleed_r=2), [Job(src)]))


@pytest.mark.parametrize('flip', [FLIP_MB, FLIP_MC])
def test_full_duplex_by_lay(tmp_path, flip):
    """Pełny: tył na osobnej stronie (płycie); MB — lustro w poziomie, MC — w pionie i obrót o 180°."""
    s = Settings(**BASE, mode='Dwustronnie', flip=flip, columns=2, rows=2)
    front, back = placements(Project(s, [Job(pairs_pdf(tmp_path, 4))]))
    for f, b in zip(front.placements, back.placements):
        assert b.source.index == f.source.index + 1
        if flip == FLIP_MB:
            assert b.slot.x == pytest.approx(s.sheet_w - f.slot.x - f.slot.w) and b.slot.rotation == f.slot.rotation
        else:
            assert b.slot.y == pytest.approx(s.sheet_h - f.slot.y - f.slot.h)
            assert b.slot.rotation == (f.slot.rotation + 180) % 360


def test_validation():
    validate(Settings(**BASE, mode=TURN_MC))
    with pytest.raises(ValueError):
        validate(Settings(**BASE, flip='Bokiem'))
    with pytest.raises(ValueError):
        validate(Settings(**BASE, mode=TURN_MB, fill_pages='Nieparzystymi'))


@pytest.mark.parametrize('mode, flip', [(TURN_MC, 'Długa krawędź'), ('Dwustronnie', FLIP_MB)])
def test_project_round_trip(tmp_path, mode, flip):
    from engine import load_project, save_project
    path = tmp_path / 'praca.psimp'
    save_project(Project(Settings(**BASE, mode=mode, flip=flip), [Job(pairs_pdf(tmp_path, 1))]), str(path))
    loaded = load_project(str(path))
    assert (loaded.settings.mode, loaded.settings.flip) == (mode, flip)
