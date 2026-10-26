# Changelog

## 0.5.9

Nowości w ImpoCraft 0.5.9:
- **Odwracanie przez markę** (wstęga „Montaż akcydensów” → „Rodzaj arkuszy” → „Przez markę ▾”):
  dwustronny pełny i niepełny przez markę boczną (MB) i czołową (MC). Przy niepełnym przody i tyły są na jednej
  płycie — liczba kolumn (MB) albo wierszy (MC) musi być parzysta.
- **Rozmiar wynikowego PDF** („Ustawienia…”): papier, pole zadruku, papier + chwyt, pole zadruku + chwyt albo
  płyta; margines „na łapki” przy krawędzi chwytaków. Domyślnie bez zmian (PDF = arkusz).

Details (English):

- Output PDF size as in the original's „Rozmiar wynikowego pdfa”: paper (default, unchanged), print area, paper +
  grip, print area + grip, plate (width, height, grip, reduce by pt); technical margin („na łapki”) at the gripper
  edge; TrimBox marks the paper on larger pages. Settings in „Ustawienia…”, page size on the status bar,
  stored in the project. H-54.
- Work-and-turn / work-and-tumble as in the original's sheet kinds: full duplex by side lay (MB, back mirrored
  horizontally) or gripper edge (MC, back mirrored vertically and rotated 180°), and half-sheet („niepełny”)
  MB / MC with fronts and backs on one plate (even columns / rows required, equal bleeds on the turn axis,
  explicit errors otherwise). New „Przez markę” ribbon button with a menu; ribbon width unchanged. H-55.

## 0.5.8

Nowości i poprawki w ImpoCraft 0.5.8:
- **Ważna poprawka:** strona obrócona w samym pliku PDF (/Rotate) trafiała na arkusz odwrócona o 180° względem
  podglądu w czytniku PDF. Teraz wygląda tak jak w czytniku. Strony bez takiego obrotu — bez zmian.
- **Spady L / P / G / D** (wstęga „Montaż akcydensów” → „Spady (dla obrotu 0°)”): wyłącz „=” i wpisz osobno spad
  lewy, prawy, górny i dolny; spady obracają się razem z użytkiem.
- Węższa grupa spadów na wstędze — mieści się w mniejszym oknie.

Details (English):

- Separate bleeds L / P / G / D „for rotation 0°” as in the original: „=” switch and four fields in the ribbon
  group „Spady (dla obrotu 0°)”; bleeds rotate with the use; grid cells, gross rectangles, cut marks, artwork
  clipping, single-page export and preflight use the bleed of each edge; preflight note for duplex when the
  bleeds on the flip axis differ. Equal bleeds (default) give exactly the previous output. H-53.
- Fix: a PDF page with /Rotate was placed on the sheet rotated by 180° compared with the PDF viewer
  (show_pdf_page rotates counter-clockwise, /Rotate clockwise). Pages without /Rotate are unchanged.
- The bleed ribbon group is narrower than before (the ribbon fits narrower windows again).
- Self-test retries the transient Tk start error seen during builds; the test shows the full report.

## 0.5.7

Nowości w ImpoCraft 0.5.7 — generatory kodów (Programy dodatkowe → Kody):
- **Kody QR**: strona WWW, wizytówka (vCard / MeCard), e-mail, telefon, SMS, Wi-Fi, lokalizacja, wydarzenie,
  przelew (PL) albo dowolny tekst; korekcja L / M / Q / H.
- **Kody Data Matrix**: zwykły tekst oraz **numery seryjne** (wzór z {SER}, prefiks, od–do, krok, zera wiodące).
- **Kody EAN-13 / EAN-8**: teraz także z wpisywania.
- Treść można wpisać albo wczytać z pliku .txt; kody wektorowe w kolorze CMYK, jeden PDF albo plik na każdy kod.

Details (English):

- Code generators in „Programy dodatkowe → Kody”: QR with content types (website, vCard and MeCard business
  cards, e-mail, phone, SMS, Wi-Fi, location, calendar event, Polish bank transfer, free text), Data Matrix (typed
  text or .txt, and serial numbers ported from the user's old datamt.py generator: {SER} template, prefix,
  from–to, step, zero padding, {GS}/{RS}/{EOT}) and EAN-13/EAN-8 with typed input. Text can be typed or loaded
  from .txt. Vector output (CMYK), size, quiet zone, QR error correction L/M/Q/H, transparent background,
  caption, one PDF or a file per code, preview. New dependency: zxing-cpp (Apache-2.0), bundled in the EXE.
  H-52.
- Tests: Tk windows in tests are created with a retry on the transient „Can't find a usable tk.tcl” error seen
  during builds (the file exists; most likely a short antivirus lock), panel tests share one Tk root.

## 0.5.6

Nowości w ImpoCraft 0.5.6:
- **Nowe menu „Programy dodatkowe”**: kafelki z ikonami w kategoriach (dziel i łącz, wybierz i usuń strony,
  kolejność i obrót, format / spady / cięcie, kody) oraz nagłówek z opisem wybranego narzędzia.
- **Usuń wybrane strony**: nowy plik PDF bez wskazanych stron (np. 2, 5-7, 10-); plik źródłowy bez zmian.

Details (English):

- „Programy dodatkowe” redesigned: tiles with drawn icons in categories (split and merge, choose and delete pages,
  order and rotation, format/bleed/cutting, codes), two columns; the selected tool gets a header with a large
  icon, name and description.
- New tool „Usuń wybrane strony”: a new PDF without the given pages (same order, vector, source untouched;
  deleting every page is refused). H-51.

## 0.5.5

Nowości i poprawki w ImpoCraft 0.5.5:
- **Ramka użytku (A)** na pasku znaczników: cienka ramka dookoła każdego użytku, na krawędzi netto i/lub brutto,
  grubość i kolor do wyboru (prawy przycisk → parametry).
- **Poprawka:** wraca przycisk „Sprawdź aktualizacje” na dolnym pasku (znikał, bo okno było za wysokie).
  Przyciski znaczników są teraz w dwóch kolumnach, a okno mieści się także na laptopie 1366 × 768.

Details (English):

- Fix: the bottom bar with „Sprawdź aktualizacje” disappeared — the marks bar had grown to 11 buttons in one column,
  the window needed ~1150 px and the bottom bar was squeezed to 1 px. The bottom bar is now packed before the
  middle of the window and the marks are laid out in two columns (required height ~830 px). Regression test added.

- Use frame (A) on the marks bar, requested by the user: a thin frame around every placed use, on the net
  (trim) edge and/or the gross (bleed) edge, width [pt] and colour (black / K 100 % / registration); default
  0.25 pt K 100 %, off by default. H-50.

## 0.5.4

Nowości w ImpoCraft 0.5.4:
- **Autowypełnianie arkusza** (wstęga „Montaż akcydensów” → „Autowypełnianie…”): narożnik startowy LG / PG / LD / PD,
  wierszami albo kolumnami, strony kolejno albo w stosie (pod cięcie stosu), wszystkie / nieparzyste / parzyste,
  NPNP albo NNNPPP, powtórzenia każdej strony.
- **Łączenie plików wynikowych** („Ustawienia…”): jeden plik, osobne pliki arkuszy, każda strona osobno
  i ich połączenia (7 wariantów).

Details (English):

- Sheet autofill from the original's „Autowypełnianie arkusza” window (ribbon „Montaż akcydensów” →
  „Autowypełnianie…”): start corner LG / PG / LD / PD, rows or columns, pages in sequence or in a stack
  (cut-and-stack), all / odd / even pages, even pages after each odd one or after all odd ones, repeats of each
  page. Single- and double-sided imposition (pairs stay together); defaults reproduce the previous layout
  (example exports unchanged). Stored in the project. H-49.

- Output file splitting from the original's „Łączenie plików wynikowych” (seven variants: one file, sheets,
  each page separately and their combinations) in „Ustawienia — plik wynikowy”, stored in the project (old
  projects: one file). Sheet files `<name>--arkusz-NN.pdf` hold front and back; page files `<name>--NN.pdf`.
  The imposition is rendered once; no temporary file is left behind. H-48.

## 0.5.3

Nowości w ImpoCraft 0.5.3:
- **Tabela stron — wiersze** (prawy przycisk → Wiersze): wakaty przed / po / tutaj, usuń wakaty, wstaw plik przed / po,
  zamień wiersz na stronę innego pliku albo inną stronę z pliku, kopiuj / wytnij / wklej (Ctrl+C / X / V);
  zaznacz wiersze ujęte / nieujęte / takie same.
- **Rozetnij strony PDF** (Programy dodatkowe): kolumny × wiersze, zakładki do sklejania ze znacznikiem i opisem.
- **Rozetnij rozkładówki** (Programy dodatkowe): rozkładówki na pojedyncze strony z TrimBox i spadami.
- **Pasery w polu brutto (S)** na pasku znaczników: V1, V2, H1, H2, grubość, kolor.
- **Nazwa pliku po impozycji**: podpowiadana jako `nazwa_oryginału_93x53mm_impozycja.pdf` w folderze oryginału.

Details (English):

- Suggested output file name (ImpoCraft's own rule, requested by the user — not from the original):
  `<source file name>_<net width>x<net height>mm_impozycja.pdf` (single-page export: `…_strony.pdf`), e.g.
  `wizytowki_93x53mm_impozycja.pdf`, in the folder of the first source file; decimal comma (`105x148,5mm`),
  forbidden characters replaced by `_`. The „--IMPOZYCJONER” phrase option still works on top of it.

- Extra programs „Rozetnij strony PDF” (columns × rows, page range, overlap tabs left/right and top/bottom,
  tab marks with length, width and CMYK colour, optional tab labels) and „Rozetnij rozkładówki” (single page
  size given or read from the first page TrimBox, optional splitting of the first/last page, TrimBox and bleed
  on the new pages, spine bleed from the neighbouring page). Vector output; rotated source pages are cut in
  their visible orientation. H-46, H-47.

- Page table row operations from the original's menu (submenu „Wiersze”): insert vacancy before / after /
  here, remove all vacancies, insert file before / after, replace a row with a page of another file or of the
  same file, copy / cut / paste before / after (Ctrl+C / X / V), select rows included / excluded / the same.
  Projects store an optional row order per item (`pages`, numbers from 1, `null` = vacancy); old projects load
  unchanged. Inserting into the middle of an item splits it with the same settings; refused for copies > 1.
  Vacancies are empty slots (blank page in duplex pairs and single-page export, ignored in economic mode).
  H-45.

- Gross-field registration marks (S), modelled on the original's window: V1, V2, H1, H2 [mm], width [pt],
  colour (black / K 100 % / registration). Crosses at the four corners of the gross grid (H-44, OQ-18);
  preflight note when they leave the sheet; shortcut S. Off by default: example exports unchanged.

## 0.5.2

Nowości w ImpoCraft 0.5.2:
- **Znaczniki własne z plików PDF (U)** — pliki U1L/U1R (strony nieparzyste) i U2L/U2R (parzyste), położenie H i V,
  osobne włączniki; prawy przycisk na „Znaczniki własne (U)” → parametry i wczytanie plików.
- **Kadruj i zapisz do pliku** — w oknie korekty obszaru netto i w menu tabeli stron: nowy PDF przycięty do netto
  albo do brutto (netto + 3 mm spadu), wektorowo, z korektami z projektu; plik źródłowy bez zmian.

Details (English):

- „Kadruj do obszaru netto / brutto (netto + 3 mm spadu) i zapisz do pliku” in the net-size correction window and in
  the page table menu: writes a new PDF where every page is cut to its TrimBox (or TrimBox + 3 mm), as vectors, with
  the project's page corrections and resizes applied; TrimBox/BleedBox set on the new pages; missing bleed in the
  file stays white and is reported; the source file is never overwritten; optionally the project row is switched to
  the new file. H-43.

- Custom marks from PDF files (U), modelled on the original's custom-marks window: files U1L/U1R (odd pages of the
  output PDF) and U2L/U2R (even pages), H and V in mm for odd and even pages (H from the left/right sheet edge, V from
  the bottom edge, both to the mark's top corner), a main switch and a draw switch per mark; a missing file means the
  mark is not drawn (preflight lists it, also marks sticking out of the sheet). Marks keep the size of their PDF page
  and are placed as vectors. Default folder `znaczniki` in the user data (or any folder set in the project); the
  parameters window (right click on „Znaczniki własne (U)”, shortcut U) loads a PDF under the right name and opens the
  folder. Off by default: exports of all example projects are byte-identical in content.
- Previews pass the real sheet number to `render_side`, so custom marks show the odd/even variant of the sheet
  being viewed (other odd/even marks still use the preview page number — unchanged).

## 0.5.1

First public release of **ImpoCraft** (author Dawid Gracz), the continuation of Impozycjoner Studio.

- Automatic updates: at start (at most every 6 hours) and with „Sprawdź aktualizacje” the program checks GitHub
  Releases of Davidgracz/ukladex_tmp. When a newer version exists it shows the changes and offers „Zaktualizuj teraz”
  (installed version: downloads the installer, verifies its SHA-256, installs silently and restarts), „Później”,
  „Pomiń tę wersję” and turning automatic checks off. The portable version only links to the release page.
- Only URLs under github.com/Davidgracz/ukladex_tmp/releases/download/ are downloaded; drafts and pre-releases are
  ignored; a corrupted download is deleted.
- `scripts/publish_release.py` publishes a release (installer, its `.sha256`, portable ZIP, notes from this file).
- Windows installer, program rename and EXE version information — see below.

## Unreleased (included in 0.5.1)

- Rename the program to **ImpoCraft** 0.5.0 (author Dawid Gracz): window title, PDF metadata, EXE name. Name, version
  and author live in `app_info.py`. User data moves to `%APPDATA%\ImpoCraft`; data from the old
  `Impozycjoner Studio` folder is copied once on first start (the old folder is left untouched). `.psimp` unchanged.
- Windows installer (`BUILD_INSTALLER_WINDOWS.bat`, Inno Setup 6, `packaging/ImpoCraft.iss`): Program Files or
  per-user install, Start menu/desktop shortcuts, `.psimp` association, uninstaller, publisher „Dawid Gracz”.
  EXE version resource (company, product, copyright) generated by `scripts/make_version_info.py`.
- Optional Authenticode signing of the EXE and installer (`scripts/sign_files.py`, signtool, SHA-256 + RFC 3161
  timestamp) when a code-signing certificate is supplied through environment variables; skipped otherwise.
- Opening a `.psimp` project passed on the command line (double click after installation).

- Resize selected pages (page table → right click „Zmień rozmiar zaznaczonych stron (skaluj)…”), as observed in a
  running Impozycjoner (user screenshots: editing Width/Height of table rows scales A4 and A6 pages to 108 × 151):
  width and height independently (stretch) or with cropping (keep proportions), width only, height only, keep
  orientation, optional bleed from artwork outside the TrimBox. Pages are rebuilt as vectors in memory when PDFs are
  opened; the file on disk is unchanged; new sizes are shown with * in the table; stored per file (`page_sizes`,
  optional). Tests: `tests/test_page_resize.py`.

- Page size correction in the page table (right click → „Koryguj rozmiar strony (obszar netto)…”), modelled on the
  Imp4 window „Korekta położenia i rozmiaru obszaru netto” (UI texts + REA call metadata): page preview with a
  movable net frame, width/height and position in mm, scope this page / all / odd / even, in the file or the whole
  table, only pages of the same size as the corrected one (others listed), restore from file, set the use size.
  Stored per file in the project (`page_boxes`, optional); the TrimBox is applied in memory when PDFs are opened,
  so imposition, single pages, preflight and preview use it while the PDF on disk stays unchanged. Corrected sizes
  are marked with * in the table. Tests: `tests/test_page_boxes.py`.

- Mixed page sizes in one PDF (A4/A3/A5/landscape/A6) scaled to A5 or A6: new option „obracaj strony do orientacji
  użytku” (Kadrowanie PDF) turns a landscape page on a portrait use (and vice versa) by 90° instead of shrinking it
  (Dopasuj) or cutting half of it off (Wypełnij). Also accepted in „Bez skalowania”, refused with „Kadruj 1:1”;
  preflight shows an OBROT note. Templates „Ulotka A6/A5 + 1,5 mm …” enable it (optional template field).
  Off by default — example projects export byte-identically. Tests: `tests/test_mixed_sizes.py`.

- Portable EXE for a USB stick: `BUILD_EXE_WINDOWS.bat` runs the tests first, builds `dist\Impozycjoner-Studio` with a
  generated icon (`scripts/make_icon.py`), adds `PORTABLE.txt`, a `dane` data folder and examples, checks the built
  EXE with `--self-test` (`selftest.py`, `scripts/check_exe.py`) and zips it; `jedenplik` also builds a single-file EXE.
  New `user_data.py`: with `PORTABLE.txt` next to the program, job templates and machine profiles are stored in `dane`
  next to it instead of `%APPDATA%`. Tests: `tests/test_portable.py`.

- Added `docs/PRZENIESIENIE.md` (setup on another computer: tools, GitHub, REA MCP, working rules, state, next steps) and
  `scripts/imp4_resources.py` (reads UI texts of the original from .NET resources into a folder outside the repository;
  refuses to write inside the repo). Test: `tests/test_imp4_resources_script.py`.

- Cut marks (guillotine, N) now follow the full Imp4 "net size marks" window: separate LP/GD lengths (GD=LP switch),
  colour (previous black / K 100 % / registration), all/odd/even output pages, first sheet only, corner marks
  LG/PG/LD/PD (clamped to half the use), net centre marks, and an option to keep marks off neighbouring uses.
  Geometry in `marks.py`. Default settings produce byte-identical drawing streams (checked on all example
  projects against the previous `main`). Tests: `tests/test_cut_marks.py`.

- Colour control strip (K) as in the final Imp4: 12 cubes K1–K12 (CMYK %, at least one coloured), cube size, zones,
  offset, top / bottom / horizontal gutter, full print-area length or minus X, centred or from the left, or a strip
  taken from a PDF file. Drawn in DeviceCMYK; a note when it does not fit; the slug moves above the strip.
  Parameters dialog with a 12-colour editor and swatches. Optional `.psimp` fields. Tests: `tests/test_color_strip.py`.

- Marks from the final Imp4 (UI texts read with REA): gross-size marks (B: LP/GD length, width, all/odd/even pages,
  first sheet only), registration marks (P: own designs 1/2, diameter, count per long/short side, automatic or own
  offset, corner/edge placement, 100 % CMYK) and imposition slug (O: output file name, "Arkusz N • Strona M" with
  arabic/roman numbering, print area, net/gross/bleed, date and time, extra text; 10/12/14 pt Arial/Courier; top
  and/or left edge; a preflight/status note when it does not fit). Parameters dialog supports choices and text.
  New `.psimp` fields are optional; defaults keep the previous output. Tests: `tests/test_marks_gross_reg_slug.py`.

- Scaling and cropping: new fit mode „Wypełnij ze spadem” (artwork covers net + bleed, e.g. A4 → A6 + 1.5 mm, overflow
  cropped, no white bleed) and „przytnij białe marginesy źródła” (detects a white frame around the artwork and uses
  the content area; `whitecrop.py`). Works in imposition, single-page export and preflight.
- „Programy dodatkowe”: „Dodaj spady” as in Imp4 (per edge: added bleed, strip width, strip distance from the
  MediaBox edge; stretched strips over or under the page) and „Skaluj strony” (mm or %, proportional, TrimBox or
  MediaBox, optional centring page).
- Built-in job template „Ulotka A6 + 1,5 mm z A4 (bez białych marginesów) — SRA3”; job templates accept the optional
  `white_trim` field (older templates still load).
- `docs/imp4-wersja-finalna.md` §5a: how the final Imp4 scales, crops and adds bleed (UI texts + REA call metadata).

- Marks from the final Imp4: centre cut gutter („Wycinka”, W) — vertical/horizontal width, applied only for an even
  number of columns/rows (otherwise a preflight and status-bar note), axis mark with length or across the print area;
  extra TrimBox hair crop („Docięcie TrimBox”, T) — left on even pages, right on odd; cut-mark offset, length and
  width (N); „Wyłącz wszystkie”. Click toggles, right click opens parameters. Rules in `marks.py`, tests in
  `tests/test_marks.py`. New `.psimp` settings are optional; defaults give the previous output.

- Mapped the final Impozycjoner 4.0.4.0 from its UI texts (REA static analysis, nothing executed) and compared it
  with Studio: `docs/imp4-wersja-finalna.md`.
- Added the „Programy dodatkowe” tab (`tools_ui.py`, `pdftools.py`, `pageops.py`): split into single pages
  (`--XX`), merge, extract (range / each page / remainder / even-odd / cover and body / N pages per file), rotate,
  duplicate, shuffle pages or leaves — vector, input never overwritten. Page ranges use the `-3, 6, 9-11, 15-` syntax.
- Added EAN-13 / EAN-8 generator from a text file (`barcodes.py`), vector bars with GS1 check digit.
- „WYKONAJ IMPOZYCJĘ” can run all sheets, only the active sheet, or all but the active sheet (`engine.select_sides`).
- New „Ustawienia…” dialog: `--IMPOZYCJONER` phrase and PDF metadata (empty = file name); output names with
  forbidden characters or equal to an input name are refused (`naming.py`).
- Page table: multi-select and a right-click menu (select all/even/odd/invert, find first sheet with the page,
  use the page size as the use size, skip/restore pages, remove the file's rows, open in PDF reader)
  — logic in `table_actions.py`.
- Shortcuts as in Imp4: Ctrl+N new imposition, Ctrl+W load project, Shift+Ctrl+S save project as.
- A non-PDF or damaged input now gives a clear error instead of a PyMuPDF exception.
- Without the new options, export output, project format and the TAXI module are unchanged.
  New tests: `test_imp4_functions.py`, `test_pageops.py`, `test_pdftools.py`, `test_barcodes.py`.

- Reworked the main window to follow the Impozycjoner 4 layout: light theme, ribbon tabs (Montaż akcydensów / Kadrowanie PDF / Druk cyfrowy — recto/verso; simple sheet imposition only, no book tab — the Broszura mode is hidden from the UI but old projects still load and export) with captioned groups (Użytek, Tabela K×W, Spady, Odstępy i marginesy, Arkusz, Rodzaj arkuszy).
- "Rodzaj arkuszy" icon buttons replace the mode/flip combo boxes (single-sided, duplex long/short edge, economic, booklet).
- Page table with one row per PDF page (S, SPDF, Nazwa pliku, Szer., Wys., Nakład, Rola), coloured per file; clicking a use on the sheet selects its page.
- New symbolic preview ("Symbole"): coloured uses with page number:rotation and a bar on the page-head edge, drawn without rendering PDF content.
- Summary box (pages, sheets, uses per side, unused slots, gross/net), large WYKONAJ IMPOZYCJĘ button, sheet tabs (1, 2… / 1R, 1V) under the preview, vertical marks strip, printable-area readout.
- Engine, PDF output, project format and the TAXI module are unchanged. Added `ui_icons.py` and `tests/test_symbolic_preview.py`.

- Added job templates (`job_templates.py`): one-click presets for sheet, net size, bleed, gaps, mode, rotation, scaling and marks.
- Seven built-in starting points (business cards, A6/DL/A5 flyers on SRA3) plus user templates stored in `%APPDATA%\Impozycjoner Studio\job_templates.json`.
- Templates never carry per-file data (original size, crop offsets) or machine calibration; a template may only reference a machine profile by name.
- New "SZABLONY PRAC" section in the settings panel (load / save as / delete); built-in templates are read-only.
- Added `tests/test_job_templates.py`. The engine and PDF output are unchanged.

## 0.4.1 — 2026-10-14

- Reworked crop UI to source PDF → net dimensions → per-edge bleed → automatically derived gross size.
- Added practical net size presets for business cards, DL, A7 and ISO A-sizes.
- Auto-detected original PDF dimensions per selected source while preserving manual source validation for old projects.
- Added a real-PDF visual crop editor with draggable gross/net guides, 0.1-mm X/Y offsets and one-click reset.
- Stored independent crop offsets per source PDF in .psimp and validated source margins before printing.
- Unified manual crop offsets across sheet preview, vector export, single-page export and preflight.
- Added backwards-compatible auto_source/auto_gross settings and new regression/GUI checks.
- Kept regular-sheet geometry and the complete TAXI module unchanged.


## 0.4.0 — 2026-10-13

- Added single-sided economic gang-run mode for multiple PDFs with differing requested quantities.
- Combined each non-skipped page as its own artwork; exact quantity accounting and proportional per-sheet mixing.
- Minimum physical sheet count for one common gross/net size, no forced overproduction; deterministic placement.
- Added the production planning UI with sheet totals, unused slots, overproduction/shortages and UTF-8 Excel CSV reports.
- Export produces all physical sheet pages directly and saves a matching per-artwork/per-pattern CSV report.
- Added preflight and export blocking when manual changes alter ordered artwork quantities.
- Added a vector SRA3 sample, .psimp project, preview, CSV and integration/property-style tests.
- Preserved all existing imposition and TAXI generator functionality.


## 0.3.7 — 2026-10-13

- Added a printable two-page, vector-only duplex alignment sheet at the current physical sheet size.
- Added five cross/ruler targets on recto and corresponding ring targets on verso; follow flip direction and active machine offsets.
- Added a measurement calculator for front-face displacement with correct axis signs for landscape/portrait and long/short edge flipping.
- Applied measurement corrections incrementally to the current verso offset; operator can save the result as a printer profile.
- Added geometry, sign, vector PDF and profile regression tests; preserved all current imposition and TAXI functions.


## 0.3.6 — 2026-10-13

- Added 0.1-mm whole-side verso X/Y calibration after all per-slot manual edits and physical flip.
- Added per-machine calibration profiles (offsets and flip method), saved locally in a versioned JSON file outside the project.
- Persisted current duplex offsets in backward-compatible `.psimp` project settings.
- Unified calibrated placements for sheet editor, registration preview, preflight and vector PDF output, including crop marks.
- Added preflight checks for out-of-sheet calibrated back uses; reject invalid or non-0.1-mm offsets.
- Added two-sided demo PDFs, project, registration screenshot, GUI smoke check and regression tests.
- Kept source code and template files of the TAXI generator unchanged.


## 0.3.5 — 2026-10-13

- Added a real visual drag/drop sheet editor for source PDF pages, including empty grid positions.
- Added move-by-drag, arrow-key 0.1-mm nudging, exact X/Y inputs and independent 90-degree per-use rotation.
- Added drag-to-swap, reset-to-auto and clear operations, preserving independent recto and verso edits.
- Persisted artwork assignments, displacement and rotation in backward-compatible `.psimp` files.
- Unified edited geometry for preview and vector PDF output; visual page overlays remain preview-only.
- Added physical sheet-boundary checks and overlap warnings in editor and preflight.
- Kept the TAXI generator and all its template assets unchanged.
- Added regression tests for vector output, backward compatibility, save/load, duplex and 110x70 crop.


## 0.3.4 — 2026-10-13

- Added three explicit operator dimensions: original PDF, gross/with-bleed use, and final net trim.
- Made 1:1 cropping derive symmetric bleed from the gross-minus-net difference (default 1.5 mm/edge).
- Added source dimension verification and gross-fit preflight/export checks.
- Maintained project compatibility, existing scaling modes, manual recto/verso editing and page overlays.
- Kept TAXI generator source and assets unchanged.
- Added vector sample PDFs and production-focused integration tests.


## 0.3.3 — 2026-10-13

- Added centered 1:1 physical crop mode using distinct source PDF dimensions, finished trim size, and bleed.
- Preserved no-scaling exact-size mode and existing fit/fill modes.
- Added crop-mode size checks and preflight reporting.


## 0.3.2 — preview-only page overlays

- Added large semi-transparent per-slot page numbers in the raster preview only.
- Added Off / Page number / Filename + page number modes.
- Applies on recto and verso, including manually assigned cells and registration view.
- Final exported PDF is unchanged by these preview-only overlays.


## 0.3.1 — 2026-10-13

- Added manual sheet slot assignment, swapping, clearing and resetting on selected recto/verso sheet.
- Stored manual cell overrides in .psimp and applied them consistently during PDF preview and export.
- Added duplex registration overlay with appropriate flip-edge mirroring.
- Retained the TAXI generator unchanged.
- Added regression tests for overridden duplex export and project persistence.


## 0.2.8 — 2026-10-12

- Preserved proportional side-number scaling: the TAXI number is no longer stretched independently in X/Y.
- Centered the raster side number inside its target area after proportional fitting.

- Changed the TAXI generator output to one shared ZIP with all files stored flat, without per-number subfolders.
- Simplified the rear cut artwork to SVG-only output.
- Removed mirrored rear duplicates; each rear decal now contains one number above one SZCZECIN word.
- Locked rear decal geometry to operator rules: number height 55 mm, SZCZECIN width 120 mm.
- Kept side artwork as original 200 DPI TIFF templates while still changing only the taxi number.
- Updated the Windows UI texts, ZIP naming and production notes for the new TAXI workflow.
- Refreshed tests to validate flat ZIP output and the fixed SVG geometry.


## 0.2.5 — 2026-10-12

- Added a dedicated email-to-print labels tab with direct IMAP-over-SSL mail listing and read-only fetch.
- Added MIME plain-text/HTML extraction, category detection and PLN price parsing without inventing missing prices.
- Restored bakery 110x50 mm labels with prices (A4 landscape) and ice-cream 90x50 mm labels without prices (A4 portrait).
- Added editable label entries, per-item copies, category templates, and Unicode vector PDF export.
- Added optional local persistence of IMAP host, port, login and filter; never store password or email body.
- Added anonymized sample email, a production-style vector PDF example, and regression tests.


## 0.2.4 — 2026-10-12

- Added editable recto/verso roles for each input PDF and individual PDF pages (Normal, Front, Paired Back, Shared Back, Exclude).
- Added multi-select and number/range assignment (e.g. `1,3-8,22`) in a dedicated Windows dialog.
- Added common-back duplication for personalized fronts, even when a single PDF mixes fronts with one special shared-back page.
- Added explicit front-to-back pairing across separate input files, preserving front order and the chosen duplex flipping edge.
- Kept legacy sequential pairing for unchanged projects and stored assignments in backward-compatible `.psimp` project files.
- Added role validation in preflight so missing or extra backs, multiple different common backs, and non-duplex exports cannot silently misprint.
- Added a vector PDF demo and tests covering pairing, shared backs, skipping, project persistence and placement.


## 0.2.3 — 2026-10-12

- Detected mixed source page sizes in one PDF and warned about implicit enlargement or reduction to the selected target trim size.
- Consolidated low-resolution image findings by page to avoid repeating dozens of similar warnings.
- Reported effective DPI after scaling, retaining exact image instances, coordinates, pixel dimensions, and native DPI in the JSON report.
- Added regression tests for a 22-page document mixing A4/A6, grouped DPI warnings, and improved effective DPI after downscaling.

## 0.2.2 — 2026-10-12

- Added explicit vector-safe PDF resizing: Fit and Fill, with centered placement and controlled clipping.
- Added A6/A5/A4 target presets and scaling controls in the Windows GUI.
- Added standalone multipage output at the target trim size; source page order is preserved.
- Made preflight aware of scaling, crop warnings, output bleed and effective image DPI.
- Added tests for 22-page A4→A6 workflows, booklet/imposition scaling, cropped fill, shifted MediaBox and rotated pages.

## 0.2.1 — 2026-10-12

- Fixed false TRIMBOX preflight errors when a PDF has a non-zero MediaBox origin.
- Used consistent MuPDF geometry for MediaBox, TrimBox and BleedBox in PDF export.
- Fixed full-media CropBox setup for shifted MediaBox documents.
- Added regression tests covering offset media boxes, 22-page files and real invalid TrimBox rejection.

## 0.2.0 — 2026-10-12

- Added the Preflight PDF window and export gate, with TXT/JSON reports.
- Checks source dimensions against requested trim without silent rescaling.
- Detects insufficient physical bleed, potentially low-resolution images and some unembedded fonts.
- Improved vector PDF placement with asymmetric bleeds, intrinsic PDF rotation and rotated sheet slots (0/90/180/270 degrees).
- Uses the source MediaBox for placing available bleed even when the source CropBox is smaller.
- Added regression tests for rotated bleeds, dimensional mismatches and preflight reports.

**Caution:** Not a full PDF/X, CMYK/spot or ICC profile inspection. Verify a production proof and duplex orientation before running a print job.

## 0.1.0 — 2026-10-12

- First desktop preview of Impozycjoner Studio (Tkinter + PyMuPDF).
- Added PDF input jobs, imposition grid, basic duplex and booklet modes.
- Added vector PDF export, crop marks, `.psimp` projects and sample PDFs.
- Added Windows venv/pip bootstrap fix.
- Added engine tests, CI and GitHub project setup scripts.
