"""Szybki test działania programu (także zbudowanego EXE): `ImpoCraft.exe --self-test raport.txt`.

Tworzy próbny PDF w folderze tymczasowym, robi montaż ze znacznikami, preflight, programy dodatkowe,
buduje i zamyka okno programu. Raport zaczyna się od „OK” albo „BŁĄD”. Nie zmienia danych użytkownika.
"""
from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path


def _checks(folder: Path) -> list[str]:
    import pymupdf as fitz
    import barcodes
    import pdftools
    from engine import FILL_GROSS, Job, Project, Settings, export_pages, export_pdf, pt
    from preflight import inspect_project
    from user_data import data_dir, is_portable

    done = []
    src = folder / 'proba_A4.pdf'
    doc = fitz.open()
    for i in range(4):
        page = doc.new_page(width=pt(210), height=pt(297))
        page.draw_rect(fitz.Rect(30, 30, pt(210) - 30, pt(297) - 30), color=None, fill=(0.1, 0.6, 0.2))
        page.insert_text((60, 120), f'Strona {i + 1} zażółć', fontsize=30)
    doc.save(src)
    doc.close()
    done.append('PDF próbny')

    s = Settings(trim_w=105, trim_h=148, bleed=1.5, scale_mode=FILL_GROSS, white_trim=True,
                 gross_marks=True, reg_marks=True, slug_on=True, strip_on=True, mark_corners_on=True)
    project = Project(s, [Job(str(src), 2)])
    sheets = export_pdf(project, str(folder / 'montaz.pdf'))
    pages = export_pages(project, str(folder / 'strony.pdf'))
    done.append(f'eksport: {sheets} ark., {pages} str.')
    report = inspect_project(project)
    done.append(f'preflight: {report.errors} błędów, {report.warnings} uwag')
    pdftools.split_pages(str(src), str(folder / 'podzial'))
    pdftools.add_bleed(str(src), str(folder / 'spady.pdf'), (3, 3, 3, 3), (1, 1, 1, 1), (10, 10, 10, 10))
    barcodes.export_pdf(['4006381333931'], str(folder / 'ean.pdf'))
    done.append('programy dodatkowe')

    import app
    window = app.App()
    window.update()
    window.destroy()
    done.append('okno programu')
    done.append(f'dane użytkownika: {data_dir()} ({"przenośne" if is_portable() else "APPDATA"})')
    import updater
    done.append(f'aktualizacje: tryb {updater.install_mode()}, źródło {updater.API_URL}')
    return done


def run(report_path: str | None = None) -> int:
    lines: list[str]
    try:
        with tempfile.TemporaryDirectory() as folder:
            steps = _checks(Path(folder))
        lines = ['OK'] + [f'  - {step}' for step in steps]
        code = 0
    except Exception:
        lines = ['BŁĄD', traceback.format_exc()]
        code = 1
    text = '\n'.join(lines) + '\n'
    if report_path:
        Path(report_path).write_text(text, encoding='utf-8')
    elif sys.stdout:
        sys.stdout.write(text)
    return code


if __name__ == '__main__':
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
