# ImpoCraft — jak przedstawić projekt

Przewodnik dla prezentującego (Dawid Gracz): co powiedzieć, co pokazać i w jakiej kolejności, jak odpowiadać na
pytania. Pełny opis funkcji jest w [`DOKUMENTACJA.md`](DOKUMENTACJA.md).

---

## 1. Projekt w jednym zdaniu

> **ImpoCraft to darmowy, lokalny program na Windows, który w kilka kliknięć układa pliki PDF klienta na arkuszu
> drukarskim — z liniami cięcia, spadami, drukiem dwustronnym i kontrolą błędów — i zapisuje gotowy, wektorowy PDF
> do druku.**

Wersja na 30 sekund:

> W drukarni codziennie trzeba rozłożyć wizytówki, ulotki czy naklejki na arkuszu SRA3, dodać spady i znaczniki
> cięcia, dopasować przód do tyłu. Robi się to w drogich programach albo ręcznie. ImpoCraft robi to automatycznie,
> pokazuje od razu podgląd arkusza, pilnuje błędów (za mały spad, za niska rozdzielczość, przesunięty tył)
> i zapisuje plik gotowy do druku. Do tego ma zestaw narzędzi do PDF-ów i generator kodów QR, Data Matrix i EAN.

---

## 2. Dla kogo i jaki problem rozwiązuje

| Odbiorca | Co go obchodzi | Co podkreślić |
|---|---|---|
| **Drukarnia / operator DTP** | Szybkość, brak błędów na maszynie | Automatyczna siatka, spady, znaczniki, preflight, dwustronność i kalibracja tyłu, przez markę (offset), szablony prac |
| **Właściciel firmy** | Koszt, oszczędność papieru | Bez abonamentu, tryb ekonomiczny (mniej arkuszy, zero nadprodukcji), mniej makulatury dzięki preflightowi |
| **Osoba techniczna / programista** | Jakość wykonania | Python + PyMuPDF, wektorowy wynik, ok. 490 testów automatycznych, testy pikselowe, aktualizacje z kontrolą SHA-256 |
| **Rekruter / portfolio** | Co umiesz zrobić | Kompletny produkt: od analizy wymagań przez silnik, interfejs, testy, instalator, aktualizacje po wydania na GitHubie |

---

## 3. Najmocniejsze argumenty (5 punktów do zapamiętania)

1. **Od PDF do arkusza w minutę** — wczytaj pliki, wybierz format, kliknij „WYKONAJ IMPOZYCJĘ”.
2. **Wynik wektorowy i oryginały nietknięte** — tekst i grafika nie tracą jakości; pliki klienta nie są zmieniane.
3. **Kontrola zanim coś pójdzie na maszynę** — preflight blokuje błędy (brak spadu, niska rozdzielczość, użytek poza
   arkuszem, zła para przód/tył).
4. **Prawdziwa produkcja** — druk dwustronny z kalibracją drukarki, odwracanie przez markę boczną i czołową
   (offset), mix nakładów, 10 rodzajów znaczników, rozmiar płyty i chwyt.
5. **Gotowy produkt, nie prototyp** — instalator, wersja na pendrive, automatyczne aktualizacje, ponad 25 wydanych
   wersji, regresja pilnowana testami.

---

## 4. Przygotowanie przed pokazem (lista kontrolna)

- [ ] Zainstalowana najnowsza wersja (0.5.9) — sprawdź „Sprawdź aktualizacje” na dolnym pasku.
- [ ] Skopiuj folder `examples` (albo `przyklady` z wersji przenośnej) w łatwo dostępne miejsce, np. na pulpit.
- [ ] Otwórz wcześniej w czytniku PDF: `crop_041_source_110x70.pdf` i `economic_040_montaz_SRA3.pdf` (do pokazania
      „przed / po”).
- [ ] Rozdzielczość ekranu co najmniej 1600 px szerokości (wstęga mieści się w całości); okno zmaksymalizowane.
- [ ] Zamknij inne programy i powiadomienia; przygotuj folder na wyniki (np. `Pulpit\pokaz`).
- [ ] Jeśli możesz — wydrukowany arkusz z próby (dwustronny), żeby dać go do ręki.

---

## 5. Scenariusz pokazu (ok. 15 minut)

### Krok 1 — problem (1 min)
Pokaż PDF klienta: jedna wizytówka 110 × 70 mm z białym marginesem (`crop_041_source_110x70.pdf`).
Powiedz: *„Klient przysyła taki plik, a ja muszę wydrukować 500 sztuk na arkuszach SRA3 i pociąć je na gilotynie.”*

### Krok 2 — impozycja w minutę (3 min)
1. **Ctrl+N** (nowa impozycja), potem **Ctrl+O** → wczytaj `crop_041_source_110x70.pdf`.
2. Ustawienia domyślne już pasują: wizytówka netto 93 × 53 mm, spad 1,5 mm, „Kadruj 1:1”, arkusz SRA3 450 × 320.
   Program wycina brutto 96 × 56 ze środka pliku i układa **21 użytków** (7 × 3, obrót 90°) — widać to na pasku dolnym.
3. Włącz **Linie cięcia (N)** — znaczniki pojawiają się na podglądzie.
4. Zmień obrót na 0° i z powrotem na Auto — liczba użytków spada z 21 do 20 i wraca; Auto wybiera lepsze ułożenie.
5. W tabeli ustaw **Nakład** na 2 — podgląd pokazuje drugi arkusz.

Puenta: *„Liczba użytków, położenie, znaczniki — wszystko liczy program.”*

### Krok 3 — kontrola błędów (2 min)
1. Wpisz spad 10 mm → pasek dolny pokaże błąd „oryginał jest za mały na użytek ze spadami” (brutto 113 mm nie
   mieści się w pliku 110 mm) — eksport jest zablokowany.
2. Wróć do 1,5 mm, kliknij **Preflight** (Ctrl+P) — pokaż raport (rozmiary, spad, DPI).

Puenta: *„Błąd widzę na ekranie, a nie po wydrukowaniu 200 arkuszy.”*

### Krok 4 — druk dwustronny (3 min)
1. Wczytaj projekt `role_demo.psimp` (Ctrl+W) — przody w jednym pliku, wspólny tył w drugim.
2. Pokaż zakładki arkuszy **1R / 1V** i przycisk **Rejestracja przód + tył** (nałożenie przodu i tyłu).
3. Zakładka **Druk cyfrowy — recto/verso**: arkusz testowy i „Wpisz pomiar” — *„drukarka przesuwa tył o 0,7 mm,
   program to koryguje”*.
4. **Rodzaj arkuszy → Przez markę ▾ → Niepełny MB**: przody w lewej połowie, tyły w prawej — jedna płyta
   offsetowa zamiast dwóch.
5. Przełącz na **Niepełny MC** — program od razu pokazuje błąd „liczba wierszy … musi być parzysta (jest 3)”:
   *„zabezpieczenie przed płytą, której nie da się odwrócić”*. Wróć do Niepełny MB.

### Krok 5 — oszczędność papieru: tryb ekonomiczny (2 min)
1. Wczytaj `economic_040_project.psimp`: trzy wzory, nakłady 42 / 21 / 15.
2. Kliknij **Plan ekonomiczny** — 4 arkusze, nadprodukcja 0; raport CSV do Excela.

Puenta: *„Trzy zlecenia na wspólnych arkuszach zamiast trzech osobnych przebiegów.”*

### Krok 6 — wynik (1 min)
**WYKONAJ IMPOZYCJĘ** (Ctrl+E) → nazwa podpowiada się sama (`crop_041_source_110x70_93x53mm_impozycja.pdf`) → otwórz wynik w czytniku,
powiększ znaczniki — *„wektorowo, ostre przy każdym powiększeniu”*.

### Krok 7 — narzędzia dodatkowe (2 min)
Zakładka **Programy dodatkowe** — kafelki: rozdziel / połącz / usuń strony, dodaj spady, skaluj, rozetnij plakat.
Pokaż **Kody QR → wizytówka vCard** albo **Data Matrix → numery seryjne** (np. `SN-{SER}`, 1–100 → 100 kodów
w jednym PDF). Zeskanuj kod telefonem z ekranu — działa.

### Krok 8 — zamknięcie (1 min)
*„Program jest zainstalowany jak każdy inny, sam się aktualizuje z GitHuba, a każda zmiana przechodzi ok. 490 testów
automatycznych. Następne w planie: (wybierz 1–2 z rozdziału 8).”*

**Wersja skrócona (5 min):** krok 2 → krok 3 (tylko preflight) → krok 6 → jeden kod QR z kroku 7.

---

## 6. Jak opowiedzieć o technice (dla osób technicznych)

- **Architektura:** silnik bez interfejsu (`engine.py`) liczy siatkę, plan arkuszy i renderuje; okno (Tkinter) tylko
  zbiera ustawienia. Podgląd i eksport używają tego samego kodu — co widać, to jest w pliku.
- **PDF:** PyMuPDF wstawia strony źródłowe jako obiekty wektorowe (bez rasteryzacji), z przycięciem do brutto
  i obrotem; znaczniki rysowane są kodem.
- **Testy:** ok. 490 testów (pytest), w tym testy „fizyczne” — renderowany jest arkusz i sprawdzane piksele, np. czy
  tył leży dokładnie za przodem po odwróceniu; kody QR/Data Matrix są skanowane z wygenerowanego PDF; przykładowe
  projekty muszą dawać identyczny wynik po każdej zmianie (ochrona przed regresją).
- **Wydania:** skrypt buduje EXE (PyInstaller), uruchamia testy i autotest gotowego programu, tworzy instalator
  (Inno Setup) i publikuje wydanie na GitHubie; program pobiera aktualizację i sprawdza jej sumę SHA-256.
- **Zgodność wstecz:** każda nowa opcja ma wartość domyślną dającą stary wynik — projekty sprzed roku otwierają się
  i drukują tak samo.
- **Metoda:** funkcje wzorowane na profesjonalnym programie do impozycji, zaimplementowane od zera — własny kod
  i grafika, decyzje projektowe opisane jako hipotezy z testami.

---

## 7. Pytania, które mogą paść — i odpowiedzi

| Pytanie | Odpowiedź |
|---|---|
| Czym to się różni od Impozycjonera / innych programów? | Darmowy, lokalny, bez abonamentu; podobny sposób pracy (wstęga, tabela stron, znaczniki), plus rzeczy własne: tryb ekonomiczny, kalibracja tyłu drukarki, ramka użytku, generatory kodów. Na razie bez montażu książek. |
| Czy to kopia innego programu? | Nie. Funkcjonalnie wzorowany na znanym programie branżowym, ale cały kod, ikony i teksty są własne; żadne pliki oryginału nie są używane. |
| Czy zmienia pliki klienta? | Nie. Oryginały są tylko czytane; wynik to nowy plik. Projekt `.psimp` tylko wskazuje na PDF-y. |
| Czy jakość spada? | Nie — wynik jest wektorowy; zdjęcia zachowują swoje piksele. Preflight ostrzega o niskim DPI. |
| Co, gdy plik nie ma spadu? | Program nie wymyśla grafiki — pokaże to w preflight. Narzędzie „Dodaj spady” może dorobić spad z krawędzi strony. |
| Czy działa z offsetem? | Tak: odwracanie przez markę boczną i czołową, rozmiar płyty, chwyt, margines „na łapki”, pasery, pasek kontrolny. |
| A druk cyfrowy dwustronny? | Tak, z kalibracją: arkusz testowy, pomiar, profil maszyny zapamiętywany na stałe. |
| Ile to kosztuje / jaka licencja? | Program jest bezpłatny; licencja otwartoźródłowa — do ustalenia przed szerszym udostępnieniem. *(Sprawdź aktualny stan przed pokazem.)* |
| Jak się aktualizuje? | Sam sprawdza GitHub przy starcie; jedno kliknięcie „Zaktualizuj teraz”; pobrany instalator jest weryfikowany sumą SHA-256. |
| Czy działa na Macu / Linuksie? | Wydania są na Windows 10/11. Kod jest w Pythonie i testy przechodzą też na Linuksie, ale instalatora dla innych systemów nie ma. |
| Czy jest bezpieczny? | Działa lokalnie, niczego nie wysyła; jedyne połączenie to sprawdzenie aktualizacji. Bez podpisu cyfrowego Windows może pokazać „Nieznany wydawca” — podpis jest przygotowany, potrzebny certyfikat. |
| Ile czasu to zajęło / ile kodu? | Ok. 11 tys. linii Pythona w programie, blisko 490 testów, ponad 25 wydań od wersji 0.1. |

---

## 8. Co dalej (plany — mów o nich jako o planach, nie o gotowych funkcjach)

- Montaż książek i broszur (świadomie odłożony).
- Numerowanie na arkuszu, wykrojnik zewnętrzny na podglądzie, kody CODE128 / EAN-128.
- Kreator podziału arkusza (2×, 3× DL), własne szerokości kolumn, użytek wieloarkuszowy.
- Podpis cyfrowy instalatora (certyfikat Code Signing).

---

## 9. Czego unikać podczas prezentacji

- Nie mów „zastępuje w 100 % program X” — część funkcji jest jeszcze w planach (rozdz. 8).
- Nie obiecuj druku bez próby — zawsze: „przed nakładem wydruk próbny”.
- Nie pokazuj plików prawdziwych klientów — używaj przykładów z `examples`.
- Nie wchodź w szczegóły kodu przy odbiorcy nietechnicznym — wystarczą punkty z rozdziału 3.

---

## 10. Materiały do pokazania

| Plik (folder `examples`) | Do czego |
|---|---|
| `crop_041_source_110x70.pdf` → `crop_041_sheet_SRA3.pdf` | Przed / po: plik klienta → arkusz SRA3 |
| `demo_montaz.psimp`, `demo_wizytowka_90x50.pdf` | Gotowy projekt podstawowej impozycji (plik 90 × 50 bez spadu — przy nim wybierz „Bez skalowania”) |
| `role_demo.psimp` (+ `role_demo_fronts.pdf`, `role_demo_shared_back.pdf`) | Druk dwustronny, wspólny tył |
| `economic_040_project.psimp`, `economic_040_plan.csv`, `economic_040_podglad.png` | Tryb ekonomiczny i raport |
| `duplex_037_320x450.pdf`, `kalibracja_036_nalozenie.png` | Arkusz testowy i kalibracja tyłu |
| `docs/interface-imp4-styl.png` | Zrzut okna (np. do slajdu) |
| https://github.com/Davidgracz/ukladex_tmp/releases | Strona wydań (pobranie, historia wersji) |
