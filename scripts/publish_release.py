"""Publikuje wydanie ImpoCraft na GitHubie (Releases) — z niego zainstalowane programy pobierają aktualizacje.

Najpierw zbuduj instalator (BUILD_INSTALLER_WINDOWS.bat). Skrypt:
  1. bierze wersję z app_info.py,
  2. dołącza dist/ImpoCraft-<wersja>-instalator.exe, plik z jego sumą SHA-256 (sprawdzany przez program przed
     instalacją) i wersję przenośną dist/ImpoCraft-<wersja>-przenosny.zip,
  3. opis zmian bierze z CHANGELOG.md (sekcja „## <wersja>” albo „## Unreleased”),
  4. tworzy wydanie z tagiem v<wersja> poleceniem `gh release create` (wymaga zalogowanego gh).
Użycie: python scripts/publish_release.py [--dry-run]
Numer wersji podnieś w app_info.py przed budowaniem — program proponuje aktualizację tylko do wyższej wersji.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_info  # noqa: E402
import updater  # noqa: E402


def sha256_line(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return f'{digest.hexdigest()}  {path.name}\n'


def changelog_notes(text: str, version: str) -> str:
    """Treść sekcji „## <wersja>” (albo „## Unreleased”) z CHANGELOG.md, bez nagłówka."""
    lines = text.splitlines()
    for heading in (f'## {version}', f'## v{version}', '## Unreleased'):
        for start, line in enumerate(lines):
            if line.strip() == heading:
                body = []
                for following in lines[start + 1:]:
                    if following.startswith('## '):
                        break
                    body.append(following)
                return '\n'.join(body).strip()
    return ''


def release_files(version: str, dist: Path) -> list[Path]:
    """Pliki wydania; brak instalatora — FileNotFoundError. Tworzy plik .sha256 i nazwaną kopię ZIP."""
    installer = dist / updater.installer_name(version)
    if not installer.is_file():
        raise FileNotFoundError(f'Brak {installer} — najpierw uruchom BUILD_INSTALLER_WINDOWS.bat')
    checksum = dist / (installer.name + '.sha256')
    checksum.write_text(sha256_line(installer), encoding='utf-8', newline='\n')
    files = [installer, checksum]
    portable = dist / f'{app_info.APP_NAME}-przenosny.zip'
    if portable.is_file():
        named = dist / f'{app_info.APP_NAME}-{version}-przenosny.zip'
        shutil.copyfile(portable, named)
        files.append(named)
    return files


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    dry = '--dry-run' in argv
    version = app_info.VERSION
    files = release_files(version, ROOT / 'dist')
    notes = changelog_notes((ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), version) or f'{app_info.APP_NAME} {version}'
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as stream:
        stream.write(notes)
        notes_file = stream.name
    command = ['gh', 'release', 'create', f'v{version}', *map(str, files), '--repo', app_info.UPDATE_REPO,
               '--title', f'{app_info.APP_NAME} {version}', '--notes-file', notes_file]
    print(' '.join(command))
    if dry:
        print(notes)
        return 0
    code = subprocess.run(command).returncode
    Path(notes_file).unlink(missing_ok=True)
    print('Wydanie opublikowane.' if code == 0 else f'Publikacja nie powiodła się (kod {code}).')
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
