"""Odczyt tekstów okien Impozycjonera 4 z zasobów .NET (.resources) — tylko do analizy, bez uruchamiania programu.

Użycie (Windows):
    .venv\\Scripts\\python.exe -I scripts\\imp4_resources.py "G:\\ukladex\\Impozycjoner.exe" --out C:\\imp4_texty
    .venv\\Scripts\\python.exe -I scripts\\imp4_resources.py "G:\\ukladex\\Impozycjoner.exe" --out C:\\imp4_texty --grep "spad|wycink"

Wynik: jeden plik UTF-8 na okno (nazwa okna z zasobów, np. Znaczniki_Netto.txt) z parami „kontrolka<TAB>tekst”
oraz plik _wszystko.txt. **Folder wynikowy musi być poza repozytorium** — teksty oryginału nie mogą trafić na GitHub
(AGENTS/zasady projektu: czysta implementacja, opisujemy własnymi słowami). Skrypt czyta tylko łańcuchy znaków
z zasobów; nie dotyka kodu programu ani warstwy licencyjnej i nie obchodzi zaciemnienia.

Format .resources (publiczna specyfikacja .NET): nagłówek 0xBEEFCACE, wersja, typy, tabela nazw (UTF-16)
i sekcja danych; łańcuchy są zapisane jako długość 7-bitowa + UTF-8.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

MAGIC = b'\xce\xca\xef\xbe'
TEXT_KEYS = re.compile(r'\.(Text|OnText|OffText|Tooltip|ToolTip|TooltipText|TitleText|WatermarkText|HeaderText)$')


def _read7(b: bytes, p: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        c = b[p]
        p += 1
        value |= (c & 0x7F) << shift
        shift += 7
        if c < 0x80:
            return value, p


def _string(b: bytes, p: int) -> tuple[str, int]:
    n, p = _read7(b, p)
    return b[p:p + n].decode('utf-8', 'replace'), p + n


def parse_blob(b: bytes, base: int) -> list[tuple[str, str]]:
    """Wszystkie wpisy tekstowe jednego bloku .resources zaczynającego się w `base`."""
    p = base + 4
    _, skip = struct.unpack_from('<ii', b, p)
    p += 8 + skip
    version, count, ntypes = struct.unpack_from('<iii', b, p)
    p += 12
    types = []
    for _ in range(ntypes):
        name, p = _string(b, p)
        types.append(name)
    while (p - base) % 8:
        p += 1
    p += 4 * count
    positions = struct.unpack_from(f'<{count}i', b, p)
    p += 4 * count
    data_section, = struct.unpack_from('<i', b, p)
    names_start = p + 4
    entries = []
    for pos in positions:
        q = names_start + pos
        n, q = _read7(b, q)
        name = b[q:q + n].decode('utf-16-le', 'replace')
        offset, = struct.unpack_from('<i', b, q + n)
        d = base + data_section + offset
        code, d2 = _read7(b, d)
        is_string = code == 1 if version >= 2 else (code < len(types) and types[code].startswith('System.String'))
        if is_string:
            entries.append((name, _string(b, d2)[0]))
    return entries


def blobs(path: Path):
    data = path.read_bytes()
    start = 0
    while (i := data.find(MAGIC, start)) >= 0:
        start = i + 4
        try:
            entries = parse_blob(data, i)
        except (struct.error, IndexError, UnicodeDecodeError):
            continue
        if entries:
            yield entries


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('exe', type=Path, help='Impozycjoner.exe albo pl-PL\\Impozycjoner.resources.dll')
    ap.add_argument('--out', type=Path, required=True, help='folder wynikowy POZA repozytorium')
    ap.add_argument('--grep', help='wyrażenie regularne: wypisz tylko pasujące teksty (bez rozróżniania wielkości liter)')
    ap.add_argument('--all', action='store_true', help='wszystkie łańcuchy, nie tylko teksty kontrolek')
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    if out == repo or repo in out.parents:
        print('BŁĄD: folder wynikowy jest w repozytorium — wybierz folder poza nim.', file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(args.grep, re.IGNORECASE) if args.grep else None
    everything = []
    for number, entries in enumerate(blobs(args.exe), start=1):
        form = next((v for k, v in entries if k == '>>$this.Name'), None) or f'zasob_{number:03d}'
        rows = [(k, v) for k, v in sorted(entries)
                if v.strip() and (args.all or TEXT_KEYS.search(k) or not k.startswith(('>>', '$')) and '.' not in k)]
        lines = [f'{k}\t{v}'.replace('\r', '\\r').replace('\n', '\\n') for k, v in rows]
        (out / f'{form}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        everything += [f'{form}\t{line}' for line in lines]
    (out / '_wszystko.txt').write_text('\n'.join(everything) + '\n', encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    if pattern:
        for line in everything:
            if pattern.search(line):
                print(line[:400])
    print(f'Zapisano {len(everything)} tekstów do {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
