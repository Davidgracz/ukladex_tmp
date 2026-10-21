"""Aktualizacje z GitHub Releases: wersje, odczyt wydania, zaufane adresy, suma SHA-256, stan, argumenty instalatora."""
import hashlib
import importlib.util
import io
import sys
from pathlib import Path

import pytest

import app_info
import updater

ROOT = Path(__file__).resolve().parents[1]
BASE = updater.DOWNLOAD_PREFIX


def release(version='9.0.0', **extra):
    name = updater.installer_name(version)
    data = {'tag_name': f'v{version}', 'body': 'Zmiany', 'html_url': 'https://github.com/x/releases/tag/v9',
            'draft': False, 'prerelease': False,
            'assets': [{'name': name, 'browser_download_url': f'{BASE}v{version}/{name}'},
                       {'name': name + '.sha256', 'browser_download_url': f'{BASE}v{version}/{name}.sha256'}]}
    data.update(extra)
    return data


def test_versions():
    assert updater.parse_version('v0.5.1') == (0, 5, 1)
    assert updater.is_newer('0.5.10', '0.5.9') and updater.is_newer('1.0', '0.9.9.9')
    assert not updater.is_newer('0.5.1', '0.5.1') and not updater.is_newer('v0.5', '0.5.0')
    for bad in ('', 'latest', '1.x', '1.2.3.4.5'):
        with pytest.raises(ValueError):
            updater.parse_version(bad)


def test_release_info_and_check():
    info = updater.release_info(release())
    assert info.version == '9.0.0' and info.installer_name == 'ImpoCraft-9.0.0-instalator.exe' and info.notes == 'Zmiany'
    assert updater.check(fetch=lambda url: release()) == info
    assert updater.check(fetch=lambda url: release(app_info.VERSION)) is None        # ta sama wersja
    assert updater.check(fetch=lambda url: release('0.0.1')) is None                  # starsza


def test_release_rejected_when_untrusted_or_incomplete():
    assert updater.release_info(release(draft=True)) is None
    assert updater.release_info(release(prerelease=True)) is None
    assert updater.release_info(release(tag_name='nocny')) is None
    evil = release()
    evil['assets'][0]['browser_download_url'] = 'https://example.com/ImpoCraft-9.0.0-instalator.exe'
    assert updater.release_info(evil) is None
    missing = release()
    missing['assets'] = missing['assets'][:1]                                          # brak pliku z sumą
    assert updater.release_info(missing) is None
    assert updater.release_info([]) is None


def test_parse_sha256():
    digest = 'a' * 64
    assert updater.parse_sha256(f'{digest}  ImpoCraft-9-instalator.exe\n', 'ImpoCraft-9-instalator.exe') == digest
    assert updater.parse_sha256(digest.upper(), 'x.exe') == digest
    with pytest.raises(ValueError):
        updater.parse_sha256(f'{digest}  inny.exe', 'x.exe')


class FakeResponse(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data))}


def test_download_verifies_checksum(tmp_path):
    payload = b'MZ' + b'x' * 300000
    info = updater.release_info(release())
    good = hashlib.sha256(payload).hexdigest()
    seen = []
    path = updater.download(info, tmp_path, opener=lambda req, timeout: FakeResponse(payload),
                            text_fetch=lambda url: f'{good}  {info.installer_name}',
                            progress=lambda done, total: seen.append((done, total)))
    assert path.read_bytes() == payload and seen[-1] == (len(payload), len(payload))
    with pytest.raises(ValueError):
        updater.download(info, tmp_path / 'zly', opener=lambda req, timeout: FakeResponse(payload + b'!'),
                         text_fetch=lambda url: f'{good}  {info.installer_name}')
    assert not (tmp_path / 'zly' / info.installer_name).exists()                        # uszkodzony plik usunięty


def test_download_refuses_foreign_url(tmp_path):
    info = updater.release_info(release())
    forged = updater.UpdateInfo(**{**info.__dict__, 'installer_url': 'https://example.com/a.exe'})
    with pytest.raises(ValueError):
        updater.download(forged, tmp_path, opener=None, text_fetch=lambda url: '')


def test_state_roundtrip_and_rules(tmp_path):
    path = tmp_path / 'update_state.json'
    assert updater.load_state(path) == {'auto_check': True, 'skipped': '', 'last_check': 0.0}
    path.write_text('nie json', encoding='utf-8')
    assert updater.load_state(path)['auto_check'] is True
    updater.save_state({'auto_check': False, 'skipped': '9.0.0', 'last_check': 100.0}, path)
    state = updater.load_state(path)
    assert state == {'auto_check': False, 'skipped': '9.0.0', 'last_check': 100.0}
    assert not updater.should_auto_check(state, now=10 ** 9)
    assert updater.should_auto_check({'auto_check': True, 'last_check': 0}, now=10 ** 9)
    assert not updater.should_auto_check({'auto_check': True, 'last_check': 1000}, now=1000 + 60)
    info = updater.release_info(release())
    assert not updater.worth_showing(info, state, manual=False) and updater.worth_showing(info, state, manual=True)
    assert not updater.worth_showing(None, state, manual=True)


def test_installer_args_per_user_and_machine():
    local = r'C:\Users\a\AppData\Local'
    per_user = updater.installer_args(Path(local) / 'Programs' / 'ImpoCraft', local)
    assert '/CURRENTUSER' in per_user and '/RELAUNCH' in per_user and '/SILENT' in per_user
    assert '/ALLUSERS' in updater.installer_args(Path(r'C:\Program Files\ImpoCraft'), local)


def test_install_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'ImpoCraft.exe'))
    assert updater.install_mode() == updater.MODE_SOURCE
    (tmp_path / 'unins000.exe').write_bytes(b'')
    assert updater.install_mode() == updater.MODE_INSTALLED
    (tmp_path / 'PORTABLE.txt').write_text('x', encoding='utf-8')
    assert updater.install_mode() == updater.MODE_PORTABLE


def load_publish():
    spec = importlib.util.spec_from_file_location('publish_release', ROOT / 'scripts' / 'publish_release.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publish_release_files_and_notes(tmp_path):
    tool = load_publish()
    with pytest.raises(FileNotFoundError):
        tool.release_files('9.0.0', tmp_path)
    installer = tmp_path / updater.installer_name('9.0.0')
    installer.write_bytes(b'setup')
    (tmp_path / 'ImpoCraft-przenosny.zip').write_bytes(b'zip')
    files = tool.release_files('9.0.0', tmp_path)
    assert [f.name for f in files] == [installer.name, installer.name + '.sha256', 'ImpoCraft-9.0.0-przenosny.zip']
    line = files[1].read_text(encoding='utf-8')
    assert updater.parse_sha256(line, installer.name) == hashlib.sha256(b'setup').hexdigest()
    log = '# Changelog\n\n## Unreleased\n\n- Nowe\n\n## 9.0.0\n\n- Dziewiąta\n\n## 8.0\n- Stare\n'
    assert tool.changelog_notes(log, '9.0.0') == '- Dziewiąta'
    assert tool.changelog_notes(log, '10.0') == '- Nowe'


def test_installer_relaunches_after_silent_update():
    text = (ROOT / 'packaging' / 'ImpoCraft.iss').read_bytes().decode('utf-8-sig')
    assert 'Check: RelaunchRequested' in text and "Pos('/RELAUNCH'" in text and 'runasoriginaluser' in text
