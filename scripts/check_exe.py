"""Sprawdza zbudowany EXE: uruchamia go z `--self-test` i czyta raport (bez klikania w okno).

Użycie: python scripts/check_exe.py dist/ImpoCraft/ImpoCraft.exe
Kod wyjścia 0 = program startuje, ładuje moduły, buduje okno i eksportuje próbny PDF.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def main(argv: list[str]) -> int:
    exe = Path(argv[0]).resolve()
    if not exe.is_file():
        print(f'Brak pliku: {exe}')
        return 1
    with tempfile.TemporaryDirectory() as folder:
        report = Path(folder) / 'raport.txt'
        try:
            code = subprocess.run([str(exe), '--self-test', str(report)], timeout=180).returncode
        except subprocess.TimeoutExpired:
            print('Program nie zakończył testu w 180 s.')
            return 1
        text = report.read_text(encoding='utf-8') if report.is_file() else '(brak raportu)'
    sys.stdout.reconfigure(encoding='utf-8')
    print(text)
    if code != 0 or not text.startswith('OK'):
        print(f'Test zbudowanego programu NIE przeszedł (kod {code}).')
        return 1
    print('Test zbudowanego programu: OK')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
