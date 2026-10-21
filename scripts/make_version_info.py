"""Tworzy plik informacji o wersji dla PyInstallera (--version-file) z app_info.py.

Windows pokazuje te dane we Właściwościach pliku EXE → Szczegóły: nazwa produktu, wersja, firma, prawa autorskie.
Obok zapisuje też `app_info.iss` — te same dane jako definicje dla instalatora (packaging/ImpoCraft.iss).
Użycie: python scripts/make_version_info.py build/version_info.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_info  # noqa: E402

TEMPLATE = """# Wygenerowane przez scripts/make_version_info.py — nie edytować ręcznie.
VSVersionInfo(
  ffi=FixedFileInfo(filevers={ver}, prodvers={ver}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041504B0', [
      StringStruct('CompanyName', {author!r}),
      StringStruct('FileDescription', {description!r}),
      StringStruct('FileVersion', {version!r}),
      StringStruct('InternalName', {exe!r}),
      StringStruct('LegalCopyright', {copyright!r}),
      StringStruct('OriginalFilename', {exe_file!r}),
      StringStruct('ProductName', {name!r}),
      StringStruct('ProductVersion', {version!r})])]),
    VarFileInfo([VarStruct('Translation', [0x0415, 1200])])
  ]
)
"""


def render() -> str:
    return TEMPLATE.format(ver=app_info.version_tuple(), author=app_info.AUTHOR,
                           description=f'{app_info.APP_NAME} — {app_info.DESCRIPTION}',
                           version=app_info.VERSION, exe=app_info.EXE_NAME, exe_file=f'{app_info.EXE_NAME}.exe',
                           copyright=app_info.COPYRIGHT, name=app_info.APP_NAME)


def render_iss() -> str:
    values = {'AppName': app_info.APP_NAME, 'AppVersion': app_info.VERSION, 'AppPublisher': app_info.AUTHOR,
              'AppId': app_info.INSTALLER_APP_ID, 'AppCopyright': app_info.COPYRIGHT,
              'AppDescription': app_info.DESCRIPTION, 'AppExe': f'{app_info.EXE_NAME}.exe'}
    for key, value in values.items():
        if '"' in value:
            raise ValueError(f'Cudzysłów w {key} psuje skrypt instalatora')
    return '; Wygenerowane przez scripts/make_version_info.py\n' + ''.join(
        f'#define {key} "{value}"\n' for key, value in values.items())


def main(argv: list[str]) -> int:
    target = Path(argv[0] if argv else 'build/version_info.txt')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(), encoding='utf-8')
    # Inno Setup rozpoznaje UTF-8 po znaczniku BOM (polskie znaki, ©)
    (target.parent / 'app_info.iss').write_text(render_iss(), encoding='utf-8-sig')
    print(target)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
