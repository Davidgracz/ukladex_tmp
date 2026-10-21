"""Gdzie program trzyma dane użytkownika (szablony prac, profile maszyn).

Zwykle: %APPDATA%\\ImpoCraft (Windows) albo ~/.config/ImpoCraft. Dane ze starego folderu „Impozycjoner Studio”
(sprzed zmiany nazwy) są przy pierwszym użyciu kopiowane do nowego — stary folder zostaje nietknięty.
Tryb przenośny (pendrive): gdy obok programu leży plik `PORTABLE.txt`, dane są zapisywane w folderze `dane`
obok programu — szablony i profile jeżdżą razem z pendrive'em, a na komputerze nic nie zostaje.
Obok programu = folder z plikiem EXE (wersja zbudowana PyInstallerem) albo folder z app.py (uruchomienie z kodu).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_FOLDER = 'ImpoCraft'
LEGACY_FOLDER = 'Impozycjoner Studio'
PORTABLE_MARKER = 'PORTABLE.txt'
PORTABLE_DATA = 'dane'


def program_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_portable() -> bool:
    return (program_dir() / PORTABLE_MARKER).is_file()


def data_dir() -> Path:
    if is_portable():
        return program_dir() / PORTABLE_DATA
    if os.name == 'nt' and os.environ.get('APPDATA'):
        base = Path(os.environ['APPDATA'])
    else:
        base = Path.home() / '.config'
    target = base / APP_FOLDER
    _copy_legacy(base / LEGACY_FOLDER, target)
    return target


def _copy_legacy(legacy: Path, target: Path) -> None:
    """Jednorazowo kopiuje dane spod starej nazwy programu, gdy nowego folderu jeszcze nie ma."""
    if target.exists() or not legacy.is_dir():
        return
    try:
        shutil.copytree(legacy, target)
    except OSError:
        pass  # brak kopii nie blokuje programu — zacznie z pustym folderem
