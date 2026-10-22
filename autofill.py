"""Autowypełnianie arkusza — czysta logika (bez PyMuPDF i Tk).

Z okna „Autowypełnianie arkusza” Impozycjonera 4 (E1, własne streszczenie): wypełniaj stronami wszystkimi /
nieparzystymi / parzystymi; narożnik startowy siatki LG / PG / LD / PD i kierunek wypełniania wierszami albo
kolumnami; tryb „strony kolejno” albo „strony w stosie”; liczba powtórzeń każdej strony; strony parzyste po każdej
nieparzystej (N P N P) albo po wszystkich nieparzystych (N N N P P P). E2: jedno pole liczbowe (powtórzenia).

Decyzje własne (H-49): parzystość = numer strony w pliku PDF; „w stosie” = kolejne strony trafiają w to samo pole
na kolejnych arkuszach (po ułożeniu stosu arkuszy i cięciu stosy użytków mają kolejne strony); wakaty z tabeli
stron zachowują miejsce tylko przy „wszystkimi”. Ustawienia domyślne dają dotychczasowe wypełnianie.
"""
from __future__ import annotations

from math import ceil
from typing import Callable, Sequence, TypeVar

T = TypeVar('T')

PAGES_ALL = 'Wszystkimi'
PAGES_ODD = 'Nieparzystymi'
PAGES_EVEN = 'Parzystymi'
PAGE_CHOICES = (PAGES_ALL, PAGES_ODD, PAGES_EVEN)
CORNERS = ('LG', 'PG', 'LD', 'PD')   # lewy górny, prawy górny, lewy dolny, prawy dolny
MAX_REPEAT = 1000


def check(pages: str, corner: str, repeat: int):
    if pages not in PAGE_CHOICES:
        raise ValueError(f'Autowypełnianie: wypełniaj stronami {", ".join(PAGE_CHOICES).lower()}')
    if corner not in CORNERS:
        raise ValueError(f'Autowypełnianie: narożnik startowy {", ".join(CORNERS)}')
    if type(repeat) is not int or not 1 <= repeat <= MAX_REPEAT:
        raise ValueError(f'Autowypełnianie: ilość powtórzeń każdej strony 1–{MAX_REPEAT}')


def is_default(pages: str, corner: str, by_columns: bool, stack: bool, repeat: int, even_last: bool) -> bool:
    return (pages, corner, by_columns, stack, repeat, even_last) == (PAGES_ALL, 'LG', False, False, 1, False)


def slot_order(cells: Sequence[tuple[int, int]], corner: str, by_columns: bool) -> list[int]:
    """Kolejność pól siatki: indeksy `cells` [(kolumna, wiersz)] od narożnika startowego, wierszami/kolumnami."""
    if corner not in CORNERS:
        raise ValueError(f'Narożnik startowy: {", ".join(CORNERS)}')
    if not cells:
        return []
    max_col = max(c for c, _ in cells)
    max_row = max(r for _, r in cells)

    def key(index):
        col, row = cells[index]
        c = max_col - col if corner in ('PG', 'PD') else col
        r = max_row - row if corner in ('LD', 'PD') else row
        return (c, r) if by_columns else (r, c)
    return sorted(range(len(cells)), key=key)


def sequence(units: Sequence[T], page_number: Callable[[T], int | None], pages: str, even_last: bool,
             repeat: int) -> list[T]:
    """Kolejność stron do wypełnienia: wybór parzystości, parzyste na końcu, powtórzenia każdej strony."""
    check(pages, 'LG', repeat)
    chosen = list(units)
    if pages != PAGES_ALL:
        want = 1 if pages == PAGES_ODD else 0
        chosen = [u for u in chosen if page_number(u) is not None and page_number(u) % 2 == want]
    elif even_last:
        odd = [u for u in chosen if page_number(u) is None or page_number(u) % 2 == 1]
        even = [u for u in chosen if page_number(u) is not None and page_number(u) % 2 == 0]
        chosen = odd + even
    return [u for u in chosen for _ in range(repeat)]


def sheets(units: Sequence[T], capacity: int, stack: bool) -> list[list[T]]:
    """Podział na arkusze: kolejno (pełne arkusze po kolei) albo w stosie (pole k arkusza s = strona k·S + s)."""
    if capacity < 1:
        raise ValueError('Pojemność arkusza musi być co najmniej 1')
    units = list(units)
    if not units:
        return []
    if not stack:
        return [units[i:i + capacity] for i in range(0, len(units), capacity)]
    count = ceil(len(units) / capacity)
    return [[units[k * count + s] for k in range(capacity) if k * count + s < len(units)] for s in range(count)]
