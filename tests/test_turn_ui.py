"""Wstęga „Rodzaj arkuszy”: przycisk „Przez markę” z menu pełny/niepełny MB/MC (H-55)."""
import pytest
from conftest import create_tk

from engine import FLIP_MB, FLIP_MC, TURN_MB, TURN_MC

app = pytest.importorskip('app')


def test_turn_kinds_set_mode_and_flip():
    window = create_tk(app.App)
    try:
        window.update()
        expected = {f'Dwustronnie|{FLIP_MB}': ('Dwustronnie', FLIP_MB), f'Dwustronnie|{FLIP_MC}': ('Dwustronnie', FLIP_MC),
                    TURN_MB: (TURN_MB, None), TURN_MC: (TURN_MC, None)}
        for value, _, text in app.TURN_KINDS:
            window.sheet_kind.set(value)
            window._apply_sheet_kind()
            window.update()
            s = window._read_fields()
            mode, flip = expected[value]
            assert s.mode == mode and (flip is None or s.flip == flip)
            assert window.sheet_kind.get() == value                 # synchronizacja nie nadpisuje wyboru
            assert text in str(window.turn_button.cget('text'))
            assert str(window.turn_button.cget('style')) == 'KindOn.TMenubutton'
        window.sheet_kind.set('Jednostronnie')
        window._apply_sheet_kind()
        assert window._read_fields().mode == 'Jednostronnie'
        assert str(window.turn_button.cget('style')) == 'Kind.TMenubutton'
    finally:
        window.destroy()
