"""Autowypełnianie arkusza (autofill.py, H-49) — okno „Autowypełnianie arkusza” Impozycjonera 4 (E1).

Narożnik startowy LG/PG/LD/PD, kierunek wiersze/kolumny, strony kolejno / w stosie, powtórzenia każdej strony,
wszystkie / nieparzyste / parzyste, parzyste po każdej nieparzystej albo po wszystkich nieparzystych.
"""
import pymupdf as fitz
import pytest

import autofill
from engine import (Job, Project, Settings, fill_slots, load_project, open_sources, project_sides, pt, save_project,
                    validate)

# siatka 3 kolumny × 2 wiersze, pola w kolejności silnika (wierszami od LG)
CELLS = [(c, r) for r in range(2) for c in range(3)]


def test_slot_order_corners_and_direction():
    assert autofill.slot_order(CELLS, 'LG', False) == [0, 1, 2, 3, 4, 5]      # = dotychczasowa kolejność
    assert autofill.slot_order(CELLS, 'PG', False) == [2, 1, 0, 5, 4, 3]
    assert autofill.slot_order(CELLS, 'LD', False) == [3, 4, 5, 0, 1, 2]
    assert autofill.slot_order(CELLS, 'PD', False) == [5, 4, 3, 2, 1, 0]
    assert autofill.slot_order(CELLS, 'LG', True) == [0, 3, 1, 4, 2, 5]       # kolumnami
    assert autofill.slot_order(CELLS, 'PD', True) == [5, 2, 4, 1, 3, 0]
    with pytest.raises(ValueError):
        autofill.slot_order(CELLS, 'XX', False)


def test_sequence_parity_even_last_and_repeat():
    pages = [1, 2, 3, 4, 5]
    number = lambda p: p
    assert autofill.sequence(pages, number, autofill.PAGES_ALL, False, 1) == pages
    assert autofill.sequence(pages, number, autofill.PAGES_ODD, False, 1) == [1, 3, 5]
    assert autofill.sequence(pages, number, autofill.PAGES_EVEN, False, 2) == [2, 2, 4, 4]
    assert autofill.sequence(pages, number, autofill.PAGES_ALL, True, 1) == [1, 3, 5, 2, 4]   # NNNPP
    assert autofill.sequence([1, None, 2], lambda p: p, autofill.PAGES_ODD, False, 1) == [1]   # wakat tylko przy „wszystkimi”
    for bad in (0, 1001, 1.5):
        with pytest.raises(ValueError):
            autofill.sequence(pages, number, autofill.PAGES_ALL, False, bad)


def test_sheets_sequential_and_stack():
    units = list(range(1, 9))
    assert autofill.sheets(units, 4, False) == [[1, 2, 3, 4], [5, 6, 7, 8]]
    assert autofill.sheets(units, 4, True) == [[1, 3, 5, 7], [2, 4, 6, 8]]   # pole k: kolejne strony w stosie
    assert autofill.sheets(list(range(1, 8)), 3, True) == [[1, 4, 7], [2, 5], [3, 6]]
    assert autofill.sheets([], 4, True) == []


# --- silnik i PDF --------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=0, margin_x=10, margin_y=10, gap_x=5, gap_y=5,
            rotation='0', columns=2, rows=2, crop_marks=False)


def make_pdf(folder, pages):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40))
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def layout(project):
    """[(strona arkusza, [(kol., wiersz, nr strony)])]"""
    sources = open_sources(project.jobs)
    try:
        return [[(p.slot.col, p.slot.row, None if p.source is None else p.source.index + 1) for p in side.placements]
                for side in project_sides(project, sources)]
    finally:
        for doc in sources.values():
            doc.close()


def test_default_is_unchanged_and_corner_moves_pages(tmp_path):
    src = make_pdf(tmp_path, 4)
    s = Settings(**BASE)
    assert [(x.col, x.row) for x in fill_slots(s)] == [(0, 0), (1, 0), (0, 1), (1, 1)]
    assert layout(Project(s, [Job(src)])) == [[(0, 0, 1), (1, 0, 2), (0, 1, 3), (1, 1, 4)]]
    pd = Settings(**BASE, fill_corner='PD', fill_columns=True)
    assert layout(Project(pd, [Job(src)])) == [[(1, 1, 1), (1, 0, 2), (0, 1, 3), (0, 0, 4)]]


def test_stack_repeat_and_parity_on_sheets(tmp_path):
    src = make_pdf(tmp_path, 8)
    stack = Settings(**BASE, fill_stack=True)
    assert [[n for *_, n in side] for side in layout(Project(stack, [Job(src)]))] == [[1, 3, 5, 7], [2, 4, 6, 8]]
    odd_twice = Settings(**BASE, fill_pages=autofill.PAGES_ODD, fill_repeat=2)
    assert [[n for *_, n in side] for side in layout(Project(odd_twice, [Job(src)]))] == [[1, 1, 3, 3], [5, 5, 7, 7]]
    even_last = Settings(**BASE, fill_even_last=True)
    assert [[n for *_, n in side] for side in layout(Project(even_last, [Job(src)]))] == [[1, 3, 5, 7], [2, 4, 6, 8]]


def test_duplex_keeps_pairs_and_mirrors_back(tmp_path):
    src = make_pdf(tmp_path, 4)                                    # pary (1,2), (3,4)
    s = Settings(**BASE, mode='Dwustronnie', fill_corner='PG', fill_repeat=2)
    front, back = layout(Project(s, [Job(src)]))
    assert [n for *_, n in front] == [1, 1, 3, 3] and [n for *_, n in back] == [2, 2, 4, 4]
    assert front[0][:2] == (1, 0)                                   # start w prawym górnym rogu
    with pytest.raises(ValueError, match='pary'):
        validate(Settings(**BASE, mode='Dwustronnie', fill_pages=autofill.PAGES_ODD))
    with pytest.raises(ValueError, match='jednostronnym i dwustronnym'):
        validate(Settings(**BASE, mode='Ekonomiczny', fill_stack=True))


def test_project_roundtrip_and_old_file(tmp_path):
    src = make_pdf(tmp_path, 2)
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(**BASE, fill_corner='LD', fill_stack=True, fill_repeat=3), [Job(src)]), str(path))
    loaded = load_project(str(path)).settings
    assert (loaded.fill_corner, loaded.fill_stack, loaded.fill_repeat) == ('LD', True, 3)
    assert Settings().fill_corner == 'LG' and Settings().fill_repeat == 1
