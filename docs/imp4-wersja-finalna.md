# Jak działa wersja finalna Impozycjonera 4 — mapa funkcji i porównanie z Studio 0.4.1

Źródło: analiza statyczna instalacji Impozycjonera 4.0.4.0 (REA `inspect_managed_artifact`: zestaw 88 zasobów
programu, metadane kompletne) oraz własny odczyt tekstów okien, podpowiedzi i komunikatów z zasobów
`.resources` (2026-10-20). Program **nie był uruchamiany** — to opis interfejsu i reguł podanych w jego tekstach,
a nie obserwacja działania. Kod jest zaciemniony; ciał metod nie czytano i nie obchodzono zabezpieczeń.
Opis jest własnymi słowami; nazwy przycisków podano tylko jako odnośniki.

Legenda kolumny „Studio 0.4.1”: **jest** · **częściowo** · **brak** · **nowe** (dodane w tej wersji).

## 1. Okno główne i projekt

| Funkcja oryginału | Jak działa (z tekstów) | Studio 0.4.1 |
|---|---|---|
| Dwa moduły na wstędze | „Impozycja akcydensów” i „Impozycja książek i broszur”, każdy z własną tabelą użytków i przyciskiem WYKONAJ IMPOZYCJĘ | częściowo — tylko akcydensy (książki świadomie ukryte) |
| Nowa impozycja / wczytaj / zapisz / zapisz jako | Skróty Ctrl+N, Ctrl+W, Ctrl+S, Shift+Ctrl+S; Ctrl+O otwiera PDF | **nowe**: Ctrl+N, Ctrl+W, Shift+Ctrl+S (Ctrl+O i Ctrl+S już były) |
| Ustawienia | Okno z m.in. metadanymi wyniku (Tytuł/Autor/Temat/Słowa kluczowe, puste = nazwa pliku), dopiskiem `--IMPOZYCJONER`, wersją PDF (domyślnie 1.5), folderem MyImpozycjoner | **nowe**: metadane i dopisek; brak wersji PDF |
| Nazwa pliku wynikowego | Zakaz znaków `# % & * : < > ? / \ { }` i pionowej kreski; nie może być nazwą pliku przetwarzanego | **nowe** |
| Po impozycji otwórz | Przełączniki: otwórz ostatni plik / folder; podgląd JPG (72 ppi); „optymalizacja PDF” (funkcja testowa) | brak |
| Łączenie plików wynikowych | Wynik w jeden plik / w arkusze / każdy osobno i ich kombinacje | brak (zawsze jeden plik) |
| Zapis ustawień wstęgi jako domyślnych | Ustawienia wstęgi pamiętane przy starcie | częściowo — szablony prac |
| Reset do ustawień poinstalacyjnych | Z zachowaniem albo bez własnych papierów, płyt, kolorów, znaczników wycinarek | brak |

## 2. Montaż akcydensów

| Funkcja oryginału | Jak działa | Studio 0.4.1 |
|---|---|---|
| Użytek i obrót | Rozmiar poziomo/pionowo, obrót 0°/90°/180°; „Dodaj +180°” do zajętych i wolnych (z Shift — tylko zajętych), na aktywnym arkuszu albo wszystkich | jest (obrót), częściowo (+180° tylko w edytorze użytków) |
| Tabela K × W | Kolumny/wiersze; własna szerokość kolumn i wysokość wierszy; „pomiń krańcowe prawe/dolne, jeśli puste” | jest (K/W), brak (własne szerokości, pomijanie krańcowych) |
| Spady | Osobno L/P/G/D „dla obrotu 0°”; ostrzeżenie przy różnych spadach na arkuszu | częściowo — jeden spad na stronę |
| Arkusz | Papier, płyta, chwyt (domyślnie 11 mm), margines techniczny „na łapki”, redukcja rozmiaru płyty [pt]; relacja płyta > papier > PDF na podglądzie | częściowo — arkusz i marginesy |
| Rodzaj arkuszy | Jednostronny; dwustronny pełny/niepełny przez markę boczną (MB, work-and-turn) albo czołową (MC, work-and-tumble); falcowane (offset) / niefalcowane (cyfra) | częściowo — jedno-/dwustronnie (krawędź), ekonomiczny |
| Rozmiar wynikowego PDF | Papier / papier + chwyt / pole zadruku / pole zadruku + chwyt / płyta / rozmiar poddruku, każdy z ± ZMB; TrimBox bez zmian lub z korektą, spady 0 lub 3 mm | brak (PDF = arkusz) |
| Wiele arkuszy | Dodaj arkusz po zaznaczonym, usuń arkusz, usuń nieaktywne; arkusze aktywne/nieaktywne (Druk: TAK/NIE) | częściowo — arkusze wynikają z planu |
| Wykonaj impozycję | Wszystkich arkuszy / tylko aktywnego / wszystkich oprócz aktywnego; tryb makiety (podgląd uproszczony) | **nowe**: trzy tryby (pole „Wykonaj:” pod przyciskiem) |
| Kalkulator ilości arkuszy, „Rozmieść ekonomicznie” | Funkcja testowa; rozkład użytków prac o minimalnej liczbie impozycji | częściowo — tryb ekonomiczny (własny algorytm) |
| Kreator podziału arkusza | Podziel na 2×, na 3×DL, usuń podział | brak |
| Autowypełnianie, wypełnienie według wzoru | Z narożnika (LG/LD/PG/PD), centralnie; wzór pierwszego arkusza na kolejne | brak |
| Użytek wieloarkuszowy | Zmiany użytku dotyczą bieżącego arkusza albo wszystkich | brak |
| Przesunięcia P/NP | Przesunięcie środka strony parzystej/nieparzystej, symetrycznie albo niezależnie; „przesunięcie obrazu L<>P” | częściowo — przesunięcie verso X/Y (kalibracja) |
| Impozycja cząstkowa | Bez znaczników / znaczniki 1 mm / 2 mm | brak |
| Wykrojnik zewnętrzny | Plik PDF ze zmontowanym wykrojnikiem pokazywany na podglądzie | brak |

## 3. Tabela stron (menu prawego przycisku)

| Funkcja oryginału | Studio 0.4.1 |
|---|---|
| Zaznacz wszystkie / parzyste / nieparzyste / odwróć zaznaczenie | **nowe** |
| Zaznacz ujęte / nieujęte w impozycji, zaznacz takie same | brak |
| Znajdź pierwszy arkusz z tą stroną | **nowe** |
| Ustaw rozmiar użytka równy rozmiarom zaznaczonej strony | **nowe** (spad bez zmian, brutto idzie za netto) |
| Ustal rozmiar użytka na największą szerokość i wysokość w tabeli | brak |
| Koryguj odczytane rozmiary… (okno „Korekta położenia i rozmiaru obszaru netto”) | **nowe** — „Koryguj rozmiar strony (obszar netto)…”: podgląd z ramką do przesuwania, H × V i położenie, zakres ta strona / wszystkie / nieparzyste / parzyste, w pliku lub całej tabeli, tylko strony o tym samym rozmiarze, przywróć z pliku, ustaw rozmiar użytka; rozmiary skorygowane oznaczone w tabeli gwiazdką |
| Usuń zaznaczone wiersze (strony) | **nowe** jako „Pomiń zaznaczone strony” / „Przywróć” (rola Pomiń; PDF bez zmian) |
| Usuń wszystkie wiersze z pliku | **nowe** w menu (było: Delete) |
| Wstaw wakat przed/po/tutaj, usuń dodane wakaty | brak |
| Wstaw plik przed/po, zamień plik, zamień stronę na inną z pliku | brak |
| Kopiuj / wytnij / wklej, przesuń wiersz wyżej/niżej | częściowo — przesuwanie plików ↑↓ |
| Otwórz plik w czytniku PDF | **nowe** |
| Zapisz zaznaczone wiersze do pliku | brak |

## 4. Znaczniki (14 rodzajów)

W oryginale każdy rodzaj ma okno ustawień, prawy przycisk myszy włącza/wyłącza go, a pojedynczy klawisz jest
skrótem: netto **N**, brutto **B**, pasery **P**, pasery v2 **S**, paski kalibracyjne **K**, wycinka **W**,
marginesy **M**, docięcie TrimBox **T**, falcowanie **F**, opis **O**, własne **U**, wycinarki **C**, sygnatura
grzbietowa **G**, redukcja (creep) **R**. Ustawienia zapisuje się jako domyślne dla bieżącego zestawu (dwa zestawy);
jest też „Wyłącz wszystkie znaczniki”.

Reguły podane w tekstach: wycinka pionowa tylko przy parzystej liczbie kolumn; spady na krawędziach wycinki gdy
szerokość wycinki ≥ 2 × odstęp znaczników od użytków (i tylko dla spadu 0 mm oraz odstępu > 0); docięcie TrimBox to
„włos” z lewej na stronach parzystych i z prawej na nieparzystych; znaczniki falcowania dla arkuszy 8/12/16 stron.

**Studio 0.4.1:**

| Znacznik oryginału | Studio |
|---|---|
| Netto (N) | **jest** — znaczniki cięcia: odstęp od spadu, długości LP i GD (przełącznik GD=LP), grubość [pt], kolor (czarny jak dotąd / K 100 % / rejestracyjny), strony wszystkie/nieparzyste/parzyste, tylko pierwszy arkusz, „zaznaczaj narożniki” LG/PG/LD/PD (kreska obcinana do ½ wymiaru użytku), „zaznacz środek netto”, opcja Studio: bez kresek na sąsiednich użytkach; skrót **N**; bez dowolnego koloru z palety |
| Wycinka (W) | **nowe** — szerokość pionowa/pozioma, tylko przy parzystej liczbie kolumn/wierszy (inaczej uwaga w preflight i na pasku stanu), znacznik w osi o długości X albo przez całe pole zadruku, grubość [pt]; skrót **W**; bez paska kontrolnego i przycisków „Oblicz” |
| Docięcie TrimBox (T) | **nowe** — włos [pt] z lewej na stronach parzystych, z prawej na nieparzystych; skrót **T** |
| Marginesy (M) | częściowo — tylko „odstęp znaczników od użytków” (w parametrach linii cięcia); bez apli i reguły spadów przy wycince |
| „Wyłącz wszystkie znaczniki” | **nowe** |
| Brutto (B) | **nowe** — długości LP i GD, grubość, strony wszystkie/nieparzyste/parzyste, „tylko na pierwszym arkuszu”; skrót **B**; bez „zaznaczaj narożniki (kreska 2 mm)” |
| Pasery (P) | **nowe** — własne wzory: wariant 1 (okrąg z krzyżem) i 2 (dwa okręgi z krzyżem); średnica, grubość, liczba na dłuższym/krótszym boku, odsunięcie H automatyczne lub własne, narożne lub tylko wzdłuż boków, w narożnikach lub przy narożnikach; kolor 100 % CMYK; skrót **P**; bez wariantu 3 (wzór zewnętrznej firmy) i definicji koloru |
| Opis impozycji (O) | **nowe** — nazwa pliku wynikowego, „Arkusz N • Strona M” (słowa do zmiany, numeracja arabska/rzymska), pole zadruku, netto/brutto/spad, data i godzina, tekst dodatkowy; 10/12/14 pt, Arial/Courier; krawędź górna i/lub lewa; gdy się nie mieści — uwaga w preflight i na pasku stanu (jak komunikat oryginału); skrót **O**; bez opisu na wycinkach i oznaczeń kolorów |
| Pasek kontroli koloru (K) | **nowe** — 12 kostek K1–K12 (C/M/Y/K %, puste = brak; co najmniej jedna z kolorem), szerokość i wysokość kostki, ilość stref, odsunięcie, góra / dół / wycinka pozioma, pełna długość pola zadruku albo minus X, wyśrodkowany albo od lewej, pasek z pliku PDF; uwaga, gdy się nie mieści; opis arkusza przesuwa się nad pasek; skrót **K**; bez zapisu definicji do pliku `*.impc` (format oryginału nieznany — kolory zapisują się w projekcie) i bez kostek dolnych z generatora pasków |
| Pozostałe (S, F, U, C, G, R) | brak |

Kliknięcie przycisku znacznika przełącza go (jak dotąd w Studio); **prawy przycisk otwiera parametry** — w oryginale
role przycisków są odwrotne (klik = definicje, prawy = włącz/wyłącz). Parametry zapisują się w projekcie `.psimp`
(nowe pola są opcjonalne; stare projekty wczytują się z wartościami domyślnymi = wynik bez zmian).

## 5. Programy dodatkowe

| Program oryginału | Studio 0.4.1 |
|---|---|
| Rozetnij strony PDF (kolumny × wiersze, zakładki) / rozetnij rozkładówki | brak (jest „Rozdziel na pojedyncze strony” — strona = plik) |
| Wydziel strony; wydziel zakresy stron | **nowe** (zakres, każda osobno, plik bez wydzielonych, parzyste/nieparzyste, okładka i wkład, po N stron) |
| Połącz pliki PDF | **nowe** |
| Obróć strony | **nowe** (kąt, zakres, +180° dla parzystych; bez „obrotów z czytnika”) |
| Powiel strony | **nowe** |
| Tasuj strony/kartki | **nowe** (1,2,3,4 → 4,3,2,1 lub 3,4,1,2 — przykłady z oryginału) |
| Generator kodów EAN-13/EAN-8 | **nowe** (wektorowo; oryginał tworzy adnotacje) |
| Generator kodów EAN-13 v2, EAN-128, CODE128, QR | brak |
| Skaluj strony, dodaj spady, przenumeruj strony, wstaw strony, spłaszcz formularze | brak (skalowanie istnieje tylko w montażu) |
| Bitmapy ↔ PDF, rasteryzacja RGB | brak |
| Znaczniki falcowania, znaczniki dla ploterów tnących, oczka banerów | brak |
| Nałóż strony PDF (3 wersje), generator pasków densytometrycznych, kreator kalendarzy | brak |
| Ponumeruj pliki PDF w folderze, zmiana nazw | brak |

## 5a. Skalowanie, kadrowanie i spady — jak to robi wersja finalna

Źródła: teksty okien (E1) oraz metadane wywołań biblioteki PDF w klasach tych okien (REA
`inspect_managed_members`, tylko nazwy wywoływanych metod bibliotek zewnętrznych; ciał zaciemnionych metod nie czytano).

| Narzędzie oryginału | Jak działa | Studio |
|---|---|---|
| **Skaluj (zmień rozmiar) strony** | Do wymiarów w mm albo procentowo; każdy wymiar „określony” albo „proporcjonalny”; skaluje się rozmiar TrimBox albo MediaBox; nowa strona „jak po przeskalowaniu” albo o podanym rozmiarze z wyśrodkowaniem; zakres stron. Strona jest wstawiana jako obszar o nowej szerokości/wysokości (wywołania `ImportedPageArea` + `Width/Height`), wymiary strony ustawiane wprost. | **nowe** — program „Skaluj strony” (bez „optymalizacji PDF”) |
| **Dodaj spady** | Dla każdej krawędzi L/P/G/D: dodawany spad, szerokość wycinka, odległość wycinka od krawędzi PDF (MediaBox); spady nad albo pod stroną; podgląd z granicą TrimBox. Ta sama strona wstawiana wielokrotnie (28 obszarów), każdy przycięty z czterech stron (`ClipLeft/Right/Top/Bottom`) i ustawiony na zadany wymiar — wycinek krawędzi jest **rozciągany** na spad (brak śladów odbicia lustrzanego). | **nowe** — program „Dodaj spady” |
| **Korekta położenia i rozmiaru obszaru netto** | Ręczne przesuwanie/zmiana ramki netto na podglądzie strony, zakres: wybrana strona / wszystkie / parzyste / nieparzyste, w pliku lub całej tabeli; „kadruj do netto” albo „do brutto = netto + 3 mm” i zapis do pliku. | częściowo — „Kadruj PDF…” (przesunięcie kadru X/Y dla pliku, tryb Kadruj 1:1) |
| Automatyczne wykrywanie białych marginesów | **brak w oryginale** | **nowe (rozszerzenie Studio)** — „przytnij białe marginesy źródła” |
| Montaż z dopasowaniem do netto + spad | Oryginał skaluje osobnym narzędziem, a w montażu używa TrimBox | **nowe (rozszerzenie Studio)** — tryb „Wypełnij ze spadem” |

**Przepis A4 → A6 + 1,5 mm (Studio):** szablon „Ulotka A6 + 1,5 mm z A4 (bez białych marginesów) — SRA3” albo ręcznie:
netto 105 × 148, spad 1,5, *Kadrowanie PDF → Wypełnij ze spadem* i *przytnij białe marginesy źródła*. Grafika (po
odcięciu białej ramki) pokrywa cały użytek 108 × 151 mm; różnica proporcji jest docinana równo z obu stron.
Pojedyncze strony A6 ze spadem: „Eksportuj pojedyncze strony” z tymi samymi ustawieniami.
Wariant jak w oryginale (bez zmiany skali grafiki): „Dodaj spady” z odległością wycinka = szerokość białej ramki.

## 6. Decyzje własne przy nowych funkcjach (hipotezy — do sprawdzenia na działającym oryginale)

| ID | Decyzja |
|---|---|
| H-13 | Zakres stron: wynik rosnąco, bez powtórzeń; spacje dozwolone; strona spoza dokumentu = błąd. |
| H-14 | Powielanie: każda wskazana strona N razy pod rząd, w miejscu oryginału. |
| H-15 | Dopisek `--XX`: co najmniej 2 cyfry z zerami (3 cyfry od 100 stron). |
| H-16 | Nazwy plików narzędzia „Wydziel”: `--wydzielone`, `--bez_wydzielonych`, `--parzyste`, `--nieparzyste`, `--okladka`, `--wklad`; części `--XX`. |
| H-17 | Okładka = strony 1, 2, przedostatnia i ostatnia. |
| H-18 | Obrót z narzędzia dodaje się do bieżącego obrotu strony. |
| H-19 | Nazwa wyniku porównywana z wejściem bez katalogu i bez wielkości liter. |
| H-20 | Kody EAN jako wektory; błędne wiersze pliku tekstowego pomijane i raportowane. |
| H-22 | Wycinka zastępuje odstęp między środkowymi kolumnami (wierszami); automatyczna siatka bierze największą liczbę kolumn mieszczącą się z wycinką — może wyjść liczba nieparzysta, wtedy wycinki nie ma (z uwagą). |
| H-23 | Znacznik wycinki: linia w osi wycinki — dwa odcinki o zadanej długości od krawędzi pola zadruku albo, przy 0, przez całe pole zadruku. Nie przesuwa się z kalibracją verso. |
| H-24 | Docięcie TrimBox usuwa z tej krawędzi także spad (strona kończy się tuż za linią cięcia). Krawędź liczona w orientacji strony po jej obrocie /Rotate. |
| H-25 | Odstęp znaczników cięcia liczony od krawędzi spadu; domyślnie 0,8 mm (dotychczasowa wartość Studio). |
| H-26 | Białe marginesy: render 144 ppi, piksel jaśniejszy niż próg 250/255 = biały; obszar treści zmniejszony o 1 piksel (≈ 0,18 mm), żeby na krawędzi spadu nie został jasny pasek; pusta strona = cały TrimBox. |
| H-27 | „Dodaj spady”: wycinek [odległość, odległość + szerokość] rozciągany na pas od nowej krawędzi do początku wycinka (zakrywa biały margines przy spadach „nad stroną”); narożniki z narożnego kwadratu wycinków; TrimBox = TrimBox strony przesunięty o spad, BleedBox = MediaBox. Strony z zapisanym /Rotate są odrzucane z komunikatem. |
| H-29 | Znaczniki brutto na przedłużeniu krawędzi brutto, od narożnika na zewnątrz; części wchodzące na brutto innego użytku pomijane; „strony” = numer strony pliku wynikowego. |
| H-30 | Pasery: środek w odległości H + promień od obrysu brutto całej siatki arkusza (także pustych pól); H automatyczne = odstęp + długość linii cięcia + 1 mm; „X na boku” = liczba paserów równomiernie wzdłuż boku; paser na brutto użytku albo poza arkuszem pomijany; kolor 100 % C, M, Y, K. Nie przesuwa się z kalibracją verso. |
| H-31 | Opis: jedna linia nad siatką (krawędź górna) i/lub obrócona przy lewej krawędzi, czytana od dołu; stopień pisma maleje do 6 pt, potem opis jest pomijany z uwagą; numeracja rzymska dotyczy strony arkusza. |
| H-32 | Pasek kontroli: kostki z kolorem tworzą sekwencję powtarzaną na całej długości (tyle całych kostek, ile się mieści); „ilość stref” > 0 = tyle powtórzeń sekwencji; domyślne kolory K1–K12 nasze (C, M, Y, K, CM, CY, MY, CMY, 50 % C/M/Y/K). Pasek z PDF — jedna kopia w naturalnym rozmiarze. |
| H-33 | Pasek u góry nad znacznikami cięcia, u dołu pod nimi (odsunięcie od nich), na wycince poziomej w jej osi (gdy wycinka ≥ kostka + 2 × odsunięcie); długość liczona od pola zadruku (szerokość arkusza − 2 × margines X); brak miejsca = uwaga, pasek nie jest rysowany. |
| H-34 | „Zaznaczaj narożniki”: kreski leżą na linii cięcia (krawędź netto), od narożnika do środka użytku, nad grafiką; długość obcinana do ½ szerokości/wysokości (to z podpowiedzi oryginału). |
| H-35 | „Zaznacz środek netto”: kreski w połowie każdej krawędzi netto, na zewnątrz, z tym samym odstępem i długościami LP/GD co znaczniki cięcia. |
| H-37 | „Obracaj strony do orientacji użytku” (rozszerzenie Studio): strona pozioma na pionowym użytku (i odwrotnie) dostaje dodatkowe +90° (tekst czytany od dołu do góry); prawie kwadratowe (różnica < 1 %) bez obrotu; w „Bez skalowania” strona obrócona o 90° też jest akceptowana; nie działa z „Kadruj 1:1” (jawny błąd). Każda strona wielostronicowego PDF jest skalowana osobno — mieszane formaty (A4/A3/A5/A6) trafiają na wspólny format użytku. |
| H-38 | Korekta rozmiaru strony (tabela stron → „Koryguj rozmiar strony…”, odpowiednik „Koryguj odczytane rozmiary…”): ramka netto w mm w widocznej orientacji strony, od lewego górnego rogu; „ten sam rozmiar” = obie krawędzie strony różnią się ≤ 0,5 mm; korekta zapisana w projekcie (`page_boxes` przy pliku), TrimBox ustawiany tylko w pamięci przy otwieraniu PDF. Bez „kadruj i zapisz do pliku” i bez zmiany rozmiaru ramki myszą (tylko przesuwanie). |
| H-39 | Zmiana rozmiaru zaznaczonych stron (**E3**: zrzuty działającego Impozycjonera od użytkownika, 2026-10-21 — wersja nowsza niż 4.0.4.0 w `G:\ukladex`, której zasoby tych okien nie zawierają): w tabeli stron „Zmień parametry w zaznaczonych wierszach” Szerokość/Wysokość 108 × 151 skaluje strony A4 i A6 do 108 × 151 i tak trafiają na arkusz (użytek 105 × 148 + spad 1,5). Opcje z okna „Automatyczna konwersja bitmap do PDF”: niezależnie (+ kadrowanie), tylko szerokość, tylko wysokość, nowa szerokość i wysokość TrimBox, zachowaj orientację, definiuj spad. Nasze decyzje: skalowany jest obszar TrimBox (rozciągnięcie albo wycinek o proporcjach celu ze środka), zachowanie orientacji tylko przy obu wymiarach, spad z grafiki źródła spoza TrimBox — bez dorabiania. Strona tworzona wektorowo w pamięci; plik na dysku bez zmian. |
| H-28 | „Wypełnij ze spadem”: skala = max(brutto/grafika) w obu osiach; spad zawsze z grafiki (ewentualny spad w źródle poza TrimBox jest pomijany); nadmiar przycinany do komórki brutto. |
| — | „Usuń zaznaczone wiersze” w Studio = rola Pomiń (strona zostaje w pliku i może wrócić). |
| — | „Wykonaj tylko aktywny arkusz” w trybie dwustronnym obejmuje recto i verso tego arkusza. |

## 7. Proponowana kolejność dalszych prac

1. ~~Znaczniki: wycinka, docięcie TrimBox~~ (zrobione). Dalej: znaczniki brutto, pasery, opis impozycji (nazwa pliku,
   arkusz, data), reguła spadów przy wycince i apla z okna Marginesy.
2. Rozmiar wynikowego PDF (papier/pole zadruku/płyta, chwyt) — wymaga modelu chwytu i płyty.
3. Wakaty w tabeli stron i wstawianie/zamiana plików.
4. Kody CODE128 i QR (normy publiczne), skalowanie, dodawanie spadów i wstawianie stron jako programy dodatkowe.
5. Do potwierdzenia na działającym oryginale (próbki wejście → wynik): MB/MC, algorytm kalkulatora, autowypełnianie.
