"""Książka szyta ze składek — druk cyfrowy, kartki niefalcowane (H-56).

Czysta logika (bez PyMuPDF i interfejsu):
  • podział stron książki na składki — równo, bez bardzo cienkiej ostatniej składki,
  • kolejność stron na kartkach składki (kartka = 4 strony: 2 na przodzie, 2 na tyle; kartki złożone na pół
    i włożone jedna w drugą, szyte przez środek),
  • rozłożenie kartek na arkuszach, gdy na arkuszu mieści się kilka rozkładówek.

E1 (teksty okien Impozycjonera 4): moduł „Impozycja książek i broszur”, oprawa szyto-klejona, arkusze niefalcowane
(druk cyfrowy), okno „Rozkład stron na składkach niekompletnych” (ilość składek, stron w składce, arkuszy w składce),
kolejności „arkusz obok arkusza”, „w stosie”, „powielone”. Szczegóły algorytmów oryginału nie są znane — przyjęte
zasady opisuje H-56.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Sequence

ORDER_SEQUENTIAL = 'Kolejno (kartka obok kartki)'
ORDER_STACK = 'W stosie (tnij i ułóż)'
ORDER_REPEAT = 'Powielone (ta sama kartka)'
ORDERS = (ORDER_SEQUENTIAL, ORDER_STACK, ORDER_REPEAT)

MAX_LEAVES = 40          # kartek w jednej składce (160 stron) — powyżej szycie przez środek nie ma sensu


@dataclass(frozen=True)
class Folio:
    """Jedna kartka składki: strony w kolejności „jak widać” na każdej stronie kartki.

    front = (lewa, prawa) strona zewnętrzna kartki, back = (lewa, prawa) wewnętrzna — obie oglądane od swojej strony.
    signature — numer składki od 1; leaf — numer kartki w składce od 1 (1 = zewnętrzna).
    """
    front: tuple[Any, Any]
    back: tuple[Any, Any]
    signature: int
    leaf: int


def signature_leaves(pages: int, max_leaves: int) -> list[int]:
    """Liczba kartek w kolejnych składkach: najmniej składek, jak najrówniejszych (większe na początku).

    Np. 100 stron, najwyżej 4 kartki w składce → 25 kartek → 7 składek: 4, 4, 4, 4, 3, 3, 3 (16·4 + 12·3 = 100).
    """
    if type(max_leaves) is not int or not 1 <= max_leaves <= MAX_LEAVES:
        raise ValueError(f'Kartek w składce: 1–{MAX_LEAVES}')
    if pages < 1:
        raise ValueError('Brak stron książki')
    leaves = ceil(pages / 4)
    count = ceil(leaves / max_leaves)
    base, extra = divmod(leaves, count)
    return [base + 1] * extra + [base] * (count - extra)


def blank_pages(pages: int) -> int:
    """Puste strony dodawane na końcu książki do wielokrotności 4."""
    return (-pages) % 4


def folios(pages: Sequence[Any], max_leaves: int) -> list[Folio]:
    """Kartki całej książki, składka po składce; brakujące strony (do wielokrotności 4) puste (None) na końcu."""
    refs = list(pages) + [None] * blank_pages(len(pages))
    result: list[Folio] = []
    start = 0
    for number, leaves in enumerate(signature_leaves(len(pages), max_leaves), start=1):
        p = refs[start:start + 4 * leaves]
        n = len(p)
        for i in range(leaves):
            # Zewnętrzna strona kartki i: ostatnia | pierwsza; wewnętrzna: druga | przedostatnia (jak broszura).
            result.append(Folio((p[n - 1 - 2 * i], p[2 * i]), (p[2 * i + 1], p[n - 2 - 2 * i]), number, i + 1))
        start += 4 * leaves
    return result


def sheets(book: Sequence[Folio], cells: int, copies: int, order: str) -> list[list[Folio | None]]:
    """Kartki na kolejnych arkuszach (po `cells` rozkładówek na stronie arkusza); None = puste pole.

    • Kolejno — kartki książki po kolei, egzemplarz za egzemplarzem.
    • W stosie — dla każdego egzemplarza: pole k arkusza s dostaje kartkę k·S + s (S = liczba arkuszy). Po wydruku
      i cięciu stos z pola 1, pod nim stos z pola 2 itd. daje kartki po kolei.
    • Powielone — na arkuszu ta sama kartka w każdym polu (kolejne egzemplarze); stos z każdego pola po cięciu to
      cała książka. Ostatnia seria ma tylko tyle pól, ile brakuje egzemplarzy (bez nadprodukcji).
    """
    if cells < 1:
        raise ValueError('Na arkuszu nie mieści się ani jedna rozkładówka')
    if type(copies) is not int or copies < 1:
        raise ValueError('Nakład musi być >= 1')
    if order not in ORDERS:
        raise ValueError(f'Kolejność kartek: {", ".join(ORDERS)}')
    if not book:
        raise ValueError('Brak stron książki')
    result: list[list[Folio | None]] = []
    if order == ORDER_SEQUENTIAL:
        flow = list(book) * copies
        for i in range(0, len(flow), cells):
            chunk = flow[i:i + cells]
            result.append(chunk + [None] * (cells - len(chunk)))
    elif order == ORDER_STACK:
        count = ceil(len(book) / cells)
        for _ in range(copies):
            for s in range(count):
                result.append([book[k * count + s] if k * count + s < len(book) else None for k in range(cells)])
    else:
        for run in range(ceil(copies / cells)):
            used = min(cells, copies - run * cells)
            for folio in book:
                result.append([folio] * used + [None] * (cells - used))
    return result


def summary(pages: int, max_leaves: int) -> str:
    """Opis podziału na składki, np. „7 składek: 4 × 16 + 3 × 12 str. (+2 puste)”."""
    leaves = signature_leaves(pages, max_leaves)
    groups: dict[int, int] = {}
    for value in leaves:
        groups[value] = groups.get(value, 0) + 1
    parts = ' + '.join(f'{count} × {4 * value}' for value, count in sorted(groups.items(), reverse=True))
    word = 'składka' if len(leaves) == 1 else ('składki' if 2 <= len(leaves) % 10 <= 4 and not 12 <= len(leaves) % 100 <= 14
                                               else 'składek')
    extra = blank_pages(pages)
    return f'{len(leaves)} {word}: {parts} str.' + (f' (+{extra} puste na końcu)' if extra else '')
