"""Ramka dookoła każdego użytku (A) — życzenie użytkownika: „cienka czarna ramka dookoła każdego użytku” (H-50).

W Imp4 4.0.4.0 ramka netto / brutto z kolorem jest tylko w programie do banerów (E1: „+RAMKA NETTO”, „+RAMKA BRUTTO”).
"""
import pymupdf as fitz
import pytest

from engine import Job, Project, Settings, export_pdf, geometry, load_project, mm, pt, save_project, validate

BASE = dict(sheet_w=200, sheet_h=150, trim_w=50, trim_h=40, bleed=2, margin_x=10, margin_y=10, gap_x=6, gap_y=6,
            rotation='0', columns=2, rows=2, crop_marks=False)


def make_pdf(folder, pages=3):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=pt(50), height=pt(40)).insert_text((20, 30), f'p{i + 1}')
    path = folder / 'a.pdf'
    doc.save(path)
    doc.close()
    return str(path)


def frames(path):
    with fitz.open(path) as doc:
        found = []
        for d in doc[0].get_drawings():
            if d.get('fill') is None and d['items'] and d['items'][0][0] == 're':
                r = d['items'][0][1]
                found.append(((round(mm(r.x0), 2), round(mm(r.y0), 2), round(mm(r.x1), 2), round(mm(r.y1), 2)),
                              d.get('color'), round(d.get('width') or 0, 2)))
        return found


def expected(s, bleed):
    out = []
    for sl in geometry(s).slots[:3]:                                # 3 strony = 3 zajęte pola z 4
        out.append(tuple(round(v, 2) for v in (sl.x - bleed, sl.y - bleed, sl.x + sl.w + bleed, sl.y + sl.h + bleed)))
    return out


def test_net_frame_on_each_placed_use(tmp_path):
    s = Settings(**BASE, frame_on=True)
    out = tmp_path / 'r.pdf'
    export_pdf(Project(s, [Job(make_pdf(tmp_path))]), str(out))
    found = frames(out)
    assert sorted(r for r, _, _ in found) == sorted(expected(s, 0))     # puste pole bez ramki
    assert all(width == 0.25 for *_, width in found)
    with fitz.open(out) as doc:
        assert '0 0 0 1 K' in doc[0].read_contents().decode('latin-1')   # K 100 %


def test_gross_and_both_frames(tmp_path):
    src = make_pdf(tmp_path)
    both = Settings(**BASE, frame_on=True, frame_gross=True, frame_pt=0.5, frame_color='Czarny (dotychczasowy)')
    out = tmp_path / 'b.pdf'
    export_pdf(Project(both, [Job(src)]), str(out))
    assert sorted(r for r, _, _ in frames(out)) == sorted(expected(both, 0) + expected(both, 2))
    gross_only = Settings(**BASE, frame_on=True, frame_net=False, frame_gross=True)
    export_pdf(Project(gross_only, [Job(src)]), str(tmp_path / 'g.pdf'))
    assert sorted(r for r, _, _ in frames(tmp_path / 'g.pdf')) == sorted(expected(gross_only, 2))


def test_off_by_default_and_validation(tmp_path):
    out = tmp_path / 'o.pdf'
    export_pdf(Project(Settings(**BASE), [Job(make_pdf(tmp_path))]), str(out))
    assert frames(out) == []
    for bad in (dict(frame_pt=0), dict(frame_pt=6), dict(frame_color='zielony'),
                dict(frame_on=True, frame_net=False, frame_gross=False)):
        with pytest.raises(ValueError):
            validate(Settings(**BASE, **bad))


def test_project_roundtrip(tmp_path):
    path = tmp_path / 'p.psimp'
    save_project(Project(Settings(**BASE, frame_on=True, frame_gross=True, frame_pt=0.1), [Job(make_pdf(tmp_path))]),
                 str(path))
    s = load_project(str(path)).settings
    assert (s.frame_on, s.frame_gross, s.frame_pt) == (True, True, 0.1)
