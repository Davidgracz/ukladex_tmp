"""Okno aktualizacji ImpoCraft: sprawdzanie w tle przy starcie, „Sprawdź aktualizacje”, pobranie i instalacja.

Logika (wersje, adresy, suma SHA-256, stan) jest w updater.py; tu tylko interfejs i wątki.
"""
from __future__ import annotations

import tempfile
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

import app_info
import updater


class UpdateChecker:
    """Sprawdza aktualizacje w wątku tła i pokazuje okno w wątku interfejsu (root.after)."""

    def __init__(self, root: tk.Tk, status: tk.StringVar | None = None):
        self.root = root
        self.status = status
        self.busy = False

    def auto(self):
        state = updater.load_state()
        if updater.install_mode() != updater.MODE_SOURCE and updater.should_auto_check(state):
            self._start(manual=False)

    def manual(self):
        self._start(manual=True)

    def _start(self, manual: bool):
        if self.busy:
            return
        self.busy = True
        if manual and self.status:
            self.status.set('Sprawdzanie aktualizacji…')
        threading.Thread(target=self._work, args=(manual,), daemon=True).start()

    def _work(self, manual: bool):
        try:
            info, error = updater.check(), None
        except Exception as exc:  # brak sieci, limit API, zła odpowiedź
            info, error = None, exc
        self.root.after(0, lambda: self._done(info, error, manual))

    def _done(self, info, error, manual: bool):
        self.busy = False
        state = updater.load_state()
        if error is None:
            state['last_check'] = time.time()
            try:
                updater.save_state(state)
            except OSError:
                pass
        if self.status:
            self.status.set('' if info is None else f'Dostępna wersja {info.version}')
        if error is not None:
            if manual:
                messagebox.showerror('Aktualizacje', f'Nie udało się sprawdzić aktualizacji:\n{error}', parent=self.root)
            return
        if updater.worth_showing(info, state, manual):
            UpdateDialog(self.root, info)
        elif manual:
            messagebox.showinfo('Aktualizacje', f'Masz najnowszą wersję ({app_info.VERSION}).', parent=self.root)


class UpdateDialog(tk.Toplevel):
    def __init__(self, root: tk.Tk, info: updater.UpdateInfo):
        super().__init__(root)
        self.root, self.info = root, info
        self.mode = updater.install_mode()
        self.title('Aktualizacja ImpoCraft')
        self.transient(root)
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'Dostępna nowa wersja: {info.version}', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=f'Twoja wersja: {app_info.VERSION}').pack(anchor='w', pady=(2, 8))
        notes = tk.Text(frame, width=72, height=12, wrap='word', relief='solid', borderwidth=1)
        notes.insert('1.0', info.notes or '(brak opisu zmian)')
        notes.configure(state='disabled')
        notes.pack(fill='both')
        if self.mode != updater.MODE_INSTALLED:
            hint = ('Wersja przenośna: pobierz nowy ZIP ze strony wydania i podmień folder na pendrivie.'
                    if self.mode == updater.MODE_PORTABLE else 'Uruchomienie z kodu: zaktualizuj repozytorium (git pull).')
            ttk.Label(frame, text=hint, wraplength=520).pack(anchor='w', pady=(8, 0))
        self.auto_var = tk.BooleanVar(value=updater.load_state()['auto_check'])
        ttk.Checkbutton(frame, text='Sprawdzaj aktualizacje przy uruchomieniu', variable=self.auto_var,
                        command=self._save_auto).pack(anchor='w', pady=(8, 0))
        self.progress_text = tk.StringVar()
        ttk.Label(frame, textvariable=self.progress_text).pack(anchor='w')
        self.bar = ttk.Progressbar(frame, length=520, mode='determinate')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=(10, 0))
        if self.mode == updater.MODE_INSTALLED:
            self.install_button = ttk.Button(buttons, text='Zaktualizuj teraz', command=self._install)
            self.install_button.pack(side='left')
        ttk.Button(buttons, text='Strona wydania', command=lambda: webbrowser.open(info.page_url)).pack(side='left', padx=6)
        ttk.Button(buttons, text='Pomiń tę wersję', command=self._skip).pack(side='right')
        ttk.Button(buttons, text='Później', command=self.destroy).pack(side='right', padx=6)
        self.grab_set()

    def _save_auto(self):
        state = updater.load_state()
        state['auto_check'] = bool(self.auto_var.get())
        updater.save_state(state)

    def _skip(self):
        state = updater.load_state()
        state['skipped'] = self.info.version
        updater.save_state(state)
        self.destroy()

    def _install(self):
        if not messagebox.askyesno('Aktualizacja', 'ImpoCraft zostanie zamknięty i zaktualizowany, a potem uruchomi się '
                                   'ponownie.\nNiezapisane zmiany w projekcie przepadną. Kontynuować?', parent=self):
            return
        self.install_button.configure(state='disabled')
        self.bar.pack(anchor='w', pady=(4, 0))
        self.progress_text.set('Pobieranie…')
        folder = Path(tempfile.gettempdir()) / f'{app_info.APP_NAME}-aktualizacja'
        threading.Thread(target=self._download, args=(folder,), daemon=True).start()

    def _download(self, folder: Path):
        def progress(done, total):
            self.root.after(0, lambda: self._progress(done, total))
        try:
            path, error = updater.download(self.info, folder, progress=progress), None
        except Exception as exc:
            path, error = None, exc
        self.root.after(0, lambda: self._downloaded(path, error))

    def _progress(self, done, total):
        if total:
            self.bar.configure(maximum=total, value=done)
        self.progress_text.set(f'Pobieranie… {done / 1048576:.1f} MB' + (f' z {total / 1048576:.1f} MB' if total else ''))

    def _downloaded(self, path, error):
        if error is not None:
            self.progress_text.set('')
            self.install_button.configure(state='normal')
            messagebox.showerror('Aktualizacja', f'Nie udało się pobrać aktualizacji:\n{error}', parent=self)
            return
        try:
            updater.launch_installer(path)
        except OSError as exc:
            messagebox.showerror('Aktualizacja', f'Nie udało się uruchomić instalatora:\n{exc}', parent=self)
            self.install_button.configure(state='normal')
            return
        self.root.destroy()
