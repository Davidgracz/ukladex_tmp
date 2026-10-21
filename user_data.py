"""Gdzie program trzyma dane użytkownika (szablony prac, profile maszyn).

Zwykle: %APPDATA%\\Impozycjoner Studio (Windows) albo ~/.config/Impozycjoner Studio.
Tryb przenośny (pendrive): gdy obok programu leży plik `PORTABLE.txt`, dane są zapisywane w folderze `dane`
obok programu — szablony i profile jeżdżą razem z pendrive'em, a na komputerze nic nie zostaje.
Obok programu = folder z plikiem EXE (wersja zbudowana PyInstallerem) albo folder z app.py (uruchomienie z kodu).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_FOLDER = 'Impozycjoner Studio'
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
        return Path(os.environ['APPDATA']) / APP_FOLDER
    return Path.home() / '.config' / APP_FOLDER
