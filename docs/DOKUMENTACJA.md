# ImpoCraft — pełna dokumentacja

Wersja programu: **0.5.9** · Autor: **Dawid Gracz** · Repozytorium: https://github.com/Davidgracz/ukladex_tmp

Ten dokument opisuje, **co robi każda część programu i jak działa** — od obsługi okna po budowę kodu, testy
i wydawanie nowych wersji. Szczegółowe porównanie z Impozycjonerem 4 (funkcja po funkcji) jest w
[`imp4-wersja-finalna.md`](imp4-wersja-finalna.md); historia zmian w [`../CHANGELOG.md`](../CHANGELOG.md).

## Spis treści

1. [Czym jest ImpoCraft](#1-czym-jest-impocraft)
2. [Instalacja, wersja przenośna, aktualizacje](#2-instalacja-wersja-przenośna-aktualizacje)
3. [Pojęcia — słowniczek](#3-pojęcia--słowniczek)
4. [Okno programu](#4-okno-programu)
5. [Pierwsza impozycja krok po kroku](#5-pierwsza-impozycja-krok-po-kroku)
6. [Montaż akcydensów — wstęga](#6-montaż-akcydensów--wstęga)
7. [Rodzaje arkuszy: jedno-, dwustronnie, przez markę, ekonomiczny](#7-rodzaje-arkuszy)
8. [Kadrowanie PDF i dopasowanie stron](#8-kadrowanie-pdf-i-dopasowanie-stron)
9. [Druk cyfrowy — recto/verso i kalibracja](#9-druk-cyfrowy--rectoverso-i-kalibracja)
10. [Tabela stron](#10-tabela-stron)
11. [Podgląd arkusza, edytor użytków, autowypełnianie](#11-podgląd-arkusza-edytor-użytków-autowypełnianie)
12. [Znaczniki](#12-znaczniki)
13. [Wykonanie impozycji: preflight, plik wynikowy, ustawienia](#13-wykonanie-impozycji)
14. [Programy dodatkowe](#14-programy-dodatkowe)
15. [Generator naklejek TAXI](#15-generator-naklejek-taxi)
16. [Projekty, szablony prac, profile maszyn](#16-projekty-szablony-prac-profile-maszyn)
17. [Skróty klawiszowe](#17-skróty-klawiszowe)
18. [Ograniczenia i zasady bezpieczeństwa produkcji](#18-ograniczenia-i-zasady-bezpieczeństwa-produkcji)
19. [Budowa programu (dla programisty)](#19-budowa-programu-dla-programisty)
20. [Testy, budowanie, wydawanie wersji](#20-testy-budowanie-wydawanie-wersji)
21. [Rozwiązywanie problemów](#21-rozwiązywanie-problemów)

---

## 1. Czym jest ImpoCraft

ImpoCraft to program na Windows do **impozycji PDF** — układania stron (użytków) na arkuszu drukarskim: wizytówek,
ulotek, naklejek, kart itp. Program bierze pliki PDF od klienta, rozmieszcza je na arkuszu (np. SRA3), dodaje znaczniki
cięcia i pasowania i zapisuje gotowy, **wektorowy** PDF do druku cyfrowego albo offsetowego.

- **Wzorowany funkcjonalnie na Impozycjonerze 4**, ale to niezależna implementacja: własny kod, własne ikony,
  bez plików, grafik i tekstów oryginału. Zakres: **akcydensy** (bez montażu książek i broszur — świadoma decyzja).
- **Wektorowo:** strony PDF są wstawiane jako wektory — tekst i grafika nie są rasteryzowane, jakość się nie zmienia.
- **Oryginały nie są zmieniane.** Program czyta PDF-y i zapisuje nowe pliki; projekt `.psimp` tylko wskazuje na PDF-y.
- **Bez abonamentu, lokalnie:** nic nie jest wysyłane do sieci poza sprawdzeniem aktualizacji na GitHubie.

Program ma trzy główne zakładki: **Impozycja PDF**, **Programy dodatkowe** (narzędzia na stronach PDF i generatory
kodów) i **Generator naklejek TAXI**.

---

## 2. Instalacja, wersja przenośna, aktualizacje

### Instalator
Plik `ImpoCraft-<wersja>-instalator.exe` (z GitHub → Releases). Instaluje program w Program Files, dodaje skrót w menu
Start (opcjonalnie na pulpicie), kojarzy pliki `.psimp` z programem i dodaje wpis w „Aplikacje i funkcje” z
deinstalatorem. Wymagania: Windows 10/11 64-bit; nic więcej nie trzeba instalować.

### Wersja przenośna
`ImpoCraft-<wersja>-przenosny.zip` — rozpakuj (np. na pendrive) i uruchom `ImpoCraft.exe`. Obok EXE leży plik
`PORTABLE.txt`: dopóki istnieje, dane programu zapisują się w podfolderze `dane` obok programu, a nie na komputerze.
Folder `przyklady` zawiera przykładowe PDF-y i projekty.

### Gdzie program trzyma dane
| Co | Wersja instalowana | Wersja przenośna |
|---|---|---|
| Szablony prac (`job_templates.json`) | `%APPDATA%\ImpoCraft` | `dane\` obok EXE |
| Profile maszyn — kalibracja verso (`duplex_profiles.json`) | jw. | jw. |
| Pliki znaczników własnych U1L/U1R/U2L/U2R | `%APPDATA%\ImpoCraft\znaczniki` | `dane\znaczniki` |
| Stan aktualizacji (ostatnie sprawdzenie, pominięta wersja) | `%APPDATA%\ImpoCraft` | `dane\` |

Przy pierwszym uruchomieniu po zmianie nazwy program kopiuje dane ze starego folderu `%APPDATA%\Impozycjoner Studio`.

### Aktualizacje
- Przy starcie program sprawdza w tle (najwyżej raz na 6 godzin), czy na GitHubie jest nowsze wydanie.
  Ręcznie: przycisk **„Sprawdź aktualizacje”** na dolnym pasku.
- Okno aktualizacji pokazuje opis zmian i daje wybór: **Zaktualizuj teraz**, **Strona wydania**, **Pomiń tę wersję**,
  **Później**; przełącznik „Sprawdzaj aktualizacje przy uruchomieniu” wyłącza automatyczne sprawdzanie.
- **Zaktualizuj teraz** pobiera instalator, **sprawdza jego sumę SHA-256** (plik `.sha256` z wydania) i dopiero wtedy
  uruchamia instalację w tle; po niej program uruchamia się ponownie. Plik o złej sumie nie jest uruchamiany.
- Wersja przenośna tylko informuje o nowej wersji — pobierz nowy ZIP ze strony wydania i podmień folder.

---

## 3. Pojęcia — słowniczek

| Pojęcie | Znaczenie |
|---|---|
| **Użytek** | Jedna kopia produktu na arkuszu (np. jedna wizytówka). |
| **Netto** | Wymiar po docięciu (np. 90 × 50 mm). Na nim stoją znaczniki cięcia. |
| **Spad** | Zapas grafiki poza netto (zwykle 1,5–3 mm), żeby po cięciu nie było białych krawędzi. Może być równy z każdej strony albo osobny L/P/G/D. |
| **Brutto** | Netto + spady — obszar grafiki pobierany z PDF i zajmowany na arkuszu. |
| **Arkusz** | Papier, na którym drukujemy (np. SRA3 450 × 320 mm). |
| **Siatka K × W** | Kolumny × wiersze użytków. 0 = program dobiera sam. |
| **Recto / verso** | Przód / tył arkusza w druku dwustronnym. |
| **TrimBox** | Pole w PDF mówiące, gdzie jest netto strony. Program z niego korzysta przy dopasowaniu. |
| **Płyta / chwyt** | W offsecie: płyta drukowa jest większa od papieru; chwyt to pas przy krawędzi chwytaków maszyny. |
| **Marka boczna / czołowa (MB / MC)** | Sposób odwracania arkusza w maszynie offsetowej: przez bok (work-and-turn) albo przez czoło (work-and-tumble). |
| **Wakat** | Celowo puste pole w kolejności stron. |
| **Preflight** | Kontrola PDF i ustawień przed zapisem wyniku. |
| **`.psimp`** | Plik projektu ImpoCraft (ustawienia + odnośniki do PDF-ów). |

---

## 4. Okno programu

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ Zakładki: Impozycja PDF │ Programy dodatkowe │ Generator naklejek TAXI          │
│ Pasek: Otwórz PDF · Wczytaj/Zapisz projekt · Nowa · Ustawienia… · Szablon pracy│
│ WSTĘGA: Montaż akcydensów │ Kadrowanie PDF │ Druk cyfrowy — recto/verso          │
├───────────────────────────────┬──────────┬───────────────────────┬────────────┤
│ PODGLĄD ARKUSZA               │ pasek:   │ TABELA STRON          │ ZNACZNIKI  │
│ (prawdziwy render albo        │ Symbole  │ przyciski plików      │ N W T B P S│
│  symbole)                     │ Edytuj   │ informacje o pliku    │ A O K U    │
│                               │ Rejestr. │ PODSUMOWANIE          │ numery     │
│ zakładki arkuszy 1, 2… / 1R 1V│ Preflight│ WYKONAJ IMPOZYCJĘ     │            │
├───────────────────────────────┴──────────┴───────────────────────┴────────────┤
│ ImpoCraft 0.5.9 · Sprawdź aktualizacje · stan montażu · rozmiar PDF            │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Wstęga** — wszystkie parametry montażu, w trzech zakładkach (rozdz. 6–9).
- **Podgląd** — tak wygląda arkusz w pliku wynikowym. **Symbole** przełączają na schemat (kolor = plik, opis
  `strona:obrót°`, biała belka = góra strony). Pod podglądem zakładki arkuszy; PgUp / PgDn zmienia arkusz.
- **Tabela stron** — każdy wiersz to strona, która pójdzie do impozycji (rozdz. 10).
- **Podsumowanie** — liczba stron, arkuszy, użytków na arkuszu, pustych pól, wymiar brutto/netto.
- **Pasek znaczników** po prawej — klik włącza/wyłącza znacznik, **prawy przycisk otwiera jego parametry** (rozdz. 12).
- **Pasek dolny** — wersja, aktualizacje, siatka i obrót, rozmiar strony PDF, komunikaty błędów konfiguracji.

---

## 5. Pierwsza impozycja krok po kroku

Przykład: 2 wzory wizytówek 90 × 50 mm, spad 2 mm, arkusz SRA3.

1. **Otwórz plik pdf do impozycji** (Ctrl+O) — wybierz PDF-y. Pojawią się w tabeli stron.
2. Wstęga **Montaż akcydensów → Użytek netto**: wybierz „Wizytówka 90 × 50 mm” albo wpisz wymiary.
   Obrót „Auto” sam wybiera ułożenie z większą liczbą użytków.
3. **Spady**: wpisz 2. Opis obok pokazuje brutto (94 × 54 mm).
4. **Arkusz**: SRA3 450 × 320 mm; **Odstępy i marginesy**: np. odstęp 5 mm, margines 6 mm.
5. **Rodzaj arkuszy**: Jednostronnie (albo Dwustronnie — rozdz. 7).
6. W tabeli ustaw **Nakład** każdego pliku (ile razy ma wystąpić każda strona). Podgląd odświeża się sam.
7. Włącz **Linie cięcia (N)** na pasku znaczników.
8. **Preflight** (Ctrl+P) — przeczytaj uwagi. Błędy geometrii blokują zapis, ostrzeżenia trzeba potwierdzić.
9. **WYKONAJ IMPOZYCJĘ** (Ctrl+E) — program podpowie nazwę, np. `wizytowki_90x50mm_impozycja.pdf`.
10. **Zapisz projekt** (Ctrl+S), żeby wrócić do pracy później.

Zawsze sprawdź wynik w czytniku PDF i zrób wydruk próbny przed nakładem.

---

## 6. Montaż akcydensów — wstęga

| Grupa | Pola | Działanie |
|---|---|---|
| **Użytek netto i obrót** | Poziomo, Pionowo, obrót (Auto / 0 / 90 / 180 / 270°), lista formatów | Wymiar netto. Formaty: wizytówki 93 × 53 i 90 × 50, DL, A7, A6, A5, A4 (pion/poziom), „Z PDF (oryginał)”, niestandardowy. Auto wybiera obrót dający więcej użytków. |
| **Tabela (0 = auto)** | K, W | Liczba kolumn i wierszy; 0 = najwięcej, ile się mieści. |
| **Autowypełnianie** | przycisk + opis | Kolejność wypełniania pól (rozdz. 11). |
| **Spady (dla obrotu 0°)** | Spad, „=”, L / P / G / D, „brutto = netto + spady” | Przy „=” jeden spad dla wszystkich krawędzi. Bez „=” osobno lewy, prawy, górny, dolny — **dla strony nieobróconej**; przy obrocie użytku spady obracają się razem z grafiką. |
| **Odstępy i marginesy** | Odstęp X/Y, Margines X/Y | Odstęp między użytkami (od brutto do brutto) i margines od krawędzi arkusza. Siatka jest wyśrodkowana. |
| **Arkusz** | lista formatów, Szer., Wys. | SRA3 (poziomo/pionowo), SRA4, A3, A4, B2 albo własny. |
| **Rodzaj arkuszy** | przyciski | Jednostronnie, Dwustronnie długa / krótka krawędź, Ekonomiczny, **Przez markę ▾** (rozdz. 7). |

Gdy użytki się nie mieszczą albo ustawienia są sprzeczne, pasek dolny pokazuje „Błąd konfiguracji / PDF: …”
z opisem — podgląd i eksport nie powstają, dopóki błąd nie zniknie.

---

## 7. Rodzaje arkuszy

### Jednostronnie
Strony wszystkich plików po kolei, każda tyle razy, ile wynosi nakład pliku. Pola wypełniane wg autowypełniania
(domyślnie od lewego górnego rogu, wierszami).

### Dwustronnie — długa / krótka krawędź (druk cyfrowy)
Każdy arkusz ma recto i verso (zakładki 1R / 1V). Strony łączą się w pary przód/tył:
- bez ról: strony 1/2, 3/4… każdego pliku;
- z rolami (tabela → **Przód / tył — role…**, Ctrl+R): **Przód**, **Tył sparowany** (kolejne tyły do kolejnych
  przodów), **Tył wspólny** (jedna strona pod każdym przodem), **Pomiń**. Role ustawia się dla całego pliku,
  zaznaczonych stron albo zakresu typu `1,3-8,22`.

Tył jest automatycznie ułożony lustrzanie tak, żeby po przewróceniu arkusza leżał dokładnie za swoim przodem.
„Długa / krótka krawędź” musi być taka sama jak w sterowniku drukarki.

### Przez markę ▾ (offset) — nowość 0.5.9
Przycisk z menu czterech wariantów:

| Wariant | Co robi |
|---|---|
| **Pełny MB** | Przód i tył na osobnych płytach; tył odbity w poziomie (arkusz odwracany przez markę boczną). |
| **Pełny MC** | Przód i tył na osobnych płytach; tył odbity w pionie i obrócony o 180° (odwracany przez czoło). |
| **Niepełny MB** | Przody i tyły **na jednej płycie** — przody w lewej połowie, tyły w prawej, każdy tył w kolumnie lustrzanej do swojego przodu. Arkusz drukuje się dwa razy tą samą płytą i tnie na pół → dwa komplety. **Liczba kolumn musi być parzysta.** |
| **Niepełny MC** | Jak wyżej, ale przody w górnej połowie, tyły w dolnej, obrócone o 180°. **Liczba wierszy musi być parzysta.** |

Przy niepełnych wariantach spady na osi odwrócenia muszą być równe (przy MC — oba osie); w przeciwnym razie program
pokazuje jawny błąd. Podsumowanie pokazuje „przód i tył na jednej płycie” i liczbę par na płycie.

### Ekonomiczny (mix nakładów)
Kilka różnych wzorów o różnych nakładach (np. A = 700, B = 300) rozkładanych na wspólnych arkuszach w proporcji
zamówienia — minimalna liczba arkuszy, bez nadprodukcji. Przycisk **Plan ekonomiczny** pokazuje rozkład arkuszy
i pozwala zapisać raport CSV (obok wyniku powstaje `…_plan_ekonomiczny.csv`). Każdy arkusz w pliku jest drukowany
**raz** — nie ustawiaj kopii w drukarce. Tylko jednostronnie, jeden format użytku; limit 10 000 arkuszy na eksport.

---

## 8. Kadrowanie PDF i dopasowanie stron

Zakładka wstęgi **Kadrowanie PDF**:

| Grupa | Działanie |
|---|---|
| **1. Oryginał PDF** | Rozmiar źródła — domyślnie odczytywany z każdego pliku. |
| **3. Brutto = netto + spady** | Domyślnie liczone automatycznie. |
| **Sposób dopasowania PDF** | **Kadruj 1:1** — wycina brutto ze środka strony bez skalowania (np. 110 × 70 → 96 × 56). **Bez skalowania** — TrimBox strony musi równać się netto (±0,5 mm), inaczej błąd. **Dopasuj** — proporcjonalnie, cała treść (możliwe marginesy). **Wypełnij** — proporcjonalnie z przycięciem. **Wypełnij ze spadem** — grafika pokrywa całe brutto. Opcje: przytnij białe marginesy źródła, obracaj strony do orientacji użytku. |
| **Kadr wybranego PDF** | Okno z podglądem strony i ramkami (turkusowa = brutto, pomarańczowa = netto); przesuwasz myszą lub wpisujesz X/Y co 0,1 mm. Kadr jest osobny dla każdego pliku. |

Program **nie dorabia spadów z niczego**: jeśli PDF nie ma grafiki poza netto, spad zostanie biały. Do dorobienia
spadów służy program dodatkowy „Dodaj spady” (rozdz. 14).

---

## 9. Druk cyfrowy — recto/verso i kalibracja

Drukarki cyfrowe często przesuwają tył względem przodu o ułamki milimetra. Zakładka **Druk cyfrowy — recto/verso**:

1. **Przesunięcie verso X / Y** — przesuwa całą stronę verso (+X w prawo, +Y w dół), krok 0,1 mm.
2. **Kalibracja spasowania → 1. Arkusz testowy PDF** — dwustronny arkusz z krzyżami A–E (przód) i pierścieniami
   (tył) z podziałką. Drukuj 100 %, bez dopasowania do strony, z tą samą krawędzią odwracania.
3. **2. Wpisz pomiar** — patrząc od przodu pod światło, wpisz przesunięcie pierścienia względem krzyża; program
   przeliczy znaki i ustawi nowe przesunięcie.
4. **Profil maszyny** — zapisz przesunięcie i krawędź jako profil (np. „Xerox SRA3”) i wczytuj przy kolejnych pracach.
5. **Rejestracja przód + tył** (pasek przy podglądzie) — nakłada przód i odwrócony tył półprzezroczyście do kontroli.

Kalibracja dotyczy tylko druku dwustronnego; przy odwracaniu przez markę arkusz testowy odmawia (pasowanie ustawia
się na maszynie).

---

## 10. Tabela stron

Każdy wiersz to strona w kolejności impozycji: **S** (kolejny numer), **SPDF** (numer strony w pliku), nazwa pliku,
szerokość, wysokość, nakład, rola. Kolor tła = plik. Przyciski pod tabelą: **+ Dodaj PDF**, **Usuń plik**, ↑ ↓
(kolejność plików), **Nakład** + Zmień, **Przód / tył — role…**, **Kadruj PDF…**, **Plan ekonomiczny**.

**Menu prawego przycisku:**
- **Zaznaczanie:** wszystkie, parzyste, nieparzyste, odwróć; ujęte / nieujęte w impozycji; takie same.
- **Znajdź pierwszy arkusz z tą stroną.**
- **Rozmiar:** zmień rozmiar zaznaczonych stron (skaluj); koryguj rozmiar strony (obszar netto) — okno z ramką
  netto do przesunięcia, dla jednej / wszystkich / parzystych / nieparzystych stron; ustaw rozmiar użytka równy
  rozmiarowi strony; kadruj plik do netto / brutto i zapisz do nowego pliku.
- **Wiersze:** wstaw wakat przed / po / tutaj, usuń dodane wakaty; wstaw plik przed / po; zamień na stronę innego
  pliku / inną stronę z pliku; kopiuj, wytnij, wklej przed / po (też Ctrl+C / X / V).
- **Pomiń zaznaczone strony** / przywróć (strona zostaje w pliku, ale nie idzie do druku).
- **Usuń wszystkie wiersze z pliku**, **Otwórz plik w czytniku PDF**.

Kliknięcie użytku na podglądzie zaznacza jego wiersz w tabeli.

---

## 11. Podgląd arkusza, edytor użytków, autowypełnianie

- **Autowypełnianie…** — narożnik startowy (LG / PG / LD / PD), wierszami lub kolumnami, strony kolejno albo
  **w stosie** (po złożeniu stosu arkuszy i cięciu każdy stosik ma kolejne numery — np. numerowane bloczki),
  wszystkie / nieparzyste / parzyste strony, kolejność NPNP lub NNNPPP, powtórzenia każdej strony.
- **Edytuj użytki** — okno edytora: przeciągnij stronę na pole, zamień dwa użytki, przesuń użytek (X/Y co 0,1 mm),
  obróć (R), wyczyść pole, przywróć automat. Przód i tył edytuje się osobno. Nakładające się zajęte użytki są
  oznaczone na czerwono i zgłaszane w preflight.
- **Nakładki** (Brak / Numer strony / Plik + numer) — duże numery tylko na podglądzie, **nie trafiają do PDF**.

---

## 12. Znaczniki

Pasek **ZNACZNIKI** po prawej. Klik = włącz/wyłącz, **prawy przycisk = parametry**, pojedyncza litera na klawiaturze
= skrót (gdy kursor nie jest w polu tekstowym). Parametry zapisują się w projekcie.

| Znacznik | Skrót | Co rysuje / najważniejsze parametry |
|---|---|---|
| **Linie cięcia** | N | Kreski na przedłużeniu netto: odstęp od spadu, długości, grubość [pt], kolor (czarny / K 100 % / rejestracyjny), strony wszystkie/parzyste/nieparzyste, tylko pierwszy arkusz, zaznaczanie narożników, środek netto. |
| **Wycinka** | W | Pas cięcia między środkowymi kolumnami/wierszami (tylko przy parzystej liczbie). |
| **Docięcie TrimBox** | T | „Włos” na krawędzi stron parzystych / nieparzystych. |
| **Brutto** | B | Kreski na krawędziach brutto. |
| **Pasery** | P | Krzyże pasowania (dwa wzory), liczba na boku, średnica, położenie; kolor 100 % CMYK. |
| **Pasery brutto** | S | Krzyże przy narożnikach siatki brutto (V1, V2, H1, H2). |
| **Ramka użytku** | A | Cienka ramka wokół każdego zajętego użytku na netto i/lub brutto (rozszerzenie ImpoCraft). |
| **Opis arkusza** | O | Nazwa pliku, „Arkusz N • Strona M”, pole zadruku, netto/brutto, data, własny tekst. |
| **Pasek kontrolny** | K | Pasek kostek kolorów K1–K12 (CMYK %) u góry / dołu / na wycince, albo z pliku PDF. |
| **Znaczniki własne** | U | Własne PDF-y U1L/U1R/U2L/U2R w zadanych miejscach na stronach nieparzystych/parzystych (folder `znaczniki`). |
| **Numery stron** | — | Numer strony przy użytku. |

**Wyłącz wszystkie** wyłącza wszystkie znaczniki naraz. Gdy znacznik się nie mieści (np. opis, pasek), program
pomija go i pisze uwagę na pasku stanu i w preflight.

---

## 13. Wykonanie impozycji

### Preflight (Ctrl+P)
Sprawdza: rozmiary TrimBox stron, czy jest grafika na spad, rozdzielczość obrazów (DPI po skalowaniu),
nieosadzone fonty, różne rozmiary stron w jednym pliku, użytki poza arkuszem, nakładanie się użytków, zgodność ról
przód/tył, nakłady w trybie ekonomicznym, znaczniki, które się nie mieszczą. **Błędy blokują eksport**, ostrzeżenia
trzeba potwierdzić. Raport można zapisać do TXT / JSON.

### WYKONAJ IMPOZYCJĘ (Ctrl+E)
- Pole **Wykonaj:** wszystkie arkusze / tylko aktywny / wszystkie oprócz aktywnego.
- Nazwa podpowiadana: `<nazwa pierwszego pliku>_<netto>mm_impozycja.pdf`. Niedozwolone znaki
  `# % & * : < > ? / \ { } |` są odrzucane; nie da się nadpisać pliku źródłowego.
- **Eksportuj pojedyncze strony** — zamiast arkusza: każda strona w formacie netto (lub netto + spad), bez montażu.

### Ustawienia… (pasek u góry)
- **Metadane PDF** (tytuł, autor, temat, słowa kluczowe) i dopisek do nazwy.
- **Plik wynikowy — łączenie:** jeden plik; jeden plik + arkusze; + każda strona osobno; tylko arkusze; arkusze +
  strony; każda strona osobno. Pliki części: `<nazwa>--arkusz-01.pdf` (przód i tył razem), `<nazwa>--01.pdf`.
- **Rozmiar wynikowego PDF:** papier (domyślnie — PDF = arkusz), pole zadruku, papier + chwyt, pole zadruku + chwyt,
  płyta (szerokość, wysokość, chwyt — domyślnie 11 mm, zmniejszenie o [pt]); margines techniczny „na łapki”. Na
  większych stronach TrimBox wskazuje papier. Rozmiar strony PDF widać na pasku dolnym.

---

## 14. Programy dodatkowe

Zakładka **Programy dodatkowe** — kafelki w kategoriach. Wejściowy plik **nigdy nie jest nadpisywany**; wynik
dostaje dopisek w nazwie (np. `--obrot`). Zakres stron wpisuje się jak `1,3-8,22`.

| Kategoria | Narzędzie | Wynik |
|---|---|---|
| Dziel i łącz | Rozdziel na pojedyncze strony | `nazwa--01.pdf`, `--02`… |
| | Połącz pliki PDF | `--polaczone` |
| | Wydziel okładkę i wkład | okładka = strony 1, 2, przedostatnia, ostatnia |
| | Wydziel zakresy po N stron | kolejne pliki po N stron |
| Wybierz i usuń strony | Wydziel strony z zakresu | opcjonalnie każda osobno i plik bez wydzielonych |
| | Usuń wybrane strony | `--bez_stron` |
| | Wydziel parzyste i nieparzyste | dwa pliki |
| Kolejność i obrót | Obróć strony | kąt dodawany do obecnego; opcja +180° dla parzystych |
| | Powiel strony | każda strona N razy pod rząd |
| | Tasuj strony / kartki | 1,2,3,4 → 4,3,2,1 albo 3,4,1,2 |
| Format, spady i cięcie | Dodaj spady | wycinek krawędzi rozciągany na spad, osobno L/P/G/D |
| | Skaluj strony | do mm albo %, TrimBox lub MediaBox, opcjonalnie wyśrodkowanie na stronie |
| | Rozetnij strony PDF | kolumny × wiersze (np. plakat na kafle), zakładki do sklejania, znaczniki |
| | Rozetnij rozkładówki | rozkładówka → dwie strony z TrimBox i spadem przy grzbiecie |
| Kody | Kody QR | WWW, wizytówka vCard/MeCard, e-mail, telefon, SMS, Wi-Fi, lokalizacja, wydarzenie, przelew, tekst |
| | Kody Data Matrix | zwykłe albo **numery seryjne** (wzór z `{SER}`, zakres od–do, krok, zera wiodące) |
| | Kody EAN-13 / EAN-8 | cyfra kontrolna liczona automatycznie |

Kody: treść wpisana w okno albo z pliku `.txt` (jeden kod w wierszu); każdy kod w osobnym pliku albo wszystkie
w jednym PDF; kody są **wektorowe** (prostokąty CMYK), kolor i rozmiar do ustawienia. Każdy kod generowany w testach
jest skanowany z PDF, żeby mieć pewność, że się czyta.

---

## 15. Generator naklejek TAXI

Zakładka do zamówień naklejek TAXI (Szczecin): wpisz numery (np. `1740, 1713`), kliknij **GENERUJ PLIKI TAXI →
JEDEN ZIP**. Dla każdego numeru: `<NUMER>_lewy.tif`, `<NUMER>_prawy.tif` (2283 × 1102 px, 200 DPI) i `<NUMER>_tyl.svg`
(numer 55 mm wysokości, napis SZCZECIN 120 mm szerokości, napisy jako krzywe). Font Impact z systemu Windows.
Przed produkcją zrób próbne cięcie na ploterze.

---

## 16. Projekty, szablony prac, profile maszyn

- **Projekt `.psimp`** — archiwum ZIP z plikiem `project.json`: wszystkie ustawienia, lista plików (ścieżki
  względne), nakłady, role, kadry, korekty stron, ręczne zmiany użytków. **PDF-y nie są kopiowane do projektu** —
  przenosząc projekt, przenieś też PDF-y (najlepiej w tym samym folderze). Nowe opcje są w projekcie opcjonalne:
  stare projekty otwierają się i dają ten sam wynik co wcześniej.
- **Szablon pracy** (pasek u góry) — zapamiętany zestaw ustawień jednej pracy (arkusz, netto, spady, odstępy, siatka,
  tryb, dopasowanie, znaczniki) bez plików. Wbudowane szablony (wizytówki, ulotki A6/DL/A5 na SRA3) są tylko do odczytu.
  Szablon można powiązać z profilem maszyny.
- **Profil maszyny** — przesunięcie verso X/Y i krawędź odwracania (rozdz. 9).

---

## 17. Skróty klawiszowe

| Skrót | Działanie |
|---|---|
| Ctrl+O | Otwórz plik PDF do impozycji |
| Ctrl+N | Nowa impozycja |
| Ctrl+W | Wczytaj projekt |
| Ctrl+S / Shift+Ctrl+S | Zapisz projekt / zapisz jako |
| Ctrl+E | Wykonaj impozycję |
| Ctrl+P | Preflight |
| Ctrl+R | Role przód / tył |
| PgUp / PgDn | Poprzedni / następny arkusz |
| N W T B P S A O K U | Przełącz znacznik (poza polami tekstowymi) |
| Ctrl+C / X / V (w tabeli) | Kopiuj / wytnij / wklej wiersze |

---

## 18. Ograniczenia i zasady bezpieczeństwa produkcji

- **Zawsze wydruk próbny** — zwłaszcza dwustronny i przez markę: ułożenie tyłu zależy od maszyny.
- Program **nie tworzy spadów z niczego** i nie rozciąga grafiki bez Twojej decyzji (tryby skalowania są jawne).
- Preflight jest uproszczony: nie zastępuje kontroli separacji, nadruku (overprint), ICC i PDF/X.
- Jeden format użytku na arkuszu (wspólne netto/brutto dla całego montażu).
- Brak montażu książek i broszur (stare projekty broszur nadal się otwierają), brak: creep, falcowania, wykrojnika
  zewnętrznego, CODE128/EAN-128, kreatora podziału arkusza. Pełna lista — `imp4-wersja-finalna.md`.
- Przy bardzo dużych pracach eksport może na chwilę zablokować okno.

---

## 19. Budowa programu (dla programisty)

Język: **Python 3.12**, interfejs **Tkinter** (ttk) + Pillow, PDF: **PyMuPDF** (wstawianie stron jako wektory),
kody: **zxing-cpp**, budowanie: **PyInstaller** + **Inno Setup 6**.

### Zasada warstw
Logika jest **bez interfejsu** (silnik, czyste moduły) i ma testy; interfejs tylko zbiera pola i wywołuje silnik.
Podgląd i eksport używają **tego samego** planu arkuszy i renderu — to, co widać, jest w pliku.

### Moduły

| Plik | Zawartość |
|---|---|
| `engine.py` | Serce programu: `Settings` (wszystkie ustawienia), `Job` (plik + nakład + role + kadr), `Project`; `validate`, `geometry` (siatka, obrót, pojemność), `plan_sides` (który PDF na którym polu którego arkusza — jedno-, dwustronnie, przez markę, ekonomiczny, broszura), render arkusza, `export_pdf`, `preview`, zapis/odczyt `.psimp`. |
| `marks.py` | Geometria znaczników (linie cięcia, pasery, wycinka, opis, pasek, własne…). |
| `press.py` | Rozmiar wynikowego PDF (papier / pole zadruku / chwyt / płyta). |
| `autofill.py` | Kolejność wypełniania pól. |
| `page_rows.py`, `table_actions.py` | Operacje na wierszach tabeli stron (wakaty, wstaw, zamień, kopiuj). |
| `page_boxes.py`, `page_box_ui.py`, `crop_editor.py`, `whitecrop.py` | Korekta obszaru netto, kadr, białe marginesy. |
| `preflight.py` | Kontrola PDF i ustawień, raport TXT/JSON. |
| `naming.py` | Nazwy plików wynikowych i części. |
| `pageops.py`, `pdftools.py` | Zakresy stron i programy dodatkowe (dziel, łącz, obróć, spady, skaluj, rozetnij…). |
| `codes.py`, `codes_ui.py`, `barcodes.py` | QR, Data Matrix, EAN. |
| `duplex_calibration.py`, `duplex_test_sheet.py` | Profile maszyn i arkusz testowy recto/verso. |
| `job_templates.py` | Szablony prac. |
| `taxi_generator.py`, `taxi_ui.py` | Generator TAXI. |
| `app.py` | Okno główne, wstęga, tabela, podgląd, okna dialogowe. `tools_ui.py` — programy dodatkowe; `ui_icons.py` — ikony rysowane kodem; `sheet_editor.py` — edytor użytków. |
| `app_info.py` | **Jedno miejsce** na nazwę, wersję, autora i repozytorium aktualizacji. |
| `updater.py`, `update_ui.py` | Aktualizacje z GitHub Releases (wersje, pobieranie, SHA-256, instalacja). |
| `user_data.py` | Folder danych (`%APPDATA%\ImpoCraft` albo `dane` w wersji przenośnej). |
| `selftest.py` | `ImpoCraft.exe --self-test` — sprawdzenie zbudowanego programu. |

### Przepływ danych
```
PDF-y + ustawienia z wstęgi ─► Settings / Job ─► validate ─► geometry (siatka)
   ─► plan_sides (strona → pole → arkusz, przód/tył) ─► render (wektorowo, + znaczniki)
   ─► podgląd w oknie  albo  export_pdf (+ rozmiar wynikowy, metadane, pliki części)
```

### Zasady rozwoju (z `AGENTS.md`)
- Nie tworzymy atrap: funkcja nieobsłużona zgłasza jawny błąd.
- Zmiany addytywne: nowe pola `Settings` mają wartości domyślne dające stary wynik; stare `.psimp` działają.
- Fakty z oryginału opisujemy własnymi słowami; własne decyzje to hipotezy **H-nn**, pytania otwarte **OQ-nn**
  (w `imp4-wersja-finalna.md`).
- Czysta implementacja: bez kodu, grafik, plików i tekstów oryginału.

---

## 20. Testy, budowanie, wydawanie wersji

### Uruchomienie ze źródeł
`START_WINDOWS.bat` (tworzy `.venv`, instaluje zależności, uruchamia). Albo `python app.py`.

### Testy
```bash
.venv\Scripts\python.exe -m pytest -q
```
Blisko 490 testów: geometria, plan arkuszy, znaczniki, eksport z kontrolą pikseli (np. czy tył leży za przodem),
kody skanowane z PDF, okna interfejsu, instalator, aktualizacje. Dodatkowo przy każdej zmianie silnika porównuje się
skróty eksportu przykładowych projektów z `examples/` — muszą być identyczne jak przed zmianą.

### Budowanie
- `BUILD_EXE_WINDOWS.bat` — testy → PyInstaller → `dist\ImpoCraft\` + `--self-test` → ZIP przenośny.
  Gdy test nie przejdzie, EXE nie powstaje.
- `BUILD_INSTALLER_WINDOWS.bat` — to samo + podpis (jeśli ustawiony certyfikat) + instalator Inno Setup
  `dist\ImpoCraft-<wersja>-instalator.exe`.
- Podpis cyfrowy: zmienne `IMPOCRAFT_SIGN_THUMBPRINT` albo `IMPOCRAFT_SIGN_PFX` + `IMPOCRAFT_SIGN_PASSWORD`
  ustawiane w konsoli — **nigdy w repozytorium**.

### Wydanie nowej wersji
1. Podnieś `VERSION` w `app_info.py`, w `CHANGELOG.md` zamień „Unreleased” na sekcję wersji (opis po polsku dla
   użytkowników + szczegóły po angielsku).
2. `BUILD_INSTALLER_WINDOWS.bat`.
3. `python scripts/publish_release.py` — tworzy wydanie `v<wersja>` na GitHubie z instalatorem, plikiem `.sha256`
   i ZIP-em; opis z CHANGELOG. Od tej chwili zainstalowane programy proponują aktualizację.

### Praca z Git
Gałąź na zmianę → testy → pull request → merge do `main` w repozytorium `Davidgracz/ukladex_tmp`. Do repozytorium
nie trafiają: `.venv`, `build`, `dist`, pliki klientów, pliki i teksty oryginalnego programu.

---

## 21. Rozwiązywanie problemów

| Objaw | Przyczyna / rozwiązanie |
|---|---|
| „Użytki nie mieszczą się na arkuszu” | Zmniejsz marginesy, odstępy, spad albo siatkę K × W; sprawdź obrót. |
| „oryginał jest za mały na użytek ze spadami” | Przy Kadruj 1:1 PDF musi być ≥ brutto. Zmień sposób dopasowania albo spad. |
| Błąd TrimBox przy „Bez skalowania” | Netto PDF różni się od użytku o > 0,5 mm — wybierz Dopasuj/Wypełnij albo popraw netto. |
| „liczba kolumn/wierszy musi być parzysta” (przez markę) | Ustaw K (MB) albo W (MC) na liczbę parzystą. |
| Biały pasek na krawędzi po cięciu | PDF nie ma spadu — „Dodaj spady” w programach dodatkowych albo plik od klienta ze spadem. |
| Tył przesunięty względem przodu | Kalibracja verso (rozdz. 9), ta sama krawędź w programie i sterowniku. |
| Brak okna aktualizacji | Kliknij „Sprawdź aktualizacje”; potrzebny internet; wersja przenośna tylko informuje. |
| Program uruchamiany ze źródeł nie startuje | `BOOTSTRAP_WINDOWS.bat` naprawia środowisko `.venv`. |
| Sprawdzenie zbudowanego programu | `ImpoCraft.exe --self-test raport.txt` — raport zaczyna się od „OK” albo „BŁĄD”. |
