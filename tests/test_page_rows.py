"""Tabela stron: wakaty, wstaw/zamień plik i stronę, kopiuj/wytnij/wklej, zaznaczanie (page_rows.py, H-45).

E1: menu tabeli stron Impozycjonera 4 — wstaw wakat PRZED / PO / TUTAJ, usuń wszystkie dodane wakaty, wstaw plik
PRZED / PO, zamień plik/stronę, zamień na inną stronę z pliku, kopiuj / wytnij / wklej, zaznacz ujęte / nieujęte /
takie same.
"""
import pymupdf as fitz
import pytest

import page_rows as pr
from engine import (ROLE_SKIP, Job, Project, Settings, export_pages, export_pdf, load_project, pt, project_sides,
                    open_sources, save_project)

COUNTS = {'a.pdf': 4, 'b.pdf': 2}.__getitem__


# --- wiersze jednej pozycji ---------------------------------------------------------------------

def test_sequence_and_storage():
    assert pr.sequence(None, 3) == [0, 1, 2]
    assert pr.sequence([3, None, 1], 3) == [2, None, 0]
    assert pr.stored([0, 1, 2], 3) is None                       # pełna kolejność = jak stary projekt
    assert pr.stored([2, None, 0], 3) == [3, None, 1]
    for bad in ([0], [4], ['1'], 'abc', [1.0]):
        with pytest.raises(ValueError):
            pr.sequence(bad, 3)


def test_vacancies():
    rows = [0, 1, 2]
    assert pr.insert_vacancy(rows, 1, pr.WHERE_BEFORE) == [0, None, 1, 2]
    assert pr.insert_vacancy(rows, 1, pr.WHERE_AFTER, 2) == [0, 1, None, None, 2]
    assert pr.insert_vacancy(rows, 2, pr.WHERE_HERE) == [0, 1, None]
    assert pr.remove_vacancies([None, 0, None, 1]) == [0, 1]
    assert pr.replace_page(rows, 0, 2, 3) == [2, 1, 2]
    with pytest.raises(ValueError):
        pr.insert_vacancy(rows, 3, pr.WHERE_BEFORE)
    with pytest.raises(ValueError):
        pr.replace_page(rows, 0, 3, 3)
    assert rows == [0, 1, 2]                                      # wejście bez zmian


# --- pozycje ------------------------------------------------------------------------------------

def test_insert_file_in_the_middle_splits_and_keeps_settings():
    jobs = [Job('a.pdf', page_roles={'2': ROLE_SKIP}, crop_x=1.5)]
    result = pr.insert_jobs(jobs, 0, 1, pr.WHERE_AFTER, [Job('b.pdf')], COUNTS)
    assert [(j.path, j.pages) for j in result] == [('a.pdf', [1, 2]), ('b.pdf', None), ('a.pdf', [3, 4])]
    assert result[0].page_roles == result[2].page_roles == {'2': ROLE_SKIP} and result[2].crop_x == 1.5
    assert result[0].page_roles is not result[2].page_roles       # osobne kopie
    assert jobs[0].pages is None                                  # wejście bez zmian
    before = pr.insert_jobs(jobs, 0, 0, pr.WHERE_BEFORE, [Job('b.pdf')], COUNTS)
    assert [j.path for j in before] == ['b.pdf', 'a.pdf'] and before[1].pages is None


def test_split_refused_for_copies_above_one():
    with pytest.raises(ValueError, match='nakładem 3'):
        pr.insert_jobs([Job('a.pdf', copies=3)], 0, 1, pr.WHERE_AFTER, [Job('b.pdf')], COUNTS)
    # na granicy pozycji wolno
    assert len(pr.insert_jobs([Job('a.pdf', copies=3)], 0, 3, pr.WHERE_AFTER, [Job('b.pdf')], COUNTS)) == 2


def test_replace_with_page_of_other_and_same_file():
    jobs = [Job('a.pdf')]
    other = pr.replace_with_page_of(jobs, 0, 2, Job('b.pdf'), 1, COUNTS)
    assert [(j.path, j.pages) for j in other] == [('a.pdf', [1, 2]), ('b.pdf', [2]), ('a.pdf', [4])]
    same = pr.replace_with_page_of(jobs, 0, 0, Job('a.pdf'), 3, COUNTS)
    assert [(j.path, j.pages) for j in same] == [('a.pdf', [4, 2, 3, 4])]
    with pytest.raises(ValueError):
        pr.replace_with_page_of(jobs, 0, 0, Job('b.pdf'), 2, COUNTS)


def test_cut_and_paste_restores_and_merges():
    jobs = [Job('a.pdf'), Job('b.pdf')]
    selection = [(0, 1), (0, 2)]
    clip = pr.copy_rows(jobs, selection, COUNTS)
    cut = pr.remove_rows(jobs, selection, COUNTS)
    assert [(j.path, j.pages) for j in cut] == [('a.pdf', [1, 4]), ('b.pdf', None)]
    back = pr.insert_jobs(cut, 0, 0, pr.WHERE_AFTER, pr.jobs_from_clipboard(clip, COUNTS), COUNTS)
    assert [(j.path, j.pages) for j in back] == [('a.pdf', None), ('b.pdf', None)]   # scalone, pełna kolejność
    # wklejenie stron pliku a za plikiem b
    pasted = pr.insert_jobs(jobs, 1, 1, pr.WHERE_AFTER, pr.jobs_from_clipboard(clip, COUNTS), COUNTS)
    assert [(j.path, j.pages) for j in pasted] == [('a.pdf', None), ('b.pdf', None), ('a.pdf', [2, 3])]
    assert [j.path for j in pr.remove_rows(jobs, [(1, 0), (1, 1)], COUNTS)] == ['a.pdf']   # pusta pozycja znika


def test_selection_helpers():
    jobs = [Job('a.pdf', page_roles={'2': ROLE_SKIP}, pages=[1, 2, None, 1]), Job('b.pdf')]
    assert pr.rows_excluded(jobs, COUNTS, ROLE_SKIP) == [(0, 1)]
    assert (0, 2) in pr.rows_included(jobs, COUNTS, ROLE_SKIP)    # wakat zajmuje pole — ujęty
    assert pr.rows_same(jobs, COUNTS, [(0, 0)]) == [(0, 0), (0, 3)]
    assert pr.rows_same(jobs, COUNTS, [(0, 2)]) == [(0, 2)]


# --- silnik i PDF --------------------------------------------------------------------------------

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=0, margin_x=10, margin_y=10, gap_x=5, gap_y=5,
            rotation='0', columns=2, rows=1, crop_marks=False)


def make_pdf(folder, name, pages):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40)).insert_text((10, 20), f'{name}{i + 1}')
    path = folder / f'{name}.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def placed(project):
    sources = open_sources(project.jobs)
    try:
        return [[None if p.source is None else (p.source.path[-5], p.source.index + 1) for p in side.placements]
                for side in project_sides(project, sources)]
    finally:
        for doc in sources.values():
            doc.close()


def test_single_sided_vacancy_and_inserted_file(tmp_path):
    a, b = make_pdf(tmp_path, 'a', 3), make_pdf(tmp_path, 'b', 1)
    jobs = pr.insert_jobs([Job(a)], 0, 0, pr.WHERE_AFTER, [Job(b)], lambda p: fitz.open(p).page_count)
    jobs[-1].pages = [None, 2, 3]                                 # wakat w miejscu strony 1 drugiej części
    project = Project(Settings(**BASE), jobs)
    assert placed(project) == [[('a', 1), ('b', 1)], [None, ('a', 2)], [('a', 3)]]
    out = tmp_path / 'm.pdf'
    assert export_pdf(project, str(out)) == 3


def test_duplex_vacancy_is_a_blank_page_in_pair(tmp_path):
    a = make_pdf(tmp_path, 'a', 3)
    project = Project(Settings(**{**BASE, 'columns': 1}, mode='Dwustronnie'), [Job(a, pages=[1, None, 2, 3])])
    sides = placed(project)
    assert sides[0] == [('a', 1)] and sides[1] == [None]          # para: strona 1 / wakat
    assert sides[2] == [('a', 2)] and sides[3] == [('a', 3)]


def test_single_page_export_keeps_vacancy_as_blank_page(tmp_path):
    a = make_pdf(tmp_path, 'a', 2)
    out = tmp_path / 's.pdf'
    export_pages(Project(Settings(**BASE), [Job(a, pages=[1, None, 2])]), str(out))
    with fitz.open(out) as doc:
        assert len(doc) == 3 and doc[1].get_text().strip() == '' and 'a2' in doc[2].get_text()


def test_project_roundtrip_and_invalid_rows(tmp_path):
    a = make_pdf(tmp_path, 'a', 2)
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(**BASE), [Job(a, pages=[2, None, 1]), Job(a)]), str(path))
    jobs = load_project(str(path)).jobs
    assert jobs[0].pages == [2, None, 1] and jobs[1].pages is None
    with pytest.raises(ValueError, match='poza zakresem'):
        placed(Project(Settings(**BASE), [Job(a, pages=[3])]))
