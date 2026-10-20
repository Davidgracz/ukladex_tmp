# Przeniesienie pracy na inny komputer (Claude Code + REA + GitHub)

Stan na 2026-10-20. Repozytorium robocze: **https://github.com/Davidgracz/ukladex_tmp** (gałąź `main`).

## 1. Co trzeba zainstalować

| Program | Po co | Sprawdzenie |
|---|---|---|
| Git for Windows | repozytorium, Git Bash | `git --version` |
| GitHub CLI (`gh`) | logowanie, PR-y, scalanie | `gh --version` |
| Python 3.12 (3.11 i 3.13 też działają — CI) | aplikacja i testy | `py -3.12 --version` |
| Node.js 24 LTS (z npm) | uruchamia serwer REA przez `npx` | `node -v`, `npx -v` |
| Aplikacja Claude (desktop, zakładka Code) albo Claude Code CLI | praca z agentem | zaloguj się tym samym kontem |

Ghidra **nie jest potrzebna** — oryginał to zaciemniony program .NET; korzystamy wyłącznie z odczytu zasobów (teksty okien)
i metadanych wywołań bibliotek (REA `inspect_managed_artifact`, `inspect_managed_members` z `type_names`).

## 2. Kopia oryginału do analizy

Skopiuj folder z instalacją Impozycjonera 4 (`Impozycjoner.exe`, `pl-PL\Impozycjoner.resources.dll`, `Base.dat`) na nowy komputer,
najlepiej pod tę samą ścieżkę **`G:\ukladex`** (inna ścieżka też jest dobra — podaj ją agentowi).
**Nie wrzucaj tych plików do repozytorium** (repo jest publiczne; zasada czystej implementacji). Program nie musi być
zainstalowany ani aktywny — REA i skrypt czytają pliki statycznie.

## 3. Polecenia (PowerShell albo Git Bash)

```bash
gh auth login
gh auth setup-git
git config --global user.name "Dawid"
git config --global user.email "dawidgracz2001@gmail.com"
git clone https://github.com/Davidgracz/ukladex_tmp.git
cd ukladex_tmp
BOOTSTRAP_WINDOWS.bat
.venv\Scripts\python.exe -m pip install pytest
.venv\Scripts\python.exe -m pytest -q
```

Oczekiwany wynik testów: wszystkie zaliczone (stan przeniesienia: 327). `START_WINDOWS.bat` uruchamia program.

REA (serwer MCP dla Claude Code) — najpierw plan bez zmian, potem zapis konfiguracji:

```bash
npx -y rea-agents@6.7.0 doctor --client claude_code --json
npx -y rea-agents@6.7.0 setup --client claude_code --dry-run --json
npx -y rea-agents@6.7.0 setup --client claude_code --yes
```

Setup dopisuje serwer `rea` do `%USERPROFILE%\.claude.json` (polecenie `npx -y rea-agents@6.7.0 mcp`) i instaluje skill
`reverse-engineer-anything`. **Bez** `--install-hopper` (niepotrzebny). Po setupie zamknij i otwórz Claude (restart sesji),
a w nowej sesji poproś agenta o sprawdzenie, czy narzędzia `rea` są dostępne.

Teksty okien oryginału do folderu poza repozytorium (pomocnicze, gdy agent bada kolejną funkcję):

```bash
.venv\Scripts\python.exe -I scripts\imp4_resources.py "G:\ukladex\Impozycjoner.exe" --out C:\imp4_texty --grep "Znaczniki_Falcowanie"
```

## 4. Pierwsza wiadomość do agenta na nowym komputerze

> Pracujemy w repozytorium ukladex_tmp (folder: <ścieżka klonu>). Przeczytaj docs/PRZENIESIENIE.md i
> docs/imp4-wersja-finalna.md. Oryginał do analizy REA jest w G:\ukladex. Sprawdź, czy działają narzędzia rea i gh,
> uruchom testy i robimy dalej na tych samych zasadach.

## 5. Zasady pracy (ustalone w tej sesji)

1. **REA tylko statycznie**: teksty okien, podpowiedzi i komunikaty z zasobów (E1) oraz metadane wywołań bibliotek PDF;
   nie obchodzimy zaciemnienia, nie ruszamy licencji, nie kopiujemy tekstów, grafik ani plików oryginału do repo.
2. Tam, gdzie teksty nie mówią wszystkiego, decyzja jest **hipotezą H-nn** zapisaną w `docs/imp4-wersja-finalna.md` §6.
3. **Zgodność wstecz**: nowe pola `.psimp` są opcjonalne, domyślne wartości dają dotychczasowy wynik (test starego projektu;
   przy zmianach rysowania — porównanie strumieni PDF przykładowych projektów ze starym `main`).
4. Brak cichych pominięć: gdy czegoś nie da się zrobić (wycinka przy nieparzystej liczbie kolumn, opis/pasek bez miejsca) —
   uwaga w preflight i na pasku stanu.
5. Logika poza UI (`marks.py`, `pageops.py`, `engine.py`, …), testy jednostkowe + test z PDF, test dymny okna (zrzuty tylko okna
   programu).
6. Każdy etap: gałąź → commit (temat po angielsku, tryb rozkazujący) → push → PR do `ukladex_tmp/main` → scalenie po zielonych testach.

## 6. Stan funkcji (szczegóły: `docs/imp4-wersja-finalna.md`, `CHANGELOG.md`)

Zrobione (PR #1–#3 w `ukladex_tmp` scalone): interfejs w stylu Imp4, programy dodatkowe (podział, łączenie, wydzielanie, obrót,
powielanie, tasowanie, EAN-13/8, dodaj spady, skaluj strony), tryby „Wykonaj impozycję”, ustawienia pliku wynikowego, menu
tabeli stron, skalowanie „Wypełnij ze spadem” + przycinanie białych marginesów (A4 → A6 + 1,5 mm), znaczniki: cięcia (pełne okno
netto), wycinka, docięcie TrimBox, brutto, pasery, opis arkusza, pasek kontroli koloru.

Następne kroki (kolejność proponowana):
1. Próbny wydruk i cięcie na gilotynie znaczników narożnych i środkowych (H-34, H-35) — korekta wg wydruku.
2. Znaczniki: pasery w polu brutto (S), własne znaczniki z PDF (U), falcowanie (F), Uchida (C), sygnatura (G), redukcja (R).
3. Rozmiar wynikowego PDF (papier / pole zadruku / płyta, chwyt), wakaty w tabeli stron, CODE128 i QR.

Inne repozytoria z tej sesji (otwarte PR-y, starsza linia): `Davidgracz/ukladex` PR #2, `Davidgracz/impozycjoner` PR #1–#3.
Cała ich treść jest już w `ukladex_tmp`.
