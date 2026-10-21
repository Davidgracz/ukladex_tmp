"""Okno „Korekta rozmiaru strony” — tabela stron → PPM → „Koryguj rozmiar strony…”.

Odpowiednik okna Impozycjonera 4 „Korekta położenia i rozmiaru obszaru netto”: podgląd strony z ramką netto
(przeciąganie myszą przesuwa ramkę), rozmiar i położenie w mm, zakres (ta strona / wszystkie / nieparzyste /
parzyste, w pliku albo w całej tabeli), powrót do wartości z pliku i ustawienie rozmiaru użytka, kadrowanie pliku
do obszaru netto albo brutto z zapisem do nowego pliku (engine.crop_to_file).
Logika: page_boxes.py; zastosowanie w silniku: engine.apply_page_boxes (TrimBox tylko w pamięci).
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import pymupdf as fitz
from PIL import Image, ImageTk

import page_boxes as pb
from engine import mm

PREVIEW = 360


def page_info(path: str, index: int) -> tuple[float, float, tuple[float, float, float, float], Image.Image]:
    """Widoczny rozmiar strony (mm), TrimBox z pliku jako ramka (mm) i obraz podglądu."""
    with fitz.open(path) as doc:
        page = doc[index]
        width, height = mm(page.rect.width), mm(page.rect.height)
        trim = fitz.Rect(page.trimbox) - (page.cropbox.x0, page.cropbox.y0, page.cropbox.x0, page.cropbox.y0)
        visible = trim * page.rotation_matrix
        visible.normalize()
        box = (mm(visible.x0), mm(visible.y0), mm(visible.width), mm(visible.height))
        zoom = PREVIEW / max(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    return width, height, tuple(round(v, 2) for v in box), image


def file_page_sizes(path: str) -> list[tuple[float, float]]:
    with fitz.open(path) as doc:
        return [(round(mm(p.rect.width), 2), round(mm(p.rect.height), 2)) for p in doc]


class PageBoxDialog(tk.Toplevel):
    def __init__(self, app, job_index: int, page_index: int):
        super().__init__(app)
        self.app = app
        self.job_index, self.page = job_index, page_index + 1
        job = app.project.jobs[job_index]
        self.page_w, self.page_h, self.file_box, image = page_info(job.path, page_index)
        current = job.page_boxes.get(str(self.page)) or self.file_box
        self.title(f'Korekta rozmiaru strony — {Path(job.path).name}, strona {self.page}')
        self.transient(app)
        self.resizable(False, False)
        body = ttk.Frame(self, padding=14)
        body.pack(fill='both', expand=True)

        self.scale = image.width / self.page_w  # piksele na mm
        self.photo = ImageTk.PhotoImage(image, master=self)
        self.canvas = tk.Canvas(body, width=image.width + 2, height=image.height + 2, background='#dde2e8',
                                highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=12, sticky='n', padx=(0, 14))
        self.canvas.create_image(1, 1, image=self.photo, anchor='nw')
        x0, y0, w, h = self.file_box
        self.canvas.create_rectangle(*self._px(x0, y0, w, h), outline='#7a8696', dash=(3, 3))
        self.box_item = self.canvas.create_rectangle(0, 0, 1, 1, outline='#e8711a', width=2)
        self.canvas.bind('<ButtonPress-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag)
        ttk.Label(body, text='szara przerywana = TrimBox z pliku, pomarańczowa = nowa ramka netto\n'
                             '(przeciągnij myszą, aby przesunąć)', foreground='#66768a').grid(
            row=12, column=0, sticky='w', pady=(6, 0))

        info = (f'Strona: {self.page_w:g} × {self.page_h:g} mm   •   TrimBox z pliku: '
                f'{self.file_box[2]:g} × {self.file_box[3]:g} mm')
        ttk.Label(body, text=info).grid(row=0, column=1, columnspan=2, sticky='w')
        self.vars = {}
        for row, (key, label, value) in enumerate((('w', 'Szerokość netto (H) [mm]', current[2]),
                                                   ('h', 'Wysokość netto (V) [mm]', current[3]),
                                                   ('l', 'Z lewej [mm]', current[0]),
                                                   ('t', 'Od góry [mm]', current[1])), start=1):
            ttk.Label(body, text=label).grid(row=row, column=1, sticky='w', pady=2)
            self.vars[key] = tk.StringVar(value=f'{value:g}')
            entry = ttk.Spinbox(body, textvariable=self.vars[key], from_=0, to=5000, increment=0.5, width=9,
                                command=self._redraw)
            entry.grid(row=row, column=2, sticky='e', padx=(8, 0))
            entry.bind('<KeyRelease>', lambda e: self._redraw())
        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=1, columnspan=2, sticky='ew', pady=(4, 6))
        ttk.Button(buttons, text='Wyśrodkuj', command=self._centre).pack(side='left')
        ttk.Button(buttons, text='= użytek netto', command=self._use_size).pack(side='left', padx=4)
        ttk.Button(buttons, text='Z pliku', command=self._from_file).pack(side='left')

        ttk.Label(body, text='Zakres korekty:').grid(row=6, column=1, sticky='w', pady=(6, 0))
        self.scope = tk.StringVar(value=pb.SCOPE_PAGE)
        for row, scope in enumerate(pb.SCOPES, start=7):
            ttk.Radiobutton(body, text=scope, value=scope, variable=self.scope).grid(row=row, column=1, columnspan=2,
                                                                                    sticky='w')
        self.whole_table = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text='w całej tabeli (wszystkie pliki)', variable=self.whole_table).grid(
            row=11, column=1, columnspan=2, sticky='w', pady=(2, 0))
        self.set_use = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text='ustaw rozmiar użytka na ten rozmiar netto', variable=self.set_use).grid(
            row=12, column=1, columnspan=2, sticky='w')
        ttk.Label(body, text='Korekta obejmuje tylko strony o tym samym rozmiarze co ta strona (jak w Imp4).\n'
                             'Plik PDF na dysku się nie zmienia — korekta zapisuje się w projekcie.',
                  foreground='#66768a').grid(row=13, column=1, columnspan=2, sticky='w', pady=(6, 0))
        crop = ttk.Frame(body)
        crop.grid(row=14, column=0, columnspan=3, sticky='w', pady=(12, 0))
        from engine import CROP_BLEED, CROP_GROSS, CROP_NET
        ttk.Button(crop, text='Kadruj do obszaru netto (bez spadów) i zapisz do pliku…',
                   command=lambda: self._crop(CROP_NET)).pack(anchor='w')
        ttk.Button(crop, text=f'Kadruj do obszaru brutto (netto + {CROP_BLEED:g} mm spadu) i zapisz do pliku…',
                   command=lambda: self._crop(CROP_GROSS)).pack(anchor='w', pady=(2, 0))
        actions = ttk.Frame(body)
        actions.grid(row=15, column=0, columnspan=3, sticky='e', pady=(12, 0))
        ttk.Button(actions, text='Anuluj', command=self.destroy).pack(side='right')
        ttk.Button(actions, text='Przywróć wartości z pliku', command=lambda: self._apply(reset=True)).pack(
            side='right', padx=6)
        ttk.Button(actions, text='Zastosuj', style='Accent.TButton', command=self._apply).pack(side='right')
        self._redraw()

    def _crop(self, area):
        """Kadrowanie całego pliku z ramką netto widoczną w oknie (zakres jak przy „Zastosuj”, tylko ten plik)."""
        values = self._values()
        try:
            if values is None:
                raise ValueError('Wpisz liczby (mm).')
            box = pb.check_box(values, self.page_w, self.page_h)
        except ValueError as exc:
            messagebox.showerror('Kadruj i zapisz', str(exc), parent=self)
            return
        jobs = self.app.project.jobs
        targets, _ = pb.plan_correction([file_page_sizes(job.path) for job in jobs], self.job_index, self.page,
                                        self.scope.get(), False)
        job = jobs[self.job_index]
        source = replace(job, page_boxes=pb.apply(job.page_boxes, targets.get(self.job_index, []), box))
        self.app.crop_and_save(area, self.job_index, parent=self, source=source)

    # --- ramka ---------------------------------------------------------------------------------------
    def _px(self, left, top, width, height):
        s = self.scale
        return 1 + left * s, 1 + top * s, 1 + (left + width) * s, 1 + (top + height) * s

    def _values(self):
        try:
            return tuple(float(self.vars[k].get().replace(',', '.')) for k in ('l', 't', 'w', 'h'))
        except ValueError:
            return None

    def _set(self, box):
        for key, value in zip(('l', 't', 'w', 'h'), box):
            self.vars[key].set(f'{round(value, 2):g}')
        self._redraw()

    def _redraw(self):
        box = self._values()
        if box:
            self.canvas.coords(self.box_item, *self._px(*box))

    def _drag_start(self, event):
        self._last = (event.x, event.y)

    def _drag(self, event):
        box = self._values()
        if not box:
            return
        dx, dy = (event.x - self._last[0]) / self.scale, (event.y - self._last[1]) / self.scale
        self._last = (event.x, event.y)
        left = min(max(0.0, box[0] + dx), self.page_w - box[2])
        top = min(max(0.0, box[1] + dy), self.page_h - box[3])
        self._set((left, top, box[2], box[3]))

    def _centre(self):
        box = self._values()
        if box:
            try:
                self._set(pb.centred(self.page_w, self.page_h, box[2], box[3]))
            except ValueError as exc:
                messagebox.showerror('Korekta rozmiaru', str(exc), parent=self)

    def _use_size(self):
        s = self.app._read_fields()
        try:
            self._set(pb.centred(self.page_w, self.page_h, s.trim_w, s.trim_h))
        except ValueError as exc:
            messagebox.showerror('Korekta rozmiaru', str(exc), parent=self)

    def _from_file(self):
        self._set(self.file_box)

    # --- zastosowanie ---------------------------------------------------------------------------------
    def _apply(self, reset: bool = False):
        jobs = self.app.project.jobs
        box = None
        if not reset:
            values = self._values()
            try:
                if values is None:
                    raise ValueError('Wpisz liczby (mm).')
                box = pb.check_box(values, self.page_w, self.page_h)
            except ValueError as exc:
                messagebox.showerror('Korekta rozmiaru', str(exc), parent=self)
                return
        sizes = [file_page_sizes(job.path) for job in jobs]
        targets, skipped = pb.plan_correction(sizes, self.job_index, self.page, self.scope.get(),
                                              self.whole_table.get())
        for f, pages in targets.items():
            jobs[f].page_boxes = pb.apply(jobs[f].page_boxes, pages, box)
        if self.set_use.get() and box is not None:
            self.app.variables['trim_w'].set(f'{box[2]:g}')
            self.app.variables['trim_h'].set(f'{box[3]:g}')
            self.app.trim_preset_var.set('Niestandardowy')
        changed = sum(len(p) for p in targets.values())
        message = (f'{"Przywrócono wartości z pliku" if reset else "Skorygowano"} na {changed} str.')
        if skipped:
            listing = ', '.join(f'{Path(jobs[f].path).name} s.{p}' for f, p in skipped[:12])
            more = f' (+{len(skipped) - 12})' if len(skipped) > 12 else ''
            message += (f'\n\nPominięto {len(skipped)} str. o innym rozmiarze niż strona korygowana:\n'
                        f'{listing}{more}')
        self.app._render_jobs(self.job_index)
        self.app.side_index = 0
        self.app.refresh()
        self.destroy()
        messagebox.showinfo('Korekta rozmiaru strony', message, parent=self.app)


class ResizeDialog(tk.Toplevel):
    """„Zmień rozmiar zaznaczonych stron” — jak „Zmień parametry w zaznaczonych wierszach” w Impozycjonerze
    (Szerokość / Wysokość) z opcjami okna „Automatyczna konwersja bitmap do PDF” (sposób, orientacja, spad)."""

    def __init__(self, app, rows: list[tuple[int, int]]):
        super().__init__(app)
        self.app, self.rows = app, rows
        self.title('Zmień rozmiar zaznaczonych stron')
        self.transient(app)
        self.resizable(False, False)
        body = ttk.Frame(self, padding=14)
        body.pack(fill='both', expand=True)
        first = app.project.jobs[rows[0][0]].page_sizes.get(str(rows[0][1] + 1)) or {}
        s = app._read_fields()
        ttk.Label(body, text=f'Zaznaczone strony: {len(rows)}', style='Header.TLabel').grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 6))
        ttk.Label(body, text='Sposób określania szerokości i wysokości:').grid(row=1, column=0, columnspan=3, sticky='w')
        self.mode = tk.StringVar(value=first.get('mode', pb.RESIZE_STRETCH))
        self.crop = tk.BooleanVar(value=self.mode.get() == pb.RESIZE_CROP)
        if self.mode.get() == pb.RESIZE_CROP:
            self.mode.set(pb.RESIZE_STRETCH)
        ttk.Radiobutton(body, text='Szerokość i wysokość: niezależnie', value=pb.RESIZE_STRETCH, variable=self.mode,
                        command=self._states).grid(row=2, column=0, columnspan=3, sticky='w')
        self.crop_box = ttk.Checkbutton(body, text='Włącz kadrowanie (zachowaj proporcje, przytnij nadmiar)',
                                        variable=self.crop)
        self.crop_box.grid(row=3, column=0, columnspan=3, sticky='w', padx=(22, 0))
        ttk.Radiobutton(body, text=pb.RESIZE_WIDTH, value=pb.RESIZE_WIDTH, variable=self.mode,
                        command=self._states).grid(row=4, column=0, columnspan=3, sticky='w')
        ttk.Radiobutton(body, text=pb.RESIZE_HEIGHT, value=pb.RESIZE_HEIGHT, variable=self.mode,
                        command=self._states).grid(row=5, column=0, columnspan=3, sticky='w')
        ttk.Label(body, text='Nowa szerokość i wysokość TrimBox:').grid(row=6, column=0, columnspan=3, sticky='w',
                                                                        pady=(8, 0))
        self.w = tk.StringVar(value=f'{first.get("w", s.trim_w):g}')
        self.h = tk.StringVar(value=f'{first.get("h", s.trim_h):g}')
        ttk.Label(body, text='Szerokość [mm]:').grid(row=7, column=0, sticky='w')
        self.w_entry = ttk.Spinbox(body, textvariable=self.w, from_=1, to=5000, increment=0.5, width=9)
        self.w_entry.grid(row=7, column=1, sticky='w', padx=6)
        ttk.Label(body, text='Wysokość [mm]:').grid(row=8, column=0, sticky='w')
        self.h_entry = ttk.Spinbox(body, textvariable=self.h, from_=1, to=5000, increment=0.5, width=9)
        self.h_entry.grid(row=8, column=1, sticky='w', padx=6)
        quick = ttk.Frame(body)
        quick.grid(row=7, column=2, rowspan=2, sticky='w')
        ttk.Button(quick, text='= netto użytku', command=lambda: self._preset(False)).pack(fill='x')
        ttk.Button(quick, text='= brutto (netto + 2 × spad)', command=lambda: self._preset(True)).pack(fill='x', pady=(2, 0))
        self.keep = tk.BooleanVar(value=first.get('keep_orientation', True))
        ttk.Checkbutton(body, text='Zachowaj orientację (pion/poziom)', variable=self.keep).grid(
            row=9, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self.bleed_on = tk.BooleanVar(value=first.get('bleed', 0) > 0)
        self.bleed = tk.StringVar(value=f'{first.get("bleed", 0) or 3:g}')
        row = ttk.Frame(body)
        row.grid(row=10, column=0, columnspan=3, sticky='w')
        ttk.Checkbutton(row, text='Definiuj spad [mm]:', variable=self.bleed_on).pack(side='left')
        ttk.Spinbox(row, textvariable=self.bleed, from_=0, to=50, increment=0.5, width=6).pack(side='left', padx=6)
        ttk.Label(body, text='Strona jest skalowana wektorowo, tak że TrimBox ma podany rozmiar. Spad wypełnia\n'
                             'grafika źródła spoza TrimBox (jeśli jest). Plik PDF na dysku się nie zmienia.',
                  foreground='#66768a').grid(row=11, column=0, columnspan=3, sticky='w', pady=(8, 0))
        actions = ttk.Frame(body)
        actions.grid(row=12, column=0, columnspan=3, sticky='e', pady=(12, 0))
        ttk.Button(actions, text='Anuluj', command=self.destroy).pack(side='right')
        ttk.Button(actions, text='Przywróć rozmiar z pliku', command=lambda: self._apply(None)).pack(side='right', padx=6)
        ttk.Button(actions, text='Zmień', style='Accent.TButton', command=self._submit).pack(side='right')
        self._states()

    def _states(self):
        mode = self.mode.get()
        self.crop_box.configure(state='normal' if mode == pb.RESIZE_STRETCH else 'disabled')
        self.w_entry.configure(state='disabled' if mode == pb.RESIZE_HEIGHT else 'normal')
        self.h_entry.configure(state='disabled' if mode == pb.RESIZE_WIDTH else 'normal')

    def _preset(self, gross: bool):
        s = self.app._read_fields()
        extra = 0.0
        if gross:
            from engine import bleed_for
            extra = 2 * bleed_for(s)
        self.w.set(f'{s.trim_w + extra:g}')
        self.h.set(f'{s.trim_h + extra:g}')

    def _submit(self):
        mode = self.mode.get()
        if mode == pb.RESIZE_STRETCH and self.crop.get():
            mode = pb.RESIZE_CROP
        try:
            w = float(self.w.get().replace(',', '.')) if mode != pb.RESIZE_HEIGHT else 1.0
            h = float(self.h.get().replace(',', '.')) if mode != pb.RESIZE_WIDTH else 1.0
            bleed = float(self.bleed.get().replace(',', '.')) if self.bleed_on.get() else 0.0
            spec = pb.resize_spec(w, h, mode, self.keep.get(), bleed)
        except ValueError as exc:
            messagebox.showerror('Zmień rozmiar stron', str(exc) if 'could not convert' not in str(exc)
                                 else 'Wpisz liczby (mm).', parent=self)
            return
        self._apply(spec)

    def _apply(self, spec):
        jobs = self.app.project.jobs
        for job_index, page_index in self.rows:
            sizes = dict(jobs[job_index].page_sizes)
            if spec is None:
                sizes.pop(str(page_index + 1), None)
            else:
                sizes[str(page_index + 1)] = dict(spec)
            jobs[job_index].page_sizes = sizes
        self.app._render_jobs(self.rows[0][0])
        self.app.side_index = 0
        self.app.refresh()
        self.destroy()
