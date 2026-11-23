"""Książka szyta ze składek — druk cyfrowy, kartki niefalcowane (H-56).

Logika (book.py): podział na składki równo, kolejność stron na kartkach, kartki na arkuszach.
Silnik: każda strona tyłu leży fizycznie za swoją stroną przodu (odwrocie), z głową w tym samym kierunku
i grzbietem w tym samym miejscu; przy grzbiecie brak spadu (strony rozkładówki stykają się).
"""
import pytest

import book
from book import ORDER_REPEAT, ORDER_SEQUENTIAL, ORDER_STACK, folios, sheets, signature_leaves


# --- logika bez PDF -------------------------------------------------------------------------------------------

@pytest.mark.parametrize('pages, leaves, expected', [
    (100, 4, [4, 4, 4, 4, 3, 3, 3]),      # przykład z pytania: bez cienkiej składki na końcu
    (64, 4, [4, 4, 4, 4]),
    (65, 4, [4, 4, 3, 3, 3]),             # 17 kartek → 5 składek: 4, 4, 3, 3, 3
    (8, 4, [2]),
    (1, 4, [1]),
    (160, 40, [40]),
])
def test_signatures_split_evenly(pages, leaves, expected):
    got = signature_leaves(pages, leaves)
    assert got == expected
    assert max(got) - min(got) <= 1 and max(got) <= leaves
    assert sum(got) * 4 - pages == book.blank_pages(pages)


def test_bad_leaf_count():
    with pytest.raises(ValueError):
        signature_leaves(10, 0)
    with pytest.raises(ValueError):
        signature_leaves(10, book.MAX_LEAVES + 1)


def reading_order(signature):
    """Strony po złożeniu i zszyciu składki: kartki włożone jedna w drugą (1 = zewnętrzna)."""
    order = [p for f in signature for p in (f.front[1], f.back[0])]
    order += [p for f in reversed(signature) for p in (f.back[1], f.front[0])]
    return order


@pytest.mark.parametrize('pages, leaves', [(8, 2), (16, 4), (100, 4), (37, 3), (5, 1)])
def test_folded_signatures_read_in_order(pages, leaves):
    result = folios(list(range(1, pages + 1)), leaves)
    flat = []
    for number in sorted({f.signature for f in result}):
        flat += reading_order([f for f in result if f.signature == number])
    padded = list(range(1, pages + 1)) + [None] * book.blank_pages(pages)
    assert flat == padded


def test_eight_pages_two_leaves():
    outer, inner = folios(list(range(1, 9)), 4)
    assert (outer.front, outer.back) == ((8, 1), (2, 7))
    assert (inner.front, inner.back) == ((6, 3), (4, 5))


def test_sheet_orders():
    f = folios(list(range(1, 21)), 5)          # 5 kartek
    seq = sheets(f, 2, 2, ORDER_SEQUENTIAL)
    assert [[x.leaf if x else None for x in sheet] for sheet in seq] == [[1, 2], [3, 4], [5, 1], [2, 3], [4, 5]]
    stack = sheets(f, 2, 1, ORDER_STACK)       # 3 arkusze; pole 1: kartki 1–3, pole 2: kartki 4–5
    assert [[x.leaf if x else None for x in sheet] for sheet in stack] == [[1, 4], [2, 5], [3, None]]
    rep = sheets(f, 2, 3, ORDER_REPEAT)        # 3 egz. po 2 na arkuszu: seria 2 + seria 1 (bez nadprodukcji)
    assert len(rep) == 10 and rep[0] == [f[0], f[0]] and rep[5] == [f[0], None]
    with pytest.raises(ValueError):
        sheets(f, 0, 1, ORDER_STACK)
    with pytest.raises(ValueError):
        sheets(f, 2, 1, 'inaczej')


def test_summary_text():
    assert book.summary(100, 4) == '7 składek: 4 × 16 + 3 × 12 str.'
    assert book.summary(22, 4) == '2 składki: 2 × 12 str. (+2 puste na końcu)'


# --- silnik z PDF ---------------------------------------------------------------------------------------------

fitz = pytest.importorskip('pymupdf')
from engine import (BOOK, FLIP_MB, Job, Project, Settings, book_back_slot, book_info, export_pdf,  # noqa: E402
                    geometry, gross_rect, load_project, open_sources, project_sides, pt, save_project, swap_slots,
                    validate)

W, H, B = 148, 210, 3
RED = (255, 0, 0)


def book_pdf(folder, pages=20):
    """Strony A5 ze spadem 3 mm: tło na spad (niebieskie nieparzyste, żółte parzyste), czerwona głowa, numer."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=pt(W + 2 * B), height=pt(H + 2 * B))
        page.set_trimbox(fitz.Rect(pt(B), pt(B), pt(B + W), pt(B + H)))
        page.draw_rect(page.rect, color=None, fill=(1, 1, 0) if i % 2 else (0, 0, 1))
        page.draw_rect(fitz.Rect(pt(B), pt(B), pt(B + W), pt(B + 15)), color=None, fill=(1, 0, 0))
        page.insert_text((pt(B + 40), pt(B + 120)), str(i + 1), fontsize=150)
    path = folder / 'ksiazka.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def settings(**extra):
    base = dict(sheet_w=450, sheet_h=320, trim_w=W, trim_h=H, bleed=B, scale_mode='Bez skalowania', mode=BOOK,
                book_leaves=2, margin_x=6, margin_y=6, gap_x=5, gap_y=5)
    base.update(extra)
    return Settings(**base)


def sides_of(project):
    sources = open_sources(project.jobs)
    try:
        return list(project_sides(project, sources))
    finally:
        for doc in sources.values():
            doc.close()


HEAD = {0: 'up', 90: 'left', 180: 'down', 270: 'right'}   # kierunek głowy strony na arkuszu (H-53)


def mirror(s):
    """Fizyczne „za” dla tyłu arkusza (jak w dupleksie): True = odbicie w poziomie."""
    if s.flip == FLIP_MB:
        return True
    return (s.flip == 'Długa krawędź') != (s.sheet_w >= s.sheet_h)


def physical(slot, s, horizontal):
    """Prostokąt pola tyłu w układzie przodu + kierunek głowy + krawędź grzbietu (na przodzie)."""
    if horizontal:
        rect = (s.sheet_w - slot.x - slot.w, slot.y, s.sheet_w - slot.x, slot.y + slot.h)
        head = {'left': 'right', 'right': 'left'}.get(HEAD[slot.rotation], HEAD[slot.rotation])
    else:
        rect = (slot.x, s.sheet_h - slot.y - slot.h, slot.x + slot.w, s.sheet_h - slot.y)
        head = {'up': 'down', 'down': 'up'}.get(HEAD[slot.rotation], HEAD[slot.rotation])
    return tuple(round(v, 6) for v in rect), head


def spine_edge(slot, s):
    """Odcinek krawędzi grzbietu pola na arkuszu (strona bez spadu = grzbiet)."""
    gx0, gy0, gx1, gy1 = gross_rect(s, slot)
    x0, y0, x1, y1 = slot.x, slot.y, slot.x + slot.w, slot.y + slot.h
    edges = {'l': (x0, y0, x0, y1), 'r': (x1, y0, x1, y1), 't': (x0, y0, x1, y0), 'b': (x0, y1, x1, y1)}
    for name, gap in (('l', x0 - gx0), ('r', gx1 - x1), ('t', y0 - gy0), ('b', gy1 - y1)):
        if abs(gap) < 1e-9:
            return edges[name]
    raise AssertionError('pole bez grzbietu')


@pytest.mark.parametrize('extra', [
    dict(),                                                         # SRA3 poziomo, długa krawędź, obrót 90°
    dict(sheet_w=320, sheet_h=450),                                 # SRA3 pionowo, obrót 0°, odbicie w poziomie
    dict(sheet_w=320, sheet_h=450, flip='Krótka krawędź'),
    dict(flip='Krótka krawędź'),
    dict(flip=FLIP_MB, rotation='0', sheet_w=700, sheet_h=500),     # B2, offset przez markę boczną
])
def test_back_lies_behind_front(tmp_path, extra):
    s = settings(**extra)
    sides = sides_of(Project(s, [Job(book_pdf(tmp_path))]))
    horizontal = mirror(s)
    assert len(sides) % 2 == 0
    for front, back in zip(sides[0::2], sides[1::2]):
        assert (front.side, back.side) == (0, 1) and front.sheet_number == back.sheet_number
        behind = {physical(p.slot, s, horizontal)[0]: p for p in back.placements}
        for p in front.placements:
            q = behind[tuple(round(v, 6) for v in (p.slot.x, p.slot.y, p.slot.x + p.slot.w, p.slot.y + p.slot.h))]
            if p.source is None:
                continue
            j = p.source.index
            assert q.source.index == (j + 1 if j % 2 == 0 else j - 1)       # odwrocie tej samej kartki
            assert physical(q.slot, s, horizontal)[1] == HEAD[p.slot.rotation]   # głowa w tę samą stronę
            # grzbiet tyłu w tym samym miejscu co grzbiet przodu
            x0, y0, x1, y1 = spine_edge(q.slot, s)
            if horizontal:
                mirrored = (s.sheet_w - x1, y0, s.sheet_w - x0, y1)
            else:
                mirrored = (x0, s.sheet_h - y1, x1, s.sheet_h - y0)
            assert tuple(round(v, 6) for v in mirrored) == tuple(round(v, 6) for v in spine_edge(p.slot, s))


def test_layout_and_export(tmp_path):
    s = settings()
    project = Project(s, [Job(book_pdf(tmp_path))])
    g = geometry(s)
    assert (g.cols, g.rows, g.rotation, len(g.slots)) == (2, 1, 90, 4)
    sources = open_sources(project.jobs)
    assert book_info(project.jobs, sources, s) == '20 str. • 3 składki: 2 × 8 + 1 × 4 str. • 1 egz.'
    out = tmp_path / 'wynik.pdf'
    assert export_pdf(project, str(out)) == 6                      # 3 arkusze × przód i tył
    with fitz.open(out) as doc:
        img = doc[0].get_pixmap(dpi=50, alpha=False)
    k = 50 / 25.4
    front = sides_of(project)[0].placements
    left, right = front[0].slot, front[1].slot                      # strona 8 (dół) i 1 (góra), obrót 90°
    assert (front[0].source.index, front[1].source.index) == (7, 0)
    assert abs(left.y - (right.y + right.h)) < 1e-9                 # strony stykają się na grzbiecie
    fold = right.y + right.h
    x = int((right.x + right.w / 2) * k)
    assert img.pixel(x, int((fold - 1) * k)) == (0, 0, 255)         # strona 1 do samego grzbietu
    assert img.pixel(x, int((fold + 1) * k)) == (255, 255, 0)       # strona 8 od samego grzbietu (bez spadu)
    assert img.pixel(int((right.x + 3) * k), int((right.y + 40) * k)) == RED   # głowa przy lewej krawędzi


def test_errors_and_old_projects(tmp_path):
    src = book_pdf(tmp_path, 8)
    with pytest.raises(ValueError, match='lewy i prawy'):
        validate(settings(bleed_equal=False, bleed_l=3, bleed_r=2, bleed_t=3, bleed_b=3))
    validate(settings(bleed_equal=False, bleed_l=3, bleed_r=3, bleed_t=2, bleed_b=4))
    with pytest.raises(ValueError, match='Kartek'):
        validate(settings(book_leaves=0))
    with pytest.raises(ValueError, match='nakład'):
        sides_of(Project(settings(), [Job(src, copies=2), Job(src, copies=1)]))
    job = Job(src)
    job.page_roles = {'1': 'Przód'}
    with pytest.raises(ValueError, match='role'):
        sides_of(Project(settings(), [job]))
    project = Project(settings(), [Job(src)])
    side = sides_of(project)[0]
    with pytest.raises(ValueError, match='ręczna edycja'):
        swap_slots(project, side, 0, 1)
    with pytest.raises(ValueError, match='Autowypełnianie'):
        validate(settings(fill_corner='PD'))
    path = tmp_path / 'ksiazka.psimp'
    save_project(Project(settings(book_leaves=5, book_order=ORDER_STACK), [Job(src)]), str(path))
    loaded = load_project(str(path))
    assert (loaded.settings.mode, loaded.settings.book_leaves, loaded.settings.book_order) == (BOOK, 5, ORDER_STACK)
    assert Settings().book_leaves == 4 and Settings().book_order == ORDER_SEQUENTIAL   # stare projekty


def test_back_slot_rotation_rule():
    s = settings()                                                  # poziomy arkusz, długa krawędź → w pionie
    slot = geometry(s).slots[0]
    assert book_back_slot(slot, s, 'r').rotation == slot.rotation    # 90° przy odbiciu w pionie bez zmian
    s2 = settings(sheet_w=320, sheet_h=450)
    slot2 = geometry(s2).slots[0]
    assert slot2.rotation == 0 and book_back_slot(slot2, s2, 'l').rotation == 0
