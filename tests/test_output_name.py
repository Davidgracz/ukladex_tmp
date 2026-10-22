"""Podpowiadana nazwa pliku po impozycji: <nazwa oryginału>_<netto>mm_impozycja.pdf (życzenie użytkownika).

Działa bez PyMuPDF i Tk.
"""
from naming import IMPOSITION_SUFFIX, PAGES_SUFFIX, default_output_name, output_name_problem


def test_name_from_source_and_net_size():
    assert default_output_name(r'C:\prace\wizytowki.pdf', 93, 53) == 'wizytowki_93x53mm_impozycja.pdf'
    assert default_output_name('/prace/Ulotka A6.PDF', 105, 148.5) == 'Ulotka A6_105x148,5mm_impozycja.pdf'
    assert default_output_name('karty.pdf', 85.6, 53.98, PAGES_SUFFIX) == 'karty_85,6x53,98mm_strony.pdf'
    assert IMPOSITION_SUFFIX == 'impozycja'


def test_name_is_always_valid_output_name():
    name = default_output_name(r'C:\x\zamówienie #12 {pilne}.pdf', 90, 50)
    assert name == 'zamówienie _12 _pilne__90x50mm_impozycja.pdf'
    assert output_name_problem(name, [r'C:\x\zamówienie #12 {pilne}.pdf']) is None
    assert default_output_name('', 90, 50) == 'montaz_90x50mm_impozycja.pdf'
    assert default_output_name('.pdf', 90, 50) == 'montaz_90x50mm_impozycja.pdf'
