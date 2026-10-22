"""Tożsamość programu w jednym miejscu: nazwa, wersja, autor.

Z tych wartości korzystają okno programu, metadane eksportowanych PDF, informacje o wersji pliku EXE
(scripts/make_version_info.py) i instalator (packaging/ImpoCraft.iss przez BUILD_INSTALLER_WINDOWS.bat).
"""
from __future__ import annotations

APP_NAME = 'ImpoCraft'
VERSION = '0.5.4'
AUTHOR = 'Dawid Gracz'
COPYRIGHT_YEAR = '2026'
DESCRIPTION = 'Impozycja (montaż) PDF do druku'
EXE_NAME = 'ImpoCraft'
# Stały identyfikator instalatora: po nim Windows rozpoznaje aktualizację tej samej aplikacji. Nie zmieniać.
INSTALLER_APP_ID = '{6F0E2B1C-5A7D-4C39-9E21-0B8D4F7A3C55}'
# Repozytorium, którego wydania (Releases) program sprawdza w poszukiwaniu aktualizacji (updater.py).
UPDATE_REPO = 'Davidgracz/ukladex_tmp'

TITLE = f'{APP_NAME} {VERSION}'
COPYRIGHT = f'© {COPYRIGHT_YEAR} {AUTHOR}'


def version_tuple() -> tuple[int, int, int, int]:
    parts = [int(p) for p in VERSION.split('.')]
    return tuple((parts + [0, 0, 0, 0])[:4])  # type: ignore[return-value]
