"""Programy dodatkowe: menu kafelków z ikonami (kategorie) i narzędzie „Usuń wybrane strony” (H-51)."""
import tkinter as tk

import pymupdf as fitz
import pytest

import pdftools
import tools_ui
import ui_icons


def make_pdf(folder, pages=6):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=200, height=200).insert_text((20, 40), f'strona{i + 1}')
    path = folder / 'plik.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def texts(path):
    with fitz.open(path) as doc:
        return [page.get_text().strip() for page in doc]


def test_delete_pages_keeps_order_and_source(tmp_path):
    src = make_pdf(tmp_path)
    before = open(src, 'rb').read()
    out = tmp_path / 'wynik.pdf'
    assert pdftools.delete_pages(src, str(out), '2, 4-5') == [str(out)]
    assert texts(out) == ['strona1', 'strona3', 'strona6']
    assert open(src, 'rb').read() == before
    pdftools.delete_pages(src, str(tmp_path / 'koniec.pdf'), '5-')
    assert texts(tmp_path / 'koniec.pdf') == ['strona1', 'strona2', 'strona3', 'strona4']


def test_delete_pages_refusals(tmp_path):
    src = make_pdf(tmp_path, 3)
    for bad in ('', '1-', '7', 'abc'):
        with pytest.raises(ValueError):
            pdftools.delete_pages(src, str(tmp_path / 'x.pdf'), bad)
    with pytest.raises(ValueError):
        pdftools.delete_pages(src, src, '1')                     # nie nadpisuje pliku źródłowego
    assert not (tmp_path / 'x.pdf').exists()


def test_every_tool_has_tile_icon_and_category():
    assert len({t.name for t in tools_ui.TOOLS}) == len(tools_ui.TOOLS)
    for tool in tools_ui.TOOLS:
        assert tool.category in tools_ui.CATEGORIES, tool.name
        assert ui_icons.draw_tool(tool.icon, 28).size == (28, 28)
        assert len(tool.name) <= 30, tool.name                     # mieści się na kafelku


def test_tiles_select_tool_and_run_delete(tmp_path, monkeypatch):
    src = make_pdf(tmp_path)
    root = tk.Tk()
    try:
        frame = tools_ui.PdfToolsFrame(root)
        frame.pack()
        root.update()
        tiles = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, tools_ui.ttk.Radiobutton):
                    tiles.append(child)
                walk(child)
        walk(frame)
        assert len(tiles) == len(tools_ui.TOOLS)
        tile = next(t for t in tiles if str(t.cget('text')) == 'Usuń wybrane strony')
        tile.invoke()
        root.update()
        assert frame.title_var.get() == 'Usuń wybrane strony' and frame.tool.name == 'Usuń wybrane strony'
        frame.inputs = [src]
        frame.range_var.set('1, 6')
        target = tmp_path / 'plik--bez_stron.pdf'
        monkeypatch.setattr(tools_ui.filedialog, 'asksaveasfilename', lambda **kw: str(target))
        frame.run()
        assert texts(target) == ['strona2', 'strona3', 'strona4', 'strona5']
    finally:
        root.destroy()
