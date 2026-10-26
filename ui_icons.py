"""Small vector-style toolbar icons drawn with Pillow (no image files to ship)."""
from PIL import Image, ImageDraw

from preview_labels import _font

INK = (47, 111, 194)
DARK = (55, 65, 81)
PAPER = (255, 255, 255)
BACK = (200, 210, 224)
SCALE = 4  # draw large and downsample for smooth edges


def _canvas(size):
    big = size * SCALE
    return Image.new('RGBA', (big, big), (0, 0, 0, 0)), big


def _page(d, box, fill=PAPER, fold=True):
    x0, y0, x1, y1 = box
    f = (x1 - x0) * .3 if fold else 0
    d.polygon([(x0, y0), (x1 - f, y0), (x1, y0 + f), (x1, y1), (x0, y1)], fill=fill, outline=DARK, width=SCALE*2)
    if fold:
        d.line([(x1 - f, y0), (x1 - f, y0 + f), (x1, y0 + f)], fill=DARK, width=SCALE*2)


def _arrow(d, a, b, width):
    (x0, y0), (x1, y1) = a, b
    d.line([a, b], fill=INK, width=width)
    head = width * 2.2
    if y0 == y1:
        for x, s in ((x0, 1), (x1, -1)):
            d.polygon([(x, y0), (x + s*head, y0 - head*.8), (x + s*head, y0 + head*.8)], fill=INK)
    else:
        for y, s in ((y0, 1), (y1, -1)):
            d.polygon([(x0, y), (x0 - head*.8, y + s*head), (x0 + head*.8, y + s*head)], fill=INK)


def draw(name, size=30):
    img, n = _canvas(size)
    d = ImageDraw.Draw(img)
    u = n / 30
    if name == 'single':
        _page(d, (8*u, 3*u, 22*u, 27*u))
    elif name in ('duplex_long', 'duplex_short'):
        _page(d, (9*u, 2*u, 21*u, 17*u), fill=BACK)
        _page(d, (4*u, 7*u, 16*u, 22*u))
        if name == 'duplex_long':
            _arrow(d, (8*u, 26.5*u), (28*u, 26.5*u), int(2*u))
        else:
            _arrow(d, (25.5*u, 6*u), (25.5*u, 28*u), int(2*u))
    elif name in ('flip_mb', 'flip_mc'):    # pełny przez markę: tył na osobnej płycie
        _page(d, (9*u, 2*u, 21*u, 17*u), fill=BACK)
        _page(d, (4*u, 7*u, 16*u, 22*u))
        if name == 'flip_mb':
            _arrow(d, (4*u, 26.5*u), (26*u, 26.5*u), int(2*u))
        else:
            _arrow(d, (25.5*u, 4*u), (25.5*u, 26*u), int(2*u))
    elif name in ('turn_mb', 'turn_mc'):    # niepełny: przód i tył na jednej płycie
        if name == 'turn_mb':
            _page(d, (3*u, 4*u, 27*u, 22*u))
            d.rectangle((15*u, 4*u, 27*u, 22*u), fill=BACK, outline=DARK, width=SCALE*2)
            _arrow(d, (5*u, 26.5*u), (25*u, 26.5*u), int(2*u))
        else:
            _page(d, (3*u, 3*u, 21*u, 27*u))
            d.rectangle((3*u, 15*u, 21*u, 27*u), fill=BACK, outline=DARK, width=SCALE*2)
            _arrow(d, (25.5*u, 5*u), (25.5*u, 25*u), int(2*u))
    elif name == 'economic':
        colors = [(242, 201, 76), (201, 168, 130), (143, 193, 227), (155, 194, 91), (242, 201, 76), (143, 193, 227)]
        for i, c in enumerate(colors):
            x, y = 3*u + (i % 3)*8.3*u, 6*u + (i // 3)*10*u
            d.rectangle((x, y, x + 7*u, y + 8.5*u), fill=c, outline=DARK, width=SCALE)
    elif name == 'booklet':
        d.polygon([(15*u, 8*u), (3*u, 5*u), (3*u, 24*u), (15*u, 27*u)], fill=PAPER, outline=DARK, width=SCALE*2)
        d.polygon([(15*u, 8*u), (27*u, 5*u), (27*u, 24*u), (15*u, 27*u)], fill=BACK, outline=DARK, width=SCALE*2)
        for k in (12, 16, 20):
            d.line([(6*u, k*u), (12*u, (k+1.5)*u)], fill=INK, width=SCALE*2)
    elif name == 'symbols':
        for i, c in enumerate([(242, 201, 76), (143, 193, 227), (155, 194, 91), (79, 111, 216)]):
            x, y = 3*u + (i % 2)*12.5*u, 3*u + (i // 2)*12.5*u
            d.rectangle((x, y, x + 11*u, y + 11*u), fill=c, outline=PAPER, width=SCALE)
    elif name == 'edit':
        d.rectangle((3*u, 6*u, 21*u, 27*u), fill=PAPER, outline=DARK, width=SCALE*2)
        d.polygon([(25*u, 3*u), (28*u, 6*u), (14*u, 20*u), (10*u, 21*u), (11*u, 17*u)], fill=INK)
    elif name == 'frame':  # cztery użytki, każdy w cienkiej czarnej ramce
        for x0, y0 in ((3, 5), (16, 5), (3, 17), (16, 17)):
            d.rectangle((x0*u, y0*u, (x0 + 11)*u, (y0 + 9)*u), fill=BACK, outline=INK, width=SCALE)
    elif name == 'register':
        d.ellipse((3*u, 5*u, 20*u, 22*u), outline=DARK, width=SCALE*2)
        d.ellipse((10*u, 8*u, 27*u, 25*u), outline=INK, width=SCALE*2)
        d.line([(15*u, 2*u), (15*u, 28*u)], fill=DARK, width=SCALE)
        d.line([(2*u, 15*u), (28*u, 15*u)], fill=DARK, width=SCALE)
    elif name == 'reg2':  # użytek ze spadem i krzyże pasowania przy narożnikach
        d.rectangle((9*u, 9*u, 21*u, 21*u), fill=BACK, outline=DARK, width=SCALE)
        for x, y, dx, dy in ((9, 9, -1, -1), (21, 9, 1, -1), (9, 21, -1, 1), (21, 21, 1, 1)):
            d.line([(x*u, y*u), ((x + 7*dx)*u, y*u)], fill=INK, width=SCALE*2)
            d.line([((x + 4*dx)*u, (y + 5*dy)*u), ((x + 4*dx)*u, (y - 4*dy)*u)], fill=INK, width=SCALE*2)
    elif name == 'refresh':
        d.arc((5*u, 5*u, 25*u, 25*u), 40, 330, fill=INK, width=int(3*u))
        d.polygon([(25*u, 3*u), (26*u, 13*u), (17*u, 10*u)], fill=INK)
    elif name == 'preflight':
        _page(d, (5*u, 3*u, 22*u, 27*u))
        d.line([(10*u, 17*u), (15*u, 23*u), (28*u, 8*u)], fill=(46, 160, 67), width=int(3.4*u))
    elif name == 'marks':
        d.rectangle((9*u, 9*u, 21*u, 21*u), outline=BACK, width=SCALE*2)
        for x in (9, 21):
            d.line([(x*u, 1*u), (x*u, 6*u)], fill=DARK, width=SCALE*2)
            d.line([(x*u, 24*u), (x*u, 29*u)], fill=DARK, width=SCALE*2)
        for y in (9, 21):
            d.line([(1*u, y*u), (6*u, y*u)], fill=DARK, width=SCALE*2)
            d.line([(24*u, y*u), (29*u, y*u)], fill=DARK, width=SCALE*2)
    elif name == 'numbers':
        _page(d, (6*u, 3*u, 24*u, 27*u))
        d.text((14*u, 17*u), '12', fill=INK, anchor='mm', font=_font(int(10*u)))
    elif name == 'gutter':  # dwie pary użytków rozdzielone szerszym odstępem z linią w osi
        for x0 in (2, 8, 18, 24):
            d.rectangle((x0*u, 6*u, (x0+4.5)*u, 24*u), fill=BACK, outline=DARK, width=SCALE)
        d.line([(15*u, 1*u), (15*u, 7*u)], fill=INK, width=SCALE*2)
        d.line([(15*u, 23*u), (15*u, 29*u)], fill=INK, width=SCALE*2)
    elif name == 'gross':  # użytek ze spadem i kreski na przedłużeniu krawędzi brutto
        d.rectangle((8*u, 8*u, 22*u, 22*u), fill=BACK, outline=DARK, width=SCALE)
        for x, y, dx, dy in ((8, 8, -1, -1), (22, 8, 1, -1), (8, 22, -1, 1), (22, 22, 1, 1)):
            d.line([(x*u, y*u), ((x + 6*dx)*u, y*u)], fill=INK, width=SCALE*2)
            d.line([(x*u, y*u), (x*u, (y + 6*dy)*u)], fill=INK, width=SCALE*2)
    elif name == 'slug':  # linia tekstu nad arkuszem
        _page(d, (4*u, 11*u, 26*u, 28*u), fold=False)
        for x0, x1 in ((4, 12), (14, 20), (22, 26)):
            d.rectangle((x0*u, 4*u, x1*u, 7*u), fill=INK)
    elif name == 'strip':  # rząd kolorowych kostek nad arkuszem
        for i, c in enumerate([(0, 174, 239), (236, 0, 140), (255, 242, 0), (35, 31, 32)]):
            d.rectangle(((2 + i*6.5)*u, 4*u, (7.8 + i*6.5)*u, 10*u), fill=c)
        _page(d, (4*u, 13*u, 26*u, 28*u), fold=False)
    elif name == 'own':  # arkusz z dwoma znacznikami z plików w dolnych narożnikach
        _page(d, (3*u, 3*u, 27*u, 27*u), fold=False)
        for x0 in (5, 19):
            d.rectangle((x0*u, 19*u, (x0 + 6)*u, 25*u), fill=INK)
            d.rectangle(((x0 + 2)*u, 21*u, (x0 + 4)*u, 23*u), fill=PAPER)
    elif name == 'trimcrop':  # rozkładówka z włosowym przycięciem przy grzbiecie
        _page(d, (3*u, 5*u, 14.5*u, 25*u), fold=False)
        _page(d, (15.5*u, 5*u, 27*u, 25*u), fold=False)
        d.rectangle((13*u, 5*u, 17*u, 25*u), fill=(214, 69, 65))
    else:
        raise ValueError(f'Nieznana ikona: {name}')
    return img.resize((size, size), Image.Resampling.LANCZOS)


RED = (214, 69, 65)
GREEN = (46, 160, 67)


def draw_tool(name, size=32):
    """Ikony programów dodatkowych (kafelki menu w zakładce „Programy dodatkowe”)."""
    img, n = _canvas(size)
    d = ImageDraw.Draw(img)
    u = n / 30
    w = SCALE * 2
    if name == 'split':        # jedna strona → kilka plików
        _page(d, (2*u, 6*u, 12*u, 20*u))
        _arrow(d, (13*u, 13*u), (18*u, 13*u), int(1.6*u))
        for k in range(3):
            _page(d, ((19 + k*3)*u, (4 + k*5)*u, (27 + k)*u, (11 + k*5)*u), fold=False)
    elif name == 'merge':      # kilka stron → jeden plik
        for k in range(3):
            _page(d, ((2 + k)*u, (4 + k*7)*u, (10 + k)*u, (10 + k*7)*u), fold=False)
        _arrow(d, (13*u, 15*u), (18*u, 15*u), int(1.6*u))
        _page(d, (19*u, 5*u, 28*u, 25*u))
    elif name == 'extract':    # zaznaczone strony z pliku
        _page(d, (3*u, 3*u, 19*u, 27*u))
        for y in (8, 14, 20):
            d.rectangle((6*u, y*u, 16*u, (y + 3)*u), fill=INK if y == 14 else BACK)
        _arrow(d, (19*u, 15.5*u), (27*u, 15.5*u), int(1.6*u))
    elif name == 'evenodd':
        for k, c in enumerate((INK, BACK, INK, BACK)):
            _page(d, ((2 + k*6.5)*u, 8*u, (8 + k*6.5)*u, 22*u), fill=c, fold=False)
    elif name == 'cover':      # okładka + wkład
        _page(d, (2*u, 5*u, 14*u, 25*u), fill=INK, fold=False)
        _page(d, (16*u, 5*u, 28*u, 25*u))
    elif name == 'chunks':     # po N stron
        for x in (2, 11, 20):
            for k in range(2):
                _page(d, ((x + k*2)*u, (8 + k*3)*u, (x + 6 + k*2)*u, (18 + k*3)*u), fold=False)
    elif name == 'delete':     # strona przekreślona
        _page(d, (5*u, 3*u, 22*u, 27*u))
        d.line([(9*u, 9*u), (25*u, 25*u)], fill=RED, width=int(3*u))
        d.line([(25*u, 9*u), (9*u, 25*u)], fill=RED, width=int(3*u))
    elif name == 'rotate':
        _page(d, (8*u, 8*u, 22*u, 26*u))
        d.arc((3*u, 2*u, 27*u, 26*u), 200, 330, fill=INK, width=int(2.4*u))
        d.polygon([(25*u, 6*u), (28*u, 12*u), (21*u, 11*u)], fill=INK)
    elif name == 'duplicate':
        for k in range(3):
            _page(d, ((3 + k*5)*u, (3 + k*5)*u, (17 + k*5)*u, (17 + k*5)*u), fold=False)
    elif name == 'shuffle':
        _page(d, (3*u, 6*u, 13*u, 24*u), fold=False)
        _page(d, (17*u, 6*u, 27*u, 24*u), fill=BACK, fold=False)
        _arrow(d, (8*u, 3*u), (22*u, 3*u), int(1.4*u))
        _arrow(d, (8*u, 27.5*u), (22*u, 27.5*u), int(1.4*u))
    elif name == 'bleed':      # strona z dodanym pasem spadu
        d.rectangle((3*u, 3*u, 27*u, 27*u), fill=(214, 228, 245), outline=INK, width=w)
        _page(d, (7*u, 7*u, 23*u, 23*u), fold=False)
    elif name == 'scale':
        _page(d, (2*u, 14*u, 12*u, 27*u), fold=False)
        d.rectangle((2*u, 3*u, 27*u, 27*u), outline=INK, width=w)
        _arrow(d, (13*u, 13*u), (24*u, 13*u), int(1.4*u))
    elif name == 'grid':       # plakat na kafle
        for c in range(2):
            for r in range(2):
                d.rectangle(((3 + c*12.5)*u, (4 + r*11.5)*u, (14 + c*12.5)*u, (14 + r*11.5)*u),
                            fill=PAPER, outline=DARK, width=w)
        d.rectangle((14*u, 4*u, 15.5*u, 26*u), fill=(214, 228, 245))
    elif name == 'spreads':    # rozkładówka cięta na dwie strony
        _page(d, (2*u, 7*u, 14*u, 23*u), fold=False)
        _page(d, (16*u, 7*u, 28*u, 23*u), fold=False)
        d.line([(15*u, 3*u), (15*u, 27*u)], fill=RED, width=w)
    elif name in ('qr', 'datamatrix'):
        if name == 'qr':     # trzy znaczniki pozycji i kilka modułów
            for x0, y0 in ((3, 3), (19, 3), (3, 19)):
                d.rectangle((x0*u, y0*u, (x0 + 8)*u, (y0 + 8)*u), outline=DARK, width=int(1.6*u))
                d.rectangle(((x0 + 2.6)*u, (y0 + 2.6)*u, (x0 + 5.4)*u, (y0 + 5.4)*u), fill=DARK)
            for x, y in ((14, 4), (14, 9), (19, 14), (24, 19), (14, 19), (19, 24), (24, 24), (9, 14), (4, 14)):
                d.rectangle((x*u, y*u, (x + 3)*u, (y + 3)*u), fill=INK)
        else:                # obramowanie L i wzór zegarowy Data Matrix
            d.rectangle((3*u, 3*u, 5*u, 27*u), fill=DARK)
            d.rectangle((3*u, 25*u, 27*u, 27*u), fill=DARK)
            for k in range(6):
                d.rectangle(((5 + k*4)*u, 3*u, (7 + k*4)*u, 5*u), fill=DARK)
                d.rectangle((25*u, (5 + k*4)*u, 27*u, (7 + k*4)*u), fill=DARK)
            for x, y in ((8, 8), (14, 8), (11, 12), (17, 14), (8, 17), (14, 19), (20, 20), (20, 9)):
                d.rectangle((x*u, y*u, (x + 3)*u, (y + 3)*u), fill=INK)
    elif name == 'barcode':
        x = 4.0
        for k, bar in enumerate((2, 1, 1, 3, 1, 2, 1, 1, 2, 1, 3, 1)):
            if k % 2 == 0:
                d.rectangle((x*u, 5*u, (x + bar)*u, 22*u), fill=DARK)
            x += bar
        d.rectangle((4*u, 24*u, 26*u, 26*u), fill=INK)
    else:
        raise ValueError(f'Nieznana ikona narzędzia: {name}')
    return img.resize((size, size), Image.Resampling.LANCZOS)
