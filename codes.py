"""Generator kodów 2D do druku: QR (różne rodzaje treści) i Data Matrix (zwykły i numery seryjne), wektorowo.

Kody tworzy biblioteka zxing-cpp (Apache-2.0): QR z poziomem korekcji L/M/Q/H, Data Matrix z UTF-8 (polskie znaki).
Tu jest logika treści i rysowanie modułów jako prostokątów w PDF (bez bitmap).

Numery seryjne — jak w generatorze Data Matrix Dawida Gracza (datamt.py, 2024): wzór z `{SER}`, w miejsce którego
trafia prefiks produktu + kolejny numer od–do; każdy kod we własnym pliku nazwanym od treści. Rozszerzenia: krok,
dopełnianie numeru zerami, znaki sterujące {GS}/{RS}/{EOT} we wzorze, wszystkie kody w jednym PDF.
Rodzaje treści QR (Imp4 ma generator QR z rozmiarem, marginesem w modułach, korekcją L/M/Q/H, kolorem, tłem
przezroczystym i kodami z pliku .txt — E1): formaty treści są publicznymi konwencjami czytników (H-52).
"""
from __future__ import annotations

import re
from pathlib import Path

QR = 'QR'
DATAMATRIX = 'Data Matrix'
EC_LEVELS = ('L', 'M', 'Q', 'H')     # L 7 %, M 15 %, Q 25 %, H 30 % (E1)
MAX_CODES = 20000

# --- treści QR ------------------------------------------------------------------------------------

QR_TEXT = 'Tekst'
QR_URL = 'Strona WWW'
QR_VCARD = 'Wizytówka (vCard)'
QR_MECARD = 'Wizytówka (MeCard)'
QR_EMAIL = 'E-mail'
QR_PHONE = 'Telefon'
QR_SMS = 'SMS'
QR_WIFI = 'Wi-Fi'
QR_GEO = 'Lokalizacja (mapa)'
QR_EVENT = 'Wydarzenie (kalendarz)'
QR_TRANSFER = 'Przelew (PL)'

# (klucz, etykieta, wymagane)
QR_FIELDS: dict[str, tuple[tuple[str, str, bool], ...]] = {
    QR_TEXT: (),
    QR_URL: (),
    QR_VCARD: (('first', 'Imię', False), ('last', 'Nazwisko', True), ('org', 'Firma', False),
               ('title', 'Stanowisko', False), ('phone', 'Telefon', False), ('mobile', 'Telefon komórkowy', False),
               ('email', 'E-mail', False), ('url', 'Strona WWW', False), ('street', 'Ulica i numer', False),
               ('city', 'Miasto', False), ('zip', 'Kod pocztowy', False), ('country', 'Kraj', False),
               ('note', 'Notatka', False)),
    QR_MECARD: (('name', 'Imię i nazwisko', True), ('phone', 'Telefon', False), ('email', 'E-mail', False),
                ('url', 'Strona WWW', False), ('address', 'Adres', False), ('note', 'Notatka', False)),
    QR_EMAIL: (('to', 'Adres e-mail', True), ('subject', 'Temat', False), ('body', 'Treść', False)),
    QR_PHONE: (('phone', 'Numer telefonu', True),),
    QR_SMS: (('phone', 'Numer telefonu', True), ('body', 'Treść SMS', False)),
    QR_WIFI: (('ssid', 'Nazwa sieci (SSID)', True), ('password', 'Hasło', False),
              ('security', 'Zabezpieczenie (WPA / WEP / brak)', False), ('hidden', 'Sieć ukryta (tak / nie)', False)),
    QR_GEO: (('lat', 'Szerokość geograficzna (np. 52.2297)', True), ('lon', 'Długość geograficzna (np. 21.0122)', True)),
    QR_EVENT: (('summary', 'Nazwa wydarzenia', True), ('start', 'Początek (RRRR-MM-DD GG:MM)', True),
               ('end', 'Koniec (RRRR-MM-DD GG:MM)', False), ('location', 'Miejsce', False),
               ('description', 'Opis', False)),
    QR_TRANSFER: (('name', 'Odbiorca (do 20 znaków)', True), ('account', 'Numer rachunku (26 cyfr)', True),
                  ('amount', 'Kwota w zł (np. 123,45)', True), ('title', 'Tytuł (do 32 znaków)', True),
                  ('nip', 'NIP odbiorcy (opcjonalnie)', False)),
}
QR_TYPES = tuple(QR_FIELDS)
QR_MULTI = (QR_TEXT, QR_URL)       # typy, w których każdy wiersz pola tekstowego to osobny kod


def _escape_mecard(value: str) -> str:
    return re.sub(r'([\\;,:"])', r'\\\1', value)


def _escape_vcard(value: str) -> str:
    return value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def _required(kind: str, values: dict) -> dict:
    clean = {key: str(values.get(key, '') or '').strip() for key, _, _ in QR_FIELDS[kind]}
    missing = [label for key, label, required in QR_FIELDS[kind] if required and not clean[key]]
    if missing:
        raise ValueError(f'{kind}: uzupełnij pola: {", ".join(missing)}')
    return clean


def _event_time(text: str) -> str:
    match = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2}))?', text.strip())
    if not match:
        raise ValueError(f'Data wydarzenia: wpisz RRRR-MM-DD albo RRRR-MM-DD GG:MM, nie „{text}”')
    y, mo, d, h, mi = match.groups()
    if h is None:
        return f'{y}{mo}{d}'
    return f'{y}{mo}{d}T{int(h):02d}{mi}00'


def qr_payload(kind: str, values: dict) -> str:
    """Treść kodu QR dla danego rodzaju (pola z QR_FIELDS). Brak pól wymaganych → ValueError po polsku."""
    if kind not in QR_FIELDS:
        raise ValueError(f'Nieznany rodzaj kodu QR: {kind}')
    if kind in QR_MULTI:
        raise ValueError('Tekst i strona WWW: treść podaje się w polu tekstowym (jeden kod w wierszu)')
    v = _required(kind, values)
    if kind == QR_VCARD:
        lines = ['BEGIN:VCARD', 'VERSION:3.0', f'N:{_escape_vcard(v["last"])};{_escape_vcard(v["first"])};;;',
                 f'FN:{_escape_vcard((v["first"] + " " + v["last"]).strip())}']
        for key, tag in (('org', 'ORG'), ('title', 'TITLE'), ('phone', 'TEL;TYPE=WORK,VOICE'),
                         ('mobile', 'TEL;TYPE=CELL'), ('email', 'EMAIL'), ('url', 'URL'), ('note', 'NOTE')):
            if v[key]:
                lines.append(f'{tag}:{_escape_vcard(v[key])}')
        if any(v[k] for k in ('street', 'city', 'zip', 'country')):
            lines.append('ADR;TYPE=WORK:;;' + ';'.join(_escape_vcard(v[k]) for k in ('street', 'city')) + ';;'
                         + ';'.join(_escape_vcard(v[k]) for k in ('zip', 'country')))
        lines.append('END:VCARD')
        return '\r\n'.join(lines)
    if kind == QR_MECARD:
        parts = [f'N:{_escape_mecard(v["name"])}']
        for key, tag in (('phone', 'TEL'), ('email', 'EMAIL'), ('url', 'URL'), ('address', 'ADR'), ('note', 'NOTE')):
            if v[key]:
                parts.append(f'{tag}:{_escape_mecard(v[key])}')
        return 'MECARD:' + ';'.join(parts) + ';;'
    if kind == QR_EMAIL:
        query = '&'.join(f'{k}={_url(v[k])}' for k in ('subject', 'body') if v[k])
        return f'mailto:{v["to"]}' + (f'?{query}' if query else '')
    if kind == QR_PHONE:
        return 'tel:' + re.sub(r'[^\d+]', '', v['phone'])
    if kind == QR_SMS:
        return f'SMSTO:{re.sub(r"[^\d+]", "", v["phone"])}:{v["body"]}'
    if kind == QR_WIFI:
        security = v['security'].upper().replace('BRAK', 'nopass') or ('WPA' if v['password'] else 'nopass')
        if security not in ('WPA', 'WEP', 'nopass'):
            raise ValueError('Wi-Fi: zabezpieczenie WPA, WEP albo brak')
        hidden = v['hidden'].lower() in ('tak', 'true', '1', 'yes')
        text = f'WIFI:T:{security};S:{_escape_mecard(v["ssid"])};'
        if v['password'] and security != 'nopass':
            text += f'P:{_escape_mecard(v["password"])};'
        return text + ('H:true;' if hidden else '') + ';'
    if kind == QR_GEO:
        try:
            lat, lon = float(v['lat'].replace(',', '.')), float(v['lon'].replace(',', '.'))
        except ValueError:
            raise ValueError('Lokalizacja: wpisz liczby, np. 52.2297 i 21.0122') from None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Lokalizacja: szerokość −90…90, długość −180…180')
        return f'geo:{lat:g},{lon:g}'
    if kind == QR_EVENT:
        lines = ['BEGIN:VEVENT', f'SUMMARY:{_escape_vcard(v["summary"])}', f'DTSTART:{_event_time(v["start"])}']
        if v['end']:
            lines.append(f'DTEND:{_event_time(v["end"])}')
        for key, tag in (('location', 'LOCATION'), ('description', 'DESCRIPTION')):
            if v[key]:
                lines.append(f'{tag}:{_escape_vcard(v[key])}')
        lines.append('END:VEVENT')
        return '\r\n'.join(lines)
    # Przelew (PL): format rekomendacji ZBP dla kodów QR na fakturach (H-52)
    account = re.sub(r'\D', '', v['account'])
    if len(account) != 26:
        raise ValueError('Przelew: numer rachunku ma 26 cyfr')
    try:
        grosze = round(float(v['amount'].replace(' ', '').replace(',', '.')) * 100)
    except ValueError:
        raise ValueError('Przelew: kwota, np. 123,45') from None
    if not 0 < grosze <= 999999:
        raise ValueError('Przelew: kwota od 0,01 do 9999,99 zł')
    nip = re.sub(r'\D', '', v['nip'])
    if nip and len(nip) != 10:
        raise ValueError('Przelew: NIP ma 10 cyfr')
    if len(v['name']) > 20 or len(v['title']) > 32 or '|' in v['name'] + v['title']:
        raise ValueError('Przelew: odbiorca do 20 znaków, tytuł do 32 znaków, bez znaku |')
    return f'{nip}|PL|{account}|{grosze:06d}|{v["name"]}|{v["title"]}|||'


def _url(text: str) -> str:
    from urllib.parse import quote
    return quote(text, safe='')


def url_payload(line: str) -> str:
    line = line.strip()
    if not line:
        raise ValueError('Pusty adres strony')
    return line if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', line) else 'https://' + line


# --- wiele kodów: wiersze tekstu i numery seryjne ----------------------------------------------------

CONTROL = {'{GS}': '\x1d', '{RS}': '\x1e', '{EOT}': '\x04'}


def text_lines(text: str) -> list[str]:
    """Niepuste wiersze (jeden kod w wierszu), bez białych znaków na końcach."""
    lines = [line.strip() for line in str(text).replace('\r\n', '\n').split('\n')]
    lines = [line for line in lines if line]
    if len(lines) > MAX_CODES:
        raise ValueError(f'Za dużo kodów naraz ({len(lines)}); limit {MAX_CODES}')
    return lines


def with_controls(text: str) -> str:
    for token, char in CONTROL.items():
        text = text.replace(token, char)
    return text


def serial_values(template: str, prefix: str, start: int, end: int, step: int = 1, digits: int = 0) -> list[str]:
    """Treści kodów z numerami seryjnymi: `{SER}` we wzorze → prefiks + numer (od–do, co `step`).

    Zgodne ze starym generatorem: prefiks „04HC-S”, wzór „[)>$12$SER {SER}$PNR 04HC-V3-03$$”, numery 1–3 →
    „[)>$12$SER 04HC-S1$PNR 04HC-V3-03$$”, … `digits` > 0 dopełnia numer zerami (np. 0001).
    """
    if '{SER}' not in template:
        raise ValueError('Wzór musi zawierać {SER} — w tym miejscu pojawi się numer seryjny')
    for name, value in (('Od', start), ('Do', end), ('Krok', step), ('Cyfr w numerze', digits)):
        if type(value) is not int:
            raise ValueError(f'{name}: liczba całkowita')
    if step < 1:
        raise ValueError('Krok: co najmniej 1')
    if end < start:
        raise ValueError('Numer „do” musi być większy lub równy „od”')
    if not 0 <= digits <= 20:
        raise ValueError('Cyfr w numerze: 0–20 (0 = bez dopełniania)')
    count = (end - start) // step + 1
    if count > MAX_CODES:
        raise ValueError(f'Za dużo kodów naraz ({count}); limit {MAX_CODES}')
    return [with_controls(template.replace('{SER}', f'{prefix}{number:0{digits}d}' if digits
                                           else f'{prefix}{number}'))
            for number in range(start, end + 1, step)]


def safe_name(text: str, used: set[str] | None = None) -> str:
    """Nazwa pliku z treści kodu (jak w starym generatorze: znaki inne niż litery/cyfry → _), unikalna."""
    name = re.sub(r'\W+', '_', text).strip('_')[:80] or 'kod'
    if used is not None:
        base, n = name, 2
        while name.lower() in used:
            name = f'{base}_{n}'
            n += 1
        used.add(name.lower())
    return name


# --- macierz modułów i PDF -------------------------------------------------------------------------

def matrix(kind: str, data: str, ec_level: str = 'M', square: bool = True) -> list[list[bool]]:
    """Moduły symbolu (True = ciemny), bez strefy ciszy."""
    import zxingcpp
    from PIL import Image
    if not data:
        raise ValueError('Pusta treść kodu')
    if kind == QR:
        if ec_level not in EC_LEVELS:
            raise ValueError('Poziom korekcji QR: L, M, Q albo H')
        symbol = zxingcpp.create_barcode(data, zxingcpp.BarcodeFormat.QRCode, ec_level=ec_level)
    elif kind == DATAMATRIX:
        symbol = zxingcpp.create_barcode(data, zxingcpp.BarcodeFormat.DataMatrix, force_square=square)
    else:
        raise ValueError(f'Nieznany rodzaj kodu: {kind}')
    image = Image.fromarray(symbol.to_image(scale=1, add_quiet_zones=False)).convert('L')
    width, height = image.size
    pixels = image.load()
    return [[pixels[x, y] < 128 for x in range(width)] for y in range(height)]


MM = 72 / 25.4


def render_pdf(items: list[tuple[str, list[list[bool]]]], output: str, size_mm: float = 20.0, quiet: int = 2,
               color: tuple[float, float, float, float] = (0, 0, 0, 100), transparent: bool = False,
               caption: bool = False, separate: bool = False) -> list[str]:
    """Kody wektorowo: każdy na osobnej stronie (rozmiar = kod + strefa ciszy [+ podpis]) albo w osobnych plikach.

    `size_mm` = dłuższy bok symbolu bez strefy ciszy; `quiet` = strefa ciszy w modułach; `color` = C/M/Y/K w %.
    Przy `separate` `output` jest folderem, a pliki mają nazwy z treści kodu.
    """
    import pymupdf as fitz
    if not items:
        raise ValueError('Brak kodów do zapisania')
    if not 3 <= size_mm <= 500:
        raise ValueError('Rozmiar kodu: 3–500 mm')
    if type(quiet) is not int or not 0 <= quiet <= 20:
        raise ValueError('Margines: 0–20 modułów')
    if len(color) != 4 or any(not 0 <= c <= 100 for c in color):
        raise ValueError('Kolor: C/M/Y/K w % (0–100)')
    ink = tuple(c / 100 for c in color)
    font = fitz.Font('helv')

    def draw(doc, data, cells):
        rows, cols = len(cells), len(cells[0])
        module = size_mm * MM / max(rows, cols)
        label = 7.0 if caption else 0.0
        width = (cols + 2 * quiet) * module
        height = (rows + 2 * quiet) * module + (label * 1.8 if caption else 0)
        page = doc.new_page(width=width, height=height)
        if not transparent:
            page.draw_rect(page.rect, color=None, fill=(0, 0, 0, 0), width=0)
        shape = page.new_shape()
        overlap = module * 0.02           # minimalna zakładka — bez prześwitów między modułami
        for r, row in enumerate(cells):
            c = 0
            while c < cols:
                if not row[c]:
                    c += 1
                    continue
                start = c
                while c < cols and row[c]:
                    c += 1
                x0, y0 = (quiet + start) * module, (quiet + r) * module
                shape.draw_rect(fitz.Rect(x0, y0, (quiet + c) * module + overlap, y0 + module + overlap))
        shape.finish(color=None, fill=ink, width=0)
        shape.commit()
        if caption:
            text = data.replace('\x1d', '<GS>').replace('\x1e', '<RS>').replace('\x04', '<EOT>').replace('\r\n', ' ')
            text = text.replace('\n', ' ')
            size = label
            while size > 3 and font.text_length(text, fontsize=size) > width * 0.96:
                size -= 0.25
            writer = fitz.TextWriter(page.rect)
            x = max(0.0, (width - font.text_length(text, fontsize=size)) / 2)
            writer.append(fitz.Point(x, (rows + 2 * quiet) * module + size * 1.2), text, font=font, fontsize=size)
            writer.write_text(page, color=ink)

    written = []
    if separate:
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        used: set[str] = set()
        for data, cells in items:
            doc = fitz.open()
            try:
                draw(doc, data, cells)
                path = folder / f'{safe_name(data, used)}.pdf'
                doc.save(str(path), garbage=3, deflate=True)
            finally:
                doc.close()
            written.append(str(path))
        return written
    doc = fitz.open()
    try:
        for data, cells in items:
            draw(doc, data, cells)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output), garbage=3, deflate=True)
    finally:
        doc.close()
    return [str(output)]
