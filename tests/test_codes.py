"""Generator kodów QR i Data Matrix (codes.py): treści, numery seryjne jak w starym generatorze, odczyt z PDF.

Każdy wygenerowany PDF jest renderowany i skanowany czytnikiem zxing-cpp — sprawdzamy treść, nie tylko plik.
"""
import pymupdf as fitz
import pytest

import codes

zxingcpp = pytest.importorskip('zxingcpp')
from PIL import Image  # noqa: E402


def scan(path, page_index=0):
    with fitz.open(path) as doc:
        pix = doc[page_index].get_pixmap(dpi=300, alpha=False)
        image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    # strefa ciszy dla czytnika (kod może mieć margines 0)
    canvas = Image.new('RGB', (image.width + 80, image.height + 80), 'white')
    canvas.paste(image, (40, 40))
    return [(r.format.name, r.text) for r in zxingcpp.read_barcodes(canvas)]


# --- treści QR -------------------------------------------------------------------------------------

def test_qr_payloads():
    vcard = codes.qr_payload(codes.QR_VCARD, {'first': 'Dawid', 'last': 'Gracz', 'org': 'Drukarnia; A',
                                              'phone': '+48 600 100 200', 'email': 'd@x.pl', 'city': 'Kraków'})
    assert vcard.startswith('BEGIN:VCARD\r\nVERSION:3.0\r\nN:Gracz;Dawid;;;\r\nFN:Dawid Gracz')
    assert 'ORG:Drukarnia\\; A' in vcard and 'TEL;TYPE=WORK,VOICE:+48 600 100 200' in vcard
    assert 'ADR;TYPE=WORK:;;;Kraków;;;' in vcard and vcard.endswith('END:VCARD')
    assert codes.qr_payload(codes.QR_MECARD, {'name': 'Gracz, Dawid', 'phone': '600'}) == \
        'MECARD:N:Gracz\\, Dawid;TEL:600;;'
    assert codes.qr_payload(codes.QR_EMAIL, {'to': 'a@b.pl', 'subject': 'Zamówienie 12'}) == \
        'mailto:a@b.pl?subject=Zam%C3%B3wienie%2012'
    assert codes.qr_payload(codes.QR_PHONE, {'phone': '+48 600-100-200'}) == 'tel:+48600100200'
    assert codes.qr_payload(codes.QR_SMS, {'phone': '600 100 200', 'body': 'Hej'}) == 'SMSTO:600100200:Hej'
    assert codes.qr_payload(codes.QR_WIFI, {'ssid': 'Drukarnia', 'password': 'tajne;1'}) == \
        'WIFI:T:WPA;S:Drukarnia;P:tajne\\;1;;'
    assert codes.qr_payload(codes.QR_WIFI, {'ssid': 'Gość', 'security': 'brak', 'hidden': 'tak'}) == \
        'WIFI:T:nopass;S:Gość;H:true;;'
    assert codes.qr_payload(codes.QR_GEO, {'lat': '52,2297', 'lon': '21.0122'}) == 'geo:52.2297,21.0122'
    event = codes.qr_payload(codes.QR_EVENT, {'summary': 'Targi', 'start': '2026-11-03 9:30', 'end': '2026-11-03'})
    assert 'DTSTART:20261103T093000' in event and 'DTEND:20261103' in event
    assert codes.qr_payload(codes.QR_TRANSFER, {'name': 'Drukarnia', 'account': '12 1234 5678 9012 3456 7890 1234',
                                                'amount': '123,45', 'title': 'FV 12/2026', 'nip': '123-456-78-90'}) == \
        '1234567890|PL|12123456789012345678901234|012345|Drukarnia|FV 12/2026|||'
    assert codes.url_payload('drukarnia.pl/oferta') == 'https://drukarnia.pl/oferta'
    assert codes.url_payload('http://x.pl') == 'http://x.pl'


def test_qr_payload_errors():
    for kind, values in ((codes.QR_VCARD, {'first': 'Dawid'}), (codes.QR_WIFI, {'ssid': 'a', 'security': 'X'}),
                         (codes.QR_GEO, {'lat': '95', 'lon': '1'}), (codes.QR_EVENT, {'summary': 'a', 'start': 'jutro'}),
                         (codes.QR_TRANSFER, {'name': 'a', 'account': '123', 'amount': '1', 'title': 't'}),
                         (codes.QR_TEXT, {}), ('Nieznany', {})):
        with pytest.raises(ValueError):
            codes.qr_payload(kind, values)


# --- numery seryjne (jak datamt.py) -----------------------------------------------------------------

def test_serial_values_like_old_generator():
    template = '[)>$12$SER {SER}$PNR 04HC-V3-03$$'
    assert codes.serial_values(template, '04HC-S', 1, 3) == [
        '[)>$12$SER 04HC-S1$PNR 04HC-V3-03$$', '[)>$12$SER 04HC-S2$PNR 04HC-V3-03$$',
        '[)>$12$SER 04HC-S3$PNR 04HC-V3-03$$']
    assert codes.serial_values('SN{SER}', 'A', 8, 12, step=2, digits=4) == ['SNA0008', 'SNA0010', 'SNA0012']
    assert codes.serial_values('[)>{RS}06{GS}S{SER}{RS}{EOT}', '', 5, 5) == ['[)>\x1e06\x1dS5\x1e\x04']
    for args in (('bez', 'A', 1, 2), ('{SER}', 'A', 5, 1), ('{SER}', 'A', 1, 2, 0), ('{SER}', 'A', 1, 50000)):
        with pytest.raises(ValueError):
            codes.serial_values(*args)


def test_text_lines_and_names():
    assert codes.text_lines(' a \r\n\n b\n') == ['a', 'b']
    used = set()
    assert codes.safe_name('[)>$12$SER 04HC-S1', used) == '12_SER_04HC_S1'
    assert codes.safe_name('[)>$12$SER 04HC-S1', used) == '12_SER_04HC_S1_2'


# --- PDF: wektorowo i czytelnie -----------------------------------------------------------------------

def test_qr_pdf_scans_back(tmp_path):
    vcard = codes.qr_payload(codes.QR_VCARD, {'first': 'Dawid', 'last': 'Gracz', 'phone': '600100200'})
    items = [(text, codes.matrix(codes.QR, text, 'H')) for text in ('https://drukarnia.pl/ąę', vcard)]
    out = tmp_path / 'qr.pdf'
    assert codes.render_pdf(items, str(out), size_mm=25, quiet=4, caption=True) == [str(out)]
    assert scan(out, 0) == [('QRCode', 'https://drukarnia.pl/ąę')]
    assert scan(out, 1)[0][1].replace('\n', '\r\n') == vcard or scan(out, 1)[0][1] == vcard
    with fitz.open(out) as doc:
        assert len(doc) == 2
        assert not doc[0].get_images()                                 # wektor, bez bitmap
        side = (len(items[0][1]) + 8) * 25 / len(items[0][1])          # kod 25 mm + 2 × 4 moduły
        assert doc[0].rect.width / codes.MM == pytest.approx(side, abs=0.01)
        assert 'https://drukarnia.pl/ąę' in doc[0].get_text()           # podpis pod kodem


def test_datamatrix_serials_separate_files_scan_back(tmp_path):
    values = codes.serial_values('[)>$12$SER {SER}$PNR 04HC-V3-03$$', '04HC-S', 1, 3)
    items = [(v, codes.matrix(codes.DATAMATRIX, v)) for v in values]
    written = codes.render_pdf(items, str(tmp_path / 'dm'), size_mm=12, quiet=2, separate=True)
    assert [p.rsplit('\\', 1)[-1].rsplit('/', 1)[-1] for p in written] == [
        '12_SER_04HC_S1_PNR_04HC_V3_03.pdf', '12_SER_04HC_S2_PNR_04HC_V3_03.pdf', '12_SER_04HC_S3_PNR_04HC_V3_03.pdf']
    for path, value in zip(written, values):
        assert scan(path) == [('DataMatrix', value)]


def test_datamatrix_polish_text_square_and_colour(tmp_path):
    cells = codes.matrix(codes.DATAMATRIX, 'Zażółć gęślą jaźń 123')
    assert len(cells) == len(cells[0])                                   # kwadratowy
    out = tmp_path / 'pl.pdf'
    codes.render_pdf([('Zażółć gęślą jaźń 123', cells)], str(out), color=(100, 0, 0, 0), transparent=True)
    assert scan(out) == [('DataMatrix', 'Zażółć gęślą jaźń 123')]
    with fitz.open(out) as doc:
        assert '1 0 0 0 k' in doc[0].read_contents().decode('latin-1')  # wypełnienie C 100 %


def test_render_validation(tmp_path):
    cells = codes.matrix(codes.QR, 'x')
    for kwargs in (dict(size_mm=1), dict(quiet=30), dict(color=(0, 0, 0, 120))):
        with pytest.raises(ValueError):
            codes.render_pdf([('x', cells)], str(tmp_path / 'x.pdf'), **kwargs)
    with pytest.raises(ValueError):
        codes.matrix(codes.QR, 'x', 'Z')
    with pytest.raises(ValueError):
        codes.render_pdf([], str(tmp_path / 'x.pdf'))
