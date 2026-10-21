"""Instalator ImpoCraft: dane wersji EXE, definicje dla Inno Setup, polecenie podpisu (bez uruchamiania signtool)."""
import importlib.util
from pathlib import Path

import pytest

import app_info

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_files(tmp_path):
    tool = load('make_version_info')
    assert tool.main([str(tmp_path / 'version_info.txt')]) == 0
    text = (tmp_path / 'version_info.txt').read_text(encoding='utf-8')
    assert "StringStruct('CompanyName', 'Dawid Gracz')" in text
    assert "StringStruct('ProductName', 'ImpoCraft')" in text
    assert str(app_info.version_tuple()) in text
    compile(text.split('\n', 1)[1], 'version_info', 'eval')         # składnia czytana przez PyInstallera
    iss = (tmp_path / 'app_info.iss').read_bytes()
    assert iss.startswith(b'\xef\xbb\xbf')                          # BOM: Inno Setup czyta UTF-8
    iss_text = iss.decode('utf-8-sig')
    assert f'#define AppVersion "{app_info.VERSION}"' in iss_text
    assert '#define AppPublisher "Dawid Gracz"' in iss_text
    assert f'#define AppId "{app_info.INSTALLER_APP_ID}"' in iss_text


def test_installer_script_uses_generated_identity():
    script = (ROOT / 'packaging' / 'ImpoCraft.iss').read_bytes()
    assert script.startswith(b'\xef\xbb\xbf')
    text = script.decode('utf-8-sig')
    assert '#include "..\\build\\app_info.iss"' in text
    assert 'AppPublisher={#AppPublisher}' in text and 'AppId={{#AppId}' in text
    assert 'Excludes: "PORTABLE.txt,\\dane\\*"' in text            # instalacja zapisuje dane w %APPDATA%
    assert 'Dawid Gracz' not in text and '0.5.0' not in text         # nic przepisanego ręcznie


def test_sign_command_thumbprint_and_pfx():
    tool = load('sign_files')
    assert not tool.signing_requested({})
    cmd = tool.sign_command('signtool', ['a.exe'], {'IMPOCRAFT_SIGN_THUMBPRINT': 'ab cd'})
    assert cmd[:2] == ['signtool', 'sign'] and ['/sha1', 'abcd'] == cmd[cmd.index('/sha1'):cmd.index('/sha1') + 2]
    assert '/tr' in cmd and cmd[-1] == 'a.exe'
    cmd = tool.sign_command('signtool', ['a.exe'], {'IMPOCRAFT_SIGN_PFX': 'c.pfx', 'IMPOCRAFT_SIGN_PASSWORD': 'tajne'})
    assert 'tajne' in cmd and 'tajne' not in tool.printable(cmd)
    with pytest.raises(ValueError):
        tool.sign_command('signtool', ['a.exe'], {})


def test_sign_without_certificate_is_a_noop(monkeypatch):
    tool = load('sign_files')
    for key in ('IMPOCRAFT_SIGN_THUMBPRINT', 'IMPOCRAFT_SIGN_PFX'):
        monkeypatch.delenv(key, raising=False)
    assert tool.main(['nie-istnieje.exe']) == 0


def test_batch_files_have_crlf():
    for name in ('BUILD_INSTALLER_WINDOWS.bat', 'BUILD_EXE_WINDOWS.bat'):
        data = (ROOT / name).read_bytes()
        assert data.count(b'\n') == data.count(b'\r\n')
