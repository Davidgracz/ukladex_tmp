"""Zakładka „Książka ze składek”: wybór trybu, kartek w składce i kolejności trafia do ustawień (H-56)."""
import pytest
from conftest import create_tk

import book
from engine import BOOK

app = pytest.importorskip('app')


def test_book_tab_sets_settings(monkeypatch):
    window = create_tk(app.App)
    try:
        window.update()
        window.sheet_kind.set(BOOK)
        window._apply_sheet_kind()
        window.book_leaves_var.set('6')
        window.book_order_var.set(book.ORDER_STACK)
        s = window._read_fields()
        assert (s.mode, s.book_leaves, s.book_order) == (BOOK, 6, book.ORDER_STACK)
        assert window.sheet_kind.get() == BOOK
        assert window.book_pages_text.get() == '= do 24 stron'
        shown = []
        monkeypatch.setattr(app.messagebox, 'showinfo', lambda *a, **k: shown.append(a))
        window.edit_sheet()                                   # edycja użytków w książce — jawny komunikat
        assert shown and 'składki' in shown[0][1]
        window.book_leaves_var.set('x')
        with pytest.raises(ValueError, match='Kartek'):
            window._read_fields()
    finally:
        window.destroy()
