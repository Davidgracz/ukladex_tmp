"""„Rozetnij strony pdf” i „Rozetnij rozkładówki” — programy dodatkowe Impozycjonera 4.

E1: ilość części (kolumn × wierszy), zakres stron, zakładki na krawędziach (szerokość; z lewej albo prawej, z góry
albo z dołu), znacznik zakładki (długość, grubość, kolor) i opis zakładek; rozkładówki: rozmiar TrimBox podany albo
odczytany z pierwszej strony, rozcinanie pierwszej / ostatniej strony na życzenie.
E2 (REA): nowy dokument, strony w rozmiarze części, treść wstawiana z przycięciem; przy rozkładówkach TrimBox i spady.
Decyzje własne: H-46, H-47.
"""
import pymupdf as fitz
import pytest

import pageops
import pdftools

MM = pdftools.MM


def size(page):
    return round(page.rect.width / MM, 2), round(page.rect.height / MM, 2)


def colour(page, x_mm, y_mm):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return pix.pixel(int(x_mm * MM * 2), int(y_mm * MM * 2))


# --- czyste reguły -------------------------------------------------------------------------------

def test_grid_parts_without_and_with_tabs():
    parts = pageops.grid_parts(200, 100, 2, 2)
    assert [(p['col'], p['row'], p['rect']) for p in parts] == [
        (1, 1, (0, 0, 100, 50)), (2, 1, (100, 0, 200, 50)), (1, 2, (0, 50, 100, 100)), (2, 2, (100, 50, 200, 100))]
    tabbed = pageops.grid_parts(200, 100, 2, 2, tab=10, tab_left=True, tab_top=True)
    assert tabbed[0]['rect'] == (0, 0, 100, 50) and not tabbed[0]['strips']           # lewa górna — bez sąsiadów
    assert tabbed[1]['rect'] == (90, 0, 200, 50)                                       # zakładka z lewej
    assert tabbed[1]['strips'][0][1:] == ((1, 1), 'left') and tabbed[1]['joins'] == [(100, 0, 100, 50)]
    assert tabbed[3]['rect'] == (90, 40, 200, 100)                                     # z lewej i z góry
    right_bottom = pageops.grid_parts(200, 100, 2, 2, tab=10, tab_left=False, tab_top=False)
    assert right_bottom[0]['rect'] == (0, 0, 110, 60) and right_bottom[3]['rect'] == (100, 50, 200, 100)


def test_grid_validation_and_ticks():
    for args in ((100, 100, 1, 1), (100, 100, 0, 2), (100, 100, 51, 1), (100, 100, 2, 1, 50), (100, 100, 2, 1, -1)):
        with pytest.raises(ValueError):
            pageops.grid_parts(*args)
    assert pageops.join_ticks((100, 0, 100, 50), 5) == [(100, 0, 100, 5), (100, 45, 100, 50)]
    assert pageops.join_ticks((0, 50, 80, 50), 100) == [(0, 50, 40, 50), (40, 50, 80, 50)]
    assert pageops.join_ticks((0, 0, 0, 10), 0) == []


def test_spread_halves():
    # rozkładówka 2 × A5 z 3 mm spadu, TrimBox ustawiony
    left, right = pageops.spread_halves((3, 3, 299, 213), (0, 0, 302, 216), 148, 210)
    assert left == ((0, 0, 154, 216), (3, 3, 151, 213))                               # spad przy grzbiecie 3 mm
    assert right == ((148, 0, 302, 216), (151, 3, 299, 213))
    assert pageops.spread_halves((0, 0, 148, 210), (0, 0, 148, 210), 148, 210) is None # pojedyncza strona
    # TrimBox nieustawiony (= MediaBox ze spadem): wyśrodkowany obszar 2 × szer.
    left, _ = pageops.spread_halves((0, 0, 302, 216), (0, 0, 302, 216), 148, 210)
    assert left[1] == (3, 3, 151, 213)
    with pytest.raises(ValueError):
        pageops.spread_halves((0, 0, 210, 297), (0, 0, 210, 297), 148, 210)


# --- PDF -----------------------------------------------------------------------------------------

def quadrants(folder, rotation=0):
    """Strona 200 × 100 mm w czterech kolorach (ćwiartki) z napisem."""
    doc = fitz.open()
    page = doc.new_page(width=200 * MM, height=100 * MM)
    for (x0, y0), c in (((0, 0), (1, 0, 0)), ((100, 0), (0, 1, 0)), ((0, 50), (0, 0, 1)), ((100, 50), (1, 1, 0))):
        page.draw_rect(fitz.Rect(x0 * MM, y0 * MM, (x0 + 100) * MM, (y0 + 50) * MM), color=None, fill=c)
    page.insert_text((10 * MM, 20 * MM), 'PLAKAT', fontsize=20)
    if rotation:
        page.set_rotation(rotation)
    doc.new_page(width=50 * MM, height=50 * MM)          # druga strona — poza zakresem
    path = folder / 'plakat.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def test_split_grid_vector_parts_with_tabs_and_labels(tmp_path):
    src = quadrants(tmp_path)
    out = tmp_path / 'czesci.pdf'
    pdftools.split_grid(src, str(out), 2, 2, tab=10, mark_length=5, mark_pt=0.5, describe=True, pages_text='1')
    with fitz.open(out) as doc:
        assert len(doc) == 5                                            # 4 części + strona 2 bez zmian
        assert [size(p) for p in doc] == [(100, 50), (110, 50), (100, 60), (110, 60), (50, 50)]
        assert 'PLAKAT' in doc[0].get_text()                            # wektorowo
        assert colour(doc[0], 50, 25) == (255, 0, 0)
        assert colour(doc[1], 1, 25) == (255, 0, 0)                     # zakładka: treść lewego sąsiada
        assert colour(doc[1], 60, 25) == (0, 255, 0)
        assert 'zakładka na część 1×1' in doc[1].get_text()
        lines = [i for d in doc[1].get_drawings() for i in d['items'] if i[0] == 'l']
        assert len(lines) == 2                                          # dwie kreski znacznika na styku


def test_split_grid_rotated_page_uses_visible_orientation(tmp_path):
    src = quadrants(tmp_path, rotation=90)                              # widoczna 100 × 200
    out = tmp_path / 'r.pdf'
    pdftools.split_grid(src, str(out), 1, 2, pages_text='1')
    with fitz.open(src) as source, fitz.open(out) as doc:
        assert [size(p) for p in doc][:2] == [(100, 100), (100, 100)]
        for x, y in ((10, 10), (90, 10), (10, 90), (90, 90), (10, 110), (90, 190)):
            part, dy = (doc[0], 0) if y < 100 else (doc[1], 100)
            assert colour(part, x, y - dy) == colour(source[0], x, y)   # jak widoczna strona źródłowa
        assert 'PLAKAT' in doc[0].get_text() + doc[1].get_text()


def test_split_grid_refuses_bad_input(tmp_path):
    src = quadrants(tmp_path)
    with pytest.raises(ValueError):
        pdftools.split_grid(src, str(tmp_path / 'x.pdf'), 2, 2, color=(0, 0, 0, 120))
    with pytest.raises(ValueError):
        pdftools.split_grid(src, src, 2, 2)
    with pytest.raises(ValueError):
        pdftools.split_grid(src, str(tmp_path / 'x.pdf'), 2, 2, tab=60)


def booklet(folder):
    """Okładka A5 (pojedyncza), dwie rozkładówki 2 × A5 ze spadem 3 mm (lewa czerwona, prawa zielona), tył A5."""
    doc = fitz.open()
    cover = doc.new_page(width=148 * MM, height=210 * MM)
    cover.insert_text((20, 40), 'OKLADKA')
    for _ in range(2):
        page = doc.new_page(width=302 * MM, height=216 * MM)
        page.draw_rect(fitz.Rect(0, 0, 151 * MM, 216 * MM), color=None, fill=(1, 0, 0))
        page.draw_rect(fitz.Rect(151 * MM, 0, 302 * MM, 216 * MM), color=None, fill=(0, 1, 0))
        page.set_trimbox(fitz.Rect(3 * MM, 3 * MM, 299 * MM, 213 * MM))
    doc.new_page(width=148 * MM, height=210 * MM)
    path = folder / 'broszura.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def test_split_spreads_reads_size_from_first_page(tmp_path):
    src = booklet(tmp_path)
    out = tmp_path / 'strony.pdf'
    pdftools.split_spreads(src, str(out))
    with fitz.open(out) as doc:
        assert len(doc) == 6
        assert size(doc[0]) == (148, 210) and 'OKLADKA' in doc[0].get_text()
        left, right = doc[1], doc[2]
        assert size(left) == (154, 216) and size(right) == (154, 216)
        assert [round(v / MM, 2) for v in left.trimbox] == [3, 3, 151, 213]
        assert [round(v / MM, 2) for v in right.trimbox] == [3, 3, 151, 213]
        assert colour(left, 150, 100) == (255, 0, 0) and colour(left, 153, 100) == (0, 255, 0)   # spad grzbietu
        assert colour(right, 100, 100) == (0, 255, 0)


def test_split_spreads_given_size_and_first_last_switches(tmp_path):
    src = booklet(tmp_path)
    out = tmp_path / 's.pdf'
    with pytest.raises(ValueError, match='nie jest rozkładówką'):
        pdftools.split_spreads(src, str(out), 200, 280)
    pdftools.split_spreads(src, str(out), 148, 210, split_first=True, split_last=True)
    with fitz.open(out) as doc:
        assert len(doc) == 6                                    # okładki mają rozmiar pojedynczej strony — bez zmian
