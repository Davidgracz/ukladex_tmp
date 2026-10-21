"""Ikona programu (.ico) rysowana kodem — bez plików graficznych w repozytorium.

Użycie: python scripts/make_icon.py build/impozycjoner.ico
Niebieski kwadrat z arkuszem i znacznikami cięcia (własny wzór, wspólny styl z ui_icons.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (47, 111, 194)
WHITE = (255, 255, 255)
SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw(size: int = 256) -> Image.Image:
    scale = 4
    n = size * scale
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 32
    d.rounded_rectangle((0, 0, n - 1, n - 1), radius=int(6 * u), fill=ACCENT)
    # arkusz z czterema użytkami
    d.rectangle((9 * u, 9 * u, 23 * u, 23 * u), fill=WHITE)
    for x0, y0 in ((10, 10), (16.5, 10), (10, 16.5), (16.5, 16.5)):
        d.rectangle((x0 * u, y0 * u, (x0 + 5.5) * u, (y0 + 5.5) * u), fill=(207, 224, 247))
    # znaczniki cięcia w narożnikach
    w = max(1, int(1.6 * u))
    for x in (9, 23):
        d.line([(x * u, 3 * u), (x * u, 7 * u)], fill=WHITE, width=w)
        d.line([(x * u, 25 * u), (x * u, 29 * u)], fill=WHITE, width=w)
    for y in (9, 23):
        d.line([(3 * u, y * u), (7 * u, y * u)], fill=WHITE, width=w)
        d.line([(25 * u, y * u), (29 * u, y * u)], fill=WHITE, width=w)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def main(argv: list[str]) -> int:
    target = Path(argv[0]) if argv else Path('build/impozycjoner.ico')
    target.parent.mkdir(parents=True, exist_ok=True)
    draw(256).save(target, format='ICO', sizes=[(s, s) for s in SIZES])
    print(f'Ikona: {target}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
