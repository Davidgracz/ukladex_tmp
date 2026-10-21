"""Aktualizacje z wydań (Releases) na GitHubie — logika bez interfejsu.

Przebieg: program pyta API GitHuba o najnowsze wydanie repozytorium `app_info.UPDATE_REPO`, porównuje numer wersji
z własnym, a gdy jest nowsza — pobiera instalator `ImpoCraft-<wersja>-instalator.exe` i plik z jego sumą SHA-256
(`…-instalator.exe.sha256`) z tego samego wydania, sprawdza sumę i uruchamia instalator po cichu z `/RELAUNCH`
(instalator po skończeniu sam włącza nową wersję). Pobieramy wyłącznie adresy
`https://github.com/<UPDATE_REPO>/releases/download/…`; inne adresy w odpowiedzi są odrzucane.
Wydania robocze (draft) i przedpremierowe (prerelease) są pomijane.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import app_info
import user_data

API_URL = f'https://api.github.com/repos/{app_info.UPDATE_REPO}/releases/latest'
DOWNLOAD_PREFIX = f'https://github.com/{app_info.UPDATE_REPO}/releases/download/'
STATE_FILE = 'update_state.json'
AUTO_CHECK_INTERVAL = 6 * 3600          # automatycznie najwyżej raz na 6 godzin
TIMEOUT = 15
MAX_INSTALLER = 500 * 1024 * 1024

MODE_INSTALLED = 'zainstalowany'
MODE_PORTABLE = 'przenośny'
MODE_SOURCE = 'z kodu'


def parse_version(text: str) -> tuple[int, ...]:
    """'v0.5.1' / '0.5.1' → (0, 5, 1). Inny zapis — ValueError."""
    match = re.fullmatch(r'v?(\d+(?:\.\d+){0,3})', str(text).strip())
    if not match:
        raise ValueError(f'Nieprawidłowy numer wersji: {text!r}')
    return tuple(int(part) for part in match.group(1).split('.'))


def _padded(version: tuple[int, ...]) -> tuple[int, ...]:
    return (version + (0, 0, 0, 0))[:4]


def is_newer(remote: str, local: str = app_info.VERSION) -> bool:
    return _padded(parse_version(remote)) > _padded(parse_version(local))


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    notes: str
    page_url: str
    installer_name: str
    installer_url: str
    sha256_url: str


def installer_name(version: str) -> str:
    return f'{app_info.APP_NAME}-{version}-instalator.exe'


def _trusted(url: str) -> bool:
    return isinstance(url, str) and url.startswith(DOWNLOAD_PREFIX) and '..' not in url


def release_info(data: dict) -> UpdateInfo | None:
    """Odczytuje odpowiedź API GitHuba. Brak wymaganych plików, wydanie robocze lub obcy adres → None."""
    if not isinstance(data, dict) or data.get('draft') or data.get('prerelease'):
        return None
    try:
        version = '.'.join(str(p) for p in parse_version(data.get('tag_name', '')))
    except ValueError:
        return None
    assets = {a.get('name'): a.get('browser_download_url') for a in data.get('assets') or [] if isinstance(a, dict)}
    name = installer_name(version)
    url, sha_url = assets.get(name), assets.get(name + '.sha256')
    if not (_trusted(url) and _trusted(sha_url)):
        return None
    return UpdateInfo(version=version, notes=str(data.get('body') or '').strip(),
                      page_url=str(data.get('html_url') or f'https://github.com/{app_info.UPDATE_REPO}/releases'),
                      installer_name=name, installer_url=url, sha256_url=sha_url)


def _request(url: str):
    return urllib.request.Request(url, headers={'User-Agent': f'{app_info.APP_NAME}/{app_info.VERSION}',
                                                'Accept': 'application/vnd.github+json'})


def fetch_json(url: str = API_URL) -> dict:
    with urllib.request.urlopen(_request(url), timeout=TIMEOUT) as response:
        return json.loads(response.read(2 * 1024 * 1024).decode('utf-8'))


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(_request(url), timeout=TIMEOUT) as response:
        return response.read(64 * 1024).decode('utf-8', 'replace')


def check(current: str = app_info.VERSION, fetch: Callable[[str], dict] = fetch_json) -> UpdateInfo | None:
    """Nowsze wydanie albo None (brak nowszego). Błędy sieci przechodzą do wywołującego."""
    info = release_info(fetch(API_URL))
    return info if info and is_newer(info.version, current) else None


def parse_sha256(text: str, name: str) -> str:
    """Suma z pliku .sha256 (format `suma  nazwa` albo sama suma)."""
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts or not re.fullmatch(r'[0-9a-fA-F]{64}', parts[0]):
            continue
        if len(parts) == 1 or parts[-1].lstrip('*') == name:
            return parts[0].lower()
    raise ValueError(f'Brak sumy SHA-256 dla {name}')


def download(info: UpdateInfo, folder: Path, *, opener=urllib.request.urlopen,
             text_fetch: Callable[[str], str] = fetch_text,
             progress: Callable[[int, int], None] | None = None) -> Path:
    """Pobiera instalator i sprawdza sumę SHA-256. Zła suma — plik usunięty i ValueError."""
    if not (_trusted(info.installer_url) and _trusted(info.sha256_url)):
        raise ValueError('Adres pobierania spoza repozytorium programu')
    expected = parse_sha256(text_fetch(info.sha256_url), info.installer_name)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / info.installer_name
    digest, done = hashlib.sha256(), 0
    with opener(_request(info.installer_url), timeout=TIMEOUT) as response, open(target, 'wb') as out:
        total = int(response.headers.get('Content-Length') or 0) if getattr(response, 'headers', None) else 0
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            done += len(chunk)
            if done > MAX_INSTALLER:
                break
            digest.update(chunk)
            out.write(chunk)
            if progress:
                progress(done, total)
    if done > MAX_INSTALLER or digest.hexdigest() != expected:
        target.unlink(missing_ok=True)
        raise ValueError('Pobrany instalator jest uszkodzony (suma SHA-256 się nie zgadza) — spróbuj ponownie')
    return target


# --- tryb programu i uruchomienie instalatora --------------------------------------------------

def install_mode() -> str:
    if user_data.is_portable():
        return MODE_PORTABLE
    import sys
    if getattr(sys, 'frozen', False) and (user_data.program_dir() / 'unins000.exe').is_file():
        return MODE_INSTALLED
    return MODE_SOURCE


def installer_args(program_dir: Path, local_appdata: str | None = None) -> list[str]:
    """Argumenty cichej aktualizacji. Instalacja w profilu użytkownika — bez uprawnień administratora."""
    local = local_appdata if local_appdata is not None else os.environ.get('LOCALAPPDATA', '')
    per_user = bool(local) and str(program_dir).lower().startswith(str(Path(local)).lower())
    return ['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/RELAUNCH', '/CURRENTUSER' if per_user else '/ALLUSERS']


def launch_installer(path: Path) -> None:
    """Uruchamia instalator w tle; program powinien się zaraz zamknąć (instalator podmienia jego pliki)."""
    subprocess.Popen([str(path), *installer_args(user_data.program_dir())], close_fds=True)


# --- stan: automatyczne sprawdzanie, pominięta wersja -----------------------------------------

def state_path() -> Path:
    return user_data.data_dir() / STATE_FILE


def load_state(path: Path | None = None) -> dict:
    path = path or state_path()
    state = {'auto_check': True, 'skipped': '', 'last_check': 0.0}
    try:
        stored = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(stored, dict):
            state['auto_check'] = bool(stored.get('auto_check', True))
            state['skipped'] = str(stored.get('skipped') or '')
            state['last_check'] = float(stored.get('last_check') or 0)
    except (OSError, ValueError, TypeError):
        pass
    return state


def save_state(state: dict, path: Path | None = None) -> None:
    path = path or state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def should_auto_check(state: dict, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return bool(state.get('auto_check', True)) and now - float(state.get('last_check') or 0) >= AUTO_CHECK_INTERVAL


def worth_showing(info: UpdateInfo | None, state: dict, manual: bool) -> bool:
    """Automatycznie nie pokazujemy wersji, którą użytkownik pominął; ręczne sprawdzenie pokazuje zawsze."""
    return info is not None and (manual or info.version != state.get('skipped'))
