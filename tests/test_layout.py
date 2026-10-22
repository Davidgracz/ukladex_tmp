"""Układ okna: dolny pasek (wersja, „Sprawdź aktualizacje”, stan) nie może zniknąć na mniejszym ekranie.

Błąd z 0.5.4: pasek znaczników urósł (11 przycisków w kolumnie), okno wymagało ~1150 px wysokości i dolny pasek był
ściskany do 1 px — przycisk aktualizacji znikał. Pasek dolny jest teraz pakowany przed środkiem okna.
"""
import tkinter as tk

import pytest

app = pytest.importorskip('app')


def _find(widget, text):
    for child in widget.winfo_children():
        try:
            if str(child.cget('text')) == text:
                return child
        except tk.TclError:
            pass
        found = _find(child, text)
        if found is not None:
            return found
    return None


@pytest.mark.parametrize('size', ['1366x768', '1280x720'])
def test_update_button_visible_on_small_screen(size):
    window = app.App()
    try:
        window.geometry(size + '+0+0')
        window.update()
        button = _find(window, 'Sprawdź aktualizacje')
        assert button is not None
        bar = button.master
        assert bar.winfo_height() > 10
        assert bar.winfo_y() + bar.winfo_height() <= window.imposition_tab.winfo_height()
        assert button.winfo_ismapped()
    finally:
        window.destroy()


def test_window_fits_full_hd_height():
    window = app.App()
    try:
        window.update()
        assert window.winfo_reqheight() <= 1000          # Full HD z paskiem zadań Windows
    finally:
        window.destroy()
