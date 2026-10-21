"""Podpis cyfrowy plików EXE (Authenticode) narzędziem signtool z Windows SDK — opcjonalny krok budowania.

Certyfikat podajesz zmiennymi środowiskowymi (nigdy w plikach repozytorium):
  IMPOCRAFT_SIGN_THUMBPRINT  odcisk (SHA1) certyfikatu w magazynie Windows lub na tokenie USB — zalecane,
                             hasło/PIN pyta wtedy sterownik tokenu;
  IMPOCRAFT_SIGN_PFX         albo ścieżka do pliku .pfx,
  IMPOCRAFT_SIGN_PASSWORD    hasło do pliku .pfx (ustaw je w swojej konsoli, nie zapisuj w skryptach),
  IMPOCRAFT_SIGN_TIMESTAMP   serwer znacznika czasu (domyślnie DigiCert) — podpis pozostaje ważny po wygaśnięciu
                             certyfikatu.
Bez tych zmiennych skrypt nic nie robi i kończy się kodem 0 (budowanie bez podpisu).
Użycie: python scripts/sign_files.py plik1.exe [plik2.exe ...]
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMESTAMP = 'http://timestamp.digicert.com'
SECRET_ENV = 'IMPOCRAFT_SIGN_PASSWORD'


def signing_requested(env=os.environ) -> bool:
    return bool(env.get('IMPOCRAFT_SIGN_THUMBPRINT') or env.get('IMPOCRAFT_SIGN_PFX'))


def find_signtool() -> str | None:
    found = shutil.which('signtool')
    if found:
        return found
    roots = [os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), os.environ.get('ProgramFiles', r'C:\Program Files')]
    candidates: list[str] = []
    for root in roots:
        candidates += glob.glob(os.path.join(root, 'Windows Kits', '10', 'bin', '*', 'x64', 'signtool.exe'))
    return sorted(candidates)[-1] if candidates else None


def sign_command(signtool: str, files: list[str], env=os.environ) -> list[str]:
    """Polecenie signtool (SHA-256, znacznik czasu RFC 3161). Bez certyfikatu w env — ValueError."""
    command = [signtool, 'sign', '/fd', 'SHA256', '/tr', env.get('IMPOCRAFT_SIGN_TIMESTAMP') or DEFAULT_TIMESTAMP,
               '/td', 'SHA256']
    if env.get('IMPOCRAFT_SIGN_THUMBPRINT'):
        command += ['/sha1', env['IMPOCRAFT_SIGN_THUMBPRINT'].replace(' ', '')]
    elif env.get('IMPOCRAFT_SIGN_PFX'):
        command += ['/f', env['IMPOCRAFT_SIGN_PFX']]
        if env.get(SECRET_ENV):
            command += ['/p', env[SECRET_ENV]]
    else:
        raise ValueError('Brak certyfikatu: ustaw IMPOCRAFT_SIGN_THUMBPRINT albo IMPOCRAFT_SIGN_PFX')
    return command + list(files)


def printable(command: list[str]) -> str:
    """Polecenie do wypisania na ekran — hasło zamaskowane."""
    shown = list(command)
    if '/p' in shown:
        shown[shown.index('/p') + 1] = '********'
    return ' '.join(shown)


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    if not signing_requested():
        print('Podpis pominięty: nie ustawiono IMPOCRAFT_SIGN_THUMBPRINT ani IMPOCRAFT_SIGN_PFX.')
        return 0
    missing = [f for f in argv if not Path(f).is_file()]
    if not argv or missing:
        print(f'Brak plików do podpisu: {", ".join(missing) or "(nie podano)"}')
        return 1
    signtool = find_signtool()
    if not signtool:
        print('Nie znaleziono signtool.exe. Zainstaluj Windows SDK (składnik „Signing Tools”), np.:\n'
              '  winget install Microsoft.WindowsSDK.10.0.26100')
        return 1
    command = sign_command(signtool, argv)
    print(printable(command))
    code = subprocess.run(command).returncode
    if code == 0:
        code = subprocess.run([signtool, 'verify', '/pa', *argv]).returncode
    print('Podpis: OK' if code == 0 else f'Podpis NIE powiódł się (kod {code}).')
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
