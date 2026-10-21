"""Wersja przenośna (pendrive): dane obok programu, gdy leży tam PORTABLE.txt; ikona; test działania."""
import sys
from pathlib import Path

import pytest
from PIL import Image

import user_data

ROOT = Path(__file__).resolve().parents[1]


def test_appdata_when_not_portable(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'ImpoCraft.exe'))
    monkeypatch.setenv('APPDATA', str(tmp_path / 'roaming'))
    monkeypatch.setattr(user_data.os, 'name', 'nt')
    assert not user_data.is_portable()
    assert user_data.data_dir() == tmp_path / 'roaming' / 'ImpoCraft'


def test_portable_marker_moves_data_next_to_exe(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'ImpoCraft.exe'))
    (tmp_path / 'PORTABLE.txt').write_text('x', encoding='utf-8')
    assert user_data.is_portable()
    assert user_data.data_dir() == tmp_path / 'dane'
    import job_templates, duplex_calibration
    assert job_templates.template_path() == tmp_path / 'dane' / 'job_templates.json'
    assert duplex_calibration.profile_path() == tmp_path / 'dane' / 'duplex_profiles.json'


def test_source_checkout_is_not_portable():
    # znacznik leży w packaging/, nie obok app.py — uruchomienie z kodu zapisuje dane jak dotąd
    assert not (ROOT / 'PORTABLE.txt').exists() and (ROOT / 'packaging' / 'PORTABLE.txt').is_file()


def test_make_icon(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('make_icon', ROOT / 'scripts' / 'make_icon.py')
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    target = tmp_path / 'i.ico'
    assert tool.main([str(target)]) == 0
    with Image.open(target) as icon:
        assert (256, 256) in icon.info.get('sizes', set()) or icon.size == (256, 256)


def test_self_test_passes(tmp_path):
    import selftest
    report = tmp_path / 'raport.txt'
    assert selftest.run(str(report)) == 0
    assert report.read_text(encoding='utf-8').startswith('OK')


def test_data_from_old_program_name_is_copied_once(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'prog' / 'ImpoCraft.exe'))
    monkeypatch.setenv('APPDATA', str(tmp_path / 'roaming'))
    monkeypatch.setattr(user_data.os, 'name', 'nt')
    old = tmp_path / 'roaming' / 'Impozycjoner Studio'
    old.mkdir(parents=True)
    (old / 'job_templates.json').write_text('{"a": 1}', encoding='utf-8')
    new = user_data.data_dir()
    assert (new / 'job_templates.json').read_text(encoding='utf-8') == '{"a": 1}'
    assert (old / 'job_templates.json').is_file()                 # stary folder nietknięty
    (new / 'job_templates.json').write_text('{"b": 2}', encoding='utf-8')
    assert (user_data.data_dir() / 'job_templates.json').read_text(encoding='utf-8') == '{"b": 2}'  # bez ponownej kopii


def test_app_identity():
    import app_info
    assert app_info.APP_NAME == 'ImpoCraft' and app_info.AUTHOR == 'Dawid Gracz'
    assert len(app_info.version_tuple()) == 4 and app_info.VERSION in app_info.TITLE
