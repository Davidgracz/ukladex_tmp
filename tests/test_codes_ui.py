"""Panele generatorów kodów w „Programach dodatkowych”: wpisany tekst → PDF → skan (zxing-cpp)."""
import tkinter as tk
from pathlib import Path

import pymupdf as fitz
import pytest

import codes
import codes_ui
import tools_ui

zxingcpp = pytest.importorskip('zxingcpp')
from PIL import Image  # noqa: E402


def scan_all(path):
    found = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300, alpha=False)
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            canvas = Image.new('RGB', (image.width + 80, image.height + 80), 'white')
            canvas.paste(image, (40, 40))
            found += [(r.format.name, r.text) for r in zxingcpp.read_barcodes(canvas)]
    return found


@pytest.fixture
def frame(monkeypatch, tk_root):
    root = tk_root
    errors = []
    monkeypatch.setattr(codes_ui.messagebox, 'showerror', lambda title, text, **k: errors.append(text))
    tools = tools_ui.PdfToolsFrame(root)
    tools.pack()
    tools.errors = errors
    yield tools
    tools.destroy()


def select(tools, name):
    tools.tool_var.set(name)
    tools._update()
    tools.update()
    return tools.custom_panels.get(tools.tool.custom)


def test_switching_shows_panel_instead_of_file_list(frame):
    assert frame.files_frame.winfo_manager() == 'grid'
    panel = select(frame, 'Kody QR')
    assert isinstance(panel, codes_ui.QrPanel) and panel.winfo_manager() == 'grid'
    assert frame.files_frame.winfo_manager() == '' and frame.start_button.winfo_manager() == ''
    select(frame, 'Połącz pliki PDF')
    assert frame.files_frame.winfo_manager() == 'grid' and panel.winfo_manager() == ''


def test_qr_typed_urls_and_vcard(frame, tmp_path, monkeypatch):
    panel = select(frame, 'Kody QR')
    panel.text.insert('1.0', 'drukarnia.pl\nhttps://drukarnia.pl/kontakt\n')
    out = tmp_path / 'qr.pdf'
    monkeypatch.setattr(codes_ui.filedialog, 'asksaveasfilename', lambda **k: str(out))
    panel.generate()
    assert frame.errors == []
    assert scan_all(out) == [('QRCode', 'https://drukarnia.pl'), ('QRCode', 'https://drukarnia.pl/kontakt')]
    panel.type_var.set(codes.QR_VCARD)
    panel._show_type()
    panel.field_vars['first'].set('Dawid')
    panel.field_vars['last'].set('Gracz')
    panel.field_vars['phone'].set('600100200')
    panel.ec_var.set('H')
    card = tmp_path / 'wizytowka.pdf'
    monkeypatch.setattr(codes_ui.filedialog, 'asksaveasfilename', lambda **k: str(card))
    panel.generate()
    (fmt, text), = scan_all(card)
    assert fmt == 'QRCode' and 'FN:Dawid Gracz' in text and 'TEL;TYPE=WORK,VOICE:600100200' in text
    panel.field_vars['last'].set('')
    panel.generate()                                                    # brak nazwiska → komunikat, bez pliku
    assert frame.errors and 'Nazwisko' in frame.errors[-1]


def test_datamatrix_serial_numbers_like_old_generator(frame, tmp_path, monkeypatch):
    panel = select(frame, 'Kody Data Matrix')
    panel.mode_var.set('serial')
    panel._show_mode()
    assert panel.separate_var.get() is True                             # jak stary generator: osobne pliki
    panel.serial_vars['start'].set('7')
    panel.serial_vars['end'].set('9')
    assert 'Kodów: 3' in panel.sample_var.get() and '04HC-S7' in panel.sample_var.get()
    folder = tmp_path / 'serie'
    monkeypatch.setattr(codes_ui.filedialog, 'askdirectory', lambda **k: str(folder))
    panel.generate()
    files = sorted(folder.iterdir())
    assert [f.name for f in files] == [f'12_SER_04HC_S{n}_PNR_04HC_V3_03.pdf' for n in (7, 8, 9)]
    assert scan_all(files[0]) == [('DataMatrix', '[)>$12$SER 04HC-S7$PNR 04HC-V3-03$$')]


def test_datamatrix_typed_text_one_pdf(frame, tmp_path, monkeypatch):
    panel = select(frame, 'Kody Data Matrix')
    panel.text.insert('1.0', 'Paczka 1 – Kraków\nPaczka 2 – Gdańsk')
    out = tmp_path / 'dm.pdf'
    monkeypatch.setattr(codes_ui.filedialog, 'asksaveasfilename', lambda **k: str(out))
    panel.generate()
    assert scan_all(out) == [('DataMatrix', 'Paczka 1 – Kraków'), ('DataMatrix', 'Paczka 2 – Gdańsk')]


def test_ean_typed_codes(frame, tmp_path, monkeypatch):
    panel = select(frame, 'Kody EAN-13 / EAN-8')
    panel.text.insert('1.0', '590123412345\nzły\n4006381333931\n')
    out = tmp_path / 'ean.pdf'
    monkeypatch.setattr(codes_ui.filedialog, 'asksaveasfilename', lambda **k: str(out))
    panel.generate()
    assert [text for _, text in scan_all(out)] == ['5901234123457', '4006381333931']
    assert 'pominięto wiersz 2' in frame.log.get('1.0', 'end')


def test_load_txt_into_text_box(frame, tmp_path, monkeypatch):
    panel = select(frame, 'Kody Data Matrix')
    source = tmp_path / 'kody.txt'
    source.write_text('A1\nA2\n\nA3\n', encoding='utf-8')
    monkeypatch.setattr(codes_ui.filedialog, 'askopenfilename', lambda **k: str(source))
    panel._load_txt()
    assert panel.values() == ['A1', 'A2', 'A3'] and panel.count_var.get() == 'kodów: 3'
