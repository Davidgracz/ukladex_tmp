"""Panele generatorów kodów w „Programach dodatkowych”: QR (rodzaje treści), Data Matrix (zwykły i numery seryjne),
EAN-13 / EAN-8. Treść można wpisać albo wczytać z pliku .txt. Logika: codes.py, barcodes.py.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import barcodes
import codes
import marks

MUTED = '#66768a'
PANEL = '#ffffff'
TEXT = '#1f2933'


class _CodePanel(ttk.Frame):
    """Wspólne: pole tekstowe (wpisz lub wczytaj .txt), parametry wydruku, podgląd, generowanie."""
    kind = codes.QR
    default_size = '20'
    default_quiet = '4'
    default_name = 'kody'

    def __init__(self, parent, log):
        super().__init__(parent)
        self.log = log
        self.columnconfigure(0, weight=1)
        self.preview_image = None

    # --- elementy wspólne
    def _text_box(self, parent, row, label):
        box = ttk.Frame(parent)
        box.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(4, 2))
        box.columnconfigure(0, weight=1)
        ttk.Label(box, text=label).grid(row=0, column=0, sticky='w')
        self.count_var = tk.StringVar(value='')
        ttk.Label(box, textvariable=self.count_var, foreground=MUTED).grid(row=0, column=1, sticky='e')
        self.text = tk.Text(box, height=6, width=60, bg=PANEL, fg=TEXT, relief='solid', borderwidth=1,
                            font=('Consolas', 10), wrap='none', undo=True)
        self.text.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.text.bind('<<Modified>>', self._count)
        buttons = ttk.Frame(box)
        buttons.grid(row=2, column=0, columnspan=2, sticky='w', pady=(3, 0))
        ttk.Button(buttons, text='Wczytaj z pliku .txt…', command=self._load_txt).pack(side='left')
        ttk.Button(buttons, text='Wyczyść', command=lambda: self.text.delete('1.0', 'end')).pack(side='left', padx=6)
        return box

    def _count(self, *_):
        self.text.edit_modified(False)
        n = len([line for line in self.text.get('1.0', 'end').splitlines() if line.strip()])
        self.count_var.set(f'kodów: {n}' if n else 'jeden kod w wierszu')

    def _load_txt(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[('Plik tekstowy', '*.txt'), ('Wszystkie', '*.*')])
        if not path:
            return
        try:
            content = Path(path).read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            content = Path(path).read_text(encoding='cp1250')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', content)
        self._count()

    def _print_options(self, parent, row, ec=False, square=False):
        box = ttk.LabelFrame(parent, text='Wydruk', padding=(8, 4))
        box.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(6, 2))
        self.size_var = tk.StringVar(value=self.default_size)
        self.quiet_var = tk.StringVar(value=self.default_quiet)
        self.color_var = tk.StringVar(value='0/0/0/100')
        for col, (label, var, width) in enumerate((('Rozmiar kodu [mm]:', self.size_var, 6),
                                                   ('Margines [moduły]:', self.quiet_var, 4),
                                                   ('Kolor C/M/Y/K [%]:', self.color_var, 12))):
            ttk.Label(box, text=label).grid(row=0, column=col * 2, sticky='w', padx=(0 if col == 0 else 10, 3))
            ttk.Entry(box, textvariable=var, width=width).grid(row=0, column=col * 2 + 1, sticky='w')
        self.ec_var = tk.StringVar(value='M')
        if ec:
            ttk.Label(box, text='Korekcja błędów:').grid(row=1, column=0, sticky='w', pady=(4, 0))
            levels = ttk.Frame(box)
            levels.grid(row=1, column=1, columnspan=5, sticky='w', pady=(4, 0))
            for level, text in (('L', 'L (7 %)'), ('M', 'M (15 %)'), ('Q', 'Q (25 %)'), ('H', 'H (30 %)')):
                ttk.Radiobutton(levels, text=text, value=level, variable=self.ec_var).pack(side='left', padx=(0, 8))
        self.square_var = tk.BooleanVar(value=True)
        flags = ttk.Frame(box)
        flags.grid(row=2, column=0, columnspan=6, sticky='w', pady=(4, 0))
        if square:
            ttk.Checkbutton(flags, text='Kwadratowy', variable=self.square_var).pack(side='left', padx=(0, 10))
        self.transparent_var = tk.BooleanVar(value=False)
        self.caption_var = tk.BooleanVar(value=False)
        self.separate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags, text='Tło przezroczyste', variable=self.transparent_var).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(flags, text='Podpis pod kodem', variable=self.caption_var).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(flags, text='Każdy kod w osobnym pliku', variable=self.separate_var).pack(side='left')

    def _actions(self, parent, row):
        box = ttk.Frame(parent)
        box.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        ttk.Button(box, text='Generuj PDF…', style='Accent.TButton', command=self.generate).pack(side='left')
        ttk.Button(box, text='Podgląd', command=self.preview).pack(side='left', padx=6)
        self.preview_label = ttk.Label(box)
        self.preview_label.pack(side='left', padx=(12, 0))

    def _number(self, var, label, kind=float):
        try:
            return kind(var.get().strip().replace(',', '.'))
        except ValueError:
            raise ValueError(f'{label}: wpisz liczbę') from None

    # --- do nadpisania
    def values(self) -> list[str]:
        raise NotImplementedError

    # --- generowanie
    def _items(self):
        values = self.values()
        if not values:
            raise ValueError('Brak treści — wpisz tekst (jeden kod w wierszu) albo wczytaj plik .txt')
        return [(v, codes.matrix(self.kind, v, self.ec_var.get(), self.square_var.get())) for v in values]

    def preview(self):
        try:
            value, cells = self._items()[0]
        except Exception as exc:
            messagebox.showerror(self.kind, str(exc), parent=self)
            return
        n = max(len(cells), len(cells[0]))
        scale = max(1, 96 // (n + 4))
        image = Image.new('L', ((len(cells[0]) + 4) * scale, (len(cells) + 4) * scale), 255)
        for r, row in enumerate(cells):
            for c, dark in enumerate(row):
                if dark:
                    image.paste(0, ((c + 2) * scale, (r + 2) * scale, (c + 3) * scale, (r + 3) * scale))
        self.preview_image = ImageTk.PhotoImage(image, master=self)
        self.preview_label.configure(image=self.preview_image)

    def generate(self):
        try:
            items = self._items()
            size = self._number(self.size_var, 'Rozmiar kodu')
            quiet = self._number(self.quiet_var, 'Margines', int)
            color = marks.parse_cmyk(self.color_var.get())
            if color is None:
                raise ValueError('Kolor: C/M/Y/K w %, np. 0/0/0/100')
            if self.separate_var.get():
                target = filedialog.askdirectory(parent=self, title='Folder na pliki z kodami')
            else:
                target = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf', filetypes=[('PDF', '*.pdf')],
                                                      initialfile=f'{self.default_name}.pdf')
            if not target:
                return
            written = codes.render_pdf(items, target, size, quiet, color, self.transparent_var.get(),
                                       self.caption_var.get(), self.separate_var.get())
        except (ValueError, OSError, RuntimeError) as exc:
            messagebox.showerror(self.kind, str(exc), parent=self)
            return
        self.preview()
        self.log(f'{self.kind}: {len(items)} kod(ów) → {len(written)} plik(ów)')
        for path in written[:20]:
            self.log('  ' + path)
        if len(written) > 20:
            self.log(f'  … (+{len(written) - 20})')


class QrPanel(_CodePanel):
    kind = codes.QR
    default_size = '25'
    default_quiet = '4'
    default_name = 'kody_QR'

    def __init__(self, parent, log):
        super().__init__(parent, log)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky='w')
        ttk.Label(top, text='Rodzaj treści:').pack(side='left')
        self.type_var = tk.StringVar(value=codes.QR_URL)
        box = ttk.Combobox(top, textvariable=self.type_var, values=codes.QR_TYPES, state='readonly', width=26)
        box.pack(side='left', padx=6)
        box.bind('<<ComboboxSelected>>', lambda e: self._show_type())
        self.body = ttk.Frame(self)
        self.body.grid(row=1, column=0, sticky='ew')
        self.body.columnconfigure(1, weight=1)
        self.field_vars: dict[str, tk.StringVar] = {}
        self._print_options(self, 2, ec=True)
        self._actions(self, 3)
        self._show_type()

    def _show_type(self):
        for child in self.body.winfo_children():
            child.destroy()
        kind = self.type_var.get()
        self.field_vars = {}
        if kind in codes.QR_MULTI:
            label = 'Adresy stron (jeden w wierszu; https:// dopisze się samo):' if kind == codes.QR_URL \
                else 'Tekst (jeden kod w wierszu):'
            self._text_box(self.body, 0, label)
            self._count()
            return
        for row, (key, label, required) in enumerate(codes.QR_FIELDS[kind]):
            ttk.Label(self.body, text=label + (' *' if required else '') + ':').grid(row=row, column=0, sticky='w',
                                                                                    pady=1, padx=(0, 8))
            var = tk.StringVar()
            ttk.Entry(self.body, textvariable=var, width=44).grid(row=row, column=1, sticky='ew', pady=1)
            self.field_vars[key] = var
        ttk.Label(self.body, text='* pole wymagane — jeden kod z tych danych', foreground=MUTED).grid(
            row=len(codes.QR_FIELDS[kind]), column=0, columnspan=2, sticky='w', pady=(2, 0))

    def values(self):
        kind = self.type_var.get()
        if kind == codes.QR_URL:
            return [codes.url_payload(line) for line in codes.text_lines(self.text.get('1.0', 'end'))]
        if kind == codes.QR_TEXT:
            return codes.text_lines(self.text.get('1.0', 'end'))
        return [codes.qr_payload(kind, {k: v.get() for k, v in self.field_vars.items()})]


SERIAL_TEMPLATE = '[)>$12$SER {SER}$PNR 04HC-V3-03$$'   # domyślny wzór starego generatora (datamt.py)
SERIAL_PREFIX = '04HC-S'


class DataMatrixPanel(_CodePanel):
    kind = codes.DATAMATRIX
    default_size = '12'
    default_quiet = '2'
    default_name = 'kody_DataMatrix'

    def __init__(self, parent, log):
        super().__init__(parent, log)
        modes = ttk.Frame(self)
        modes.grid(row=0, column=0, sticky='w')
        self.mode_var = tk.StringVar(value='text')
        ttk.Radiobutton(modes, text='Zwykły (wpisany tekst albo plik .txt)', value='text', variable=self.mode_var,
                        command=self._show_mode).pack(side='left')
        ttk.Radiobutton(modes, text='Numery seryjne', value='serial', variable=self.mode_var,
                        command=self._show_mode).pack(side='left', padx=12)
        self.text_frame = ttk.Frame(self)
        self.text_frame.columnconfigure(0, weight=1)
        self._text_box(self.text_frame, 0, 'Treść (jeden kod w wierszu):')
        self._count()
        self.serial_frame = ttk.Frame(self)
        self.serial_vars = {}
        for row, (key, label, default, width) in enumerate((
                ('prefix', 'Prefiks produktu', SERIAL_PREFIX, 20),
                ('template', 'Wzór ({SER} = prefiks + numer)', SERIAL_TEMPLATE, 46),
                ('start', 'Od numeru', '1', 10), ('end', 'Do numeru', '100', 10), ('step', 'Krok', '1', 6),
                ('digits', 'Cyfr w numerze (0 = bez zer wiodących)', '0', 6))):
            ttk.Label(self.serial_frame, text=label + ':').grid(row=row, column=0, sticky='w', pady=1, padx=(0, 8))
            var = tk.StringVar(value=default)
            entry = ttk.Entry(self.serial_frame, textvariable=var, width=width)
            entry.grid(row=row, column=1, sticky='w', pady=1)
            var.trace_add('write', lambda *_: self._serial_sample())
            self.serial_vars[key] = var
        ttk.Label(self.serial_frame, text='We wzorze można użyć znaków sterujących {GS}, {RS}, {EOT}.',
                  foreground=MUTED).grid(row=6, column=0, columnspan=2, sticky='w', pady=(2, 0))
        self.sample_var = tk.StringVar()
        ttk.Label(self.serial_frame, textvariable=self.sample_var, foreground='#173f74', wraplength=600,
                  justify='left').grid(row=7, column=0, columnspan=2, sticky='w', pady=(2, 0))
        self._print_options(self, 2, square=True)
        self._actions(self, 3)
        self._show_mode()

    def _show_mode(self):
        serial = self.mode_var.get() == 'serial'
        (self.text_frame if serial else self.serial_frame).grid_remove()
        (self.serial_frame if serial else self.text_frame).grid(row=1, column=0, sticky='ew', pady=(4, 0))
        self.separate_var.set(serial)          # jak w starym generatorze: numer = osobny plik
        self._serial_sample()

    def _serial_args(self):
        v = self.serial_vars
        number = lambda key, label: self._number(v[key], label, int)
        return (v['template'].get(), v['prefix'].get().strip(), number('start', 'Od numeru'),
                number('end', 'Do numeru'), number('step', 'Krok'), number('digits', 'Cyfr w numerze'))

    def _serial_sample(self):
        try:
            values = codes.serial_values(*self._serial_args())
        except ValueError as exc:
            self.sample_var.set(f'⚠ {exc}')
            return
        show = lambda s: s.replace('\x1d', '<GS>').replace('\x1e', '<RS>').replace('\x04', '<EOT>')
        last = f'  …  ostatni: {show(values[-1])}' if len(values) > 1 else ''
        self.sample_var.set(f'Kodów: {len(values)}.  Pierwszy: {show(values[0])}{last}')

    def values(self):
        if self.mode_var.get() == 'serial':
            return codes.serial_values(*self._serial_args())
        return [codes.with_controls(line) for line in codes.text_lines(self.text.get('1.0', 'end'))]


class EanPanel(ttk.Frame):
    """EAN-13 / EAN-8: kody wpisane albo z pliku .txt (barcodes.py — jak dotąd, z cyframi pod kreskami)."""

    def __init__(self, parent, log):
        super().__init__(parent)
        self.log = log
        self.columnconfigure(0, weight=1)
        self.kind_var = tk.StringVar(value='EAN13')
        kinds = ttk.Frame(self)
        kinds.grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(kinds, text='EAN-13 (12 lub 13 cyfr)', value='EAN13', variable=self.kind_var).pack(side='left')
        ttk.Radiobutton(kinds, text='EAN-8 (7 lub 8 cyfr)', value='EAN8', variable=self.kind_var).pack(side='left',
                                                                                                    padx=12)
        _CodePanel._text_box(self, self, 1, 'Kody (jeden w wierszu; cyfra kontrolna dopisze się sama):')
        _CodePanel._count(self)
        ttk.Button(self, text='Generuj PDF…', style='Accent.TButton', command=self.generate).grid(
            row=2, column=0, sticky='w', pady=(8, 0))

    _count = _CodePanel._count
    _load_txt = _CodePanel._load_txt

    def generate(self):
        try:
            found, bad = barcodes.read_codes(self.text.get('1.0', 'end'), self.kind_var.get())
            if not found:
                raise ValueError('Brak poprawnych kodów' + (f' (błędne wiersze: {len(bad)})' if bad else ''))
            target = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf', filetypes=[('PDF', '*.pdf')],
                                                  initialfile=f'kody_{self.kind_var.get()}.pdf')
            if not target:
                return
            barcodes.export_pdf(found, target)
        except (ValueError, OSError) as exc:
            messagebox.showerror('EAN', str(exc), parent=self)
            return
        self.log(f'EAN: zapisano {len(found)} kod(ów) → {target}')
        for line, message in bad:
            self.log(f'  pominięto wiersz {line}: {message}')


PANELS = {'qr': QrPanel, 'datamatrix': DataMatrixPanel, 'ean': EanPanel}
