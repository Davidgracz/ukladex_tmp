"""Wspólne pomoce testów okien Tk.

Podczas budowania (BUILD_*.bat) start Tk potrafi jednorazowo nie odczytać swojego pliku .tcl („Can't find a usable
tk.tcl … couldn't read file”), choć plik istnieje — najpewniej chwilowa blokada pliku przez skaner antywirusowy przy
dużej liczbie zapisów na dysk. Nie dotyczy to programu (okno tworzy się raz), tylko testów, które tworzą wiele okien.
Dlatego okna w testach tworzymy z ponowieniem przy tym jednym rodzaju błędu.
"""
import time
import tkinter as tk

import pytest


def create_tk(factory=tk.Tk, attempts=3):
    """Tworzy okno Tk; przy chwilowym błędzie odczytu plików Tcl/Tk ponawia (maks. `attempts` razy)."""
    for attempt in range(attempts):
        try:
            return factory()
        except tk.TclError as exc:
            transient = 'usable' in str(exc) or "couldn't read file" in str(exc)   # np. auto.tcl, tk.tcl
            if not transient or attempt == attempts - 1:
                raise
            time.sleep(0.5)


@pytest.fixture
def tk_root():
    root = create_tk()
    yield root
    root.destroy()
