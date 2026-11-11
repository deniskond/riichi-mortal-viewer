"""Tile notation helpers.

Tenhou logs use integers (11-19 man, 21-29 pin, 31-39 sou, 41-47 honors,
51/52/53 red fives). Mortal/mjai uses strings ("1m", "5pr", "E", "P", ...).
Everything downstream of the replay uses mjai strings.
"""
from __future__ import annotations

HONORS = "ESWNPFC"  # East South West North, Haku(P) Hatsu(F) Chun(C)

HONOR_NAMES = {
    "E": "East", "S": "South", "W": "West", "N": "North",
    "P": "Haku", "F": "Hatsu", "C": "Chun",
}


def t2m(t: int) -> str:
    """Tenhou int -> mjai string."""
    if t in (51, 52, 53):
        return "5" + "mps"[t - 51] + "r"
    suit, num = divmod(t, 10)
    if suit == 4:
        return HONORS[num - 1]
    return f"{num}{'mps'[suit - 1]}"


def norm(tile: str) -> str:
    """Strip the red marker: '5mr' -> '5m'."""
    return tile[:-1] if tile.endswith("r") else tile


def sort_key(tile: str):
    if tile in HONORS:
        return (3, HONORS.index(tile), 0)
    suit = "mps".index(tile[1])
    num = int(tile[0])
    return (suit, num, 1 if tile.endswith("r") else 0)


def sort_tiles(tiles):
    return sorted(tiles, key=sort_key)


def dora_from_indicator(ind: str) -> str:
    t = norm(ind)
    if t in HONORS:
        i = HONORS.index(t)
        if i < 4:
            return HONORS[(i + 1) % 4]
        return HONORS[4 + (i - 4 + 1) % 3]
    n = int(t[0])
    return f"{n % 9 + 1}{t[1]}"


def pretty(tile: str) -> str:
    """Human label, e.g. '5pr' -> '5p(red)', 'P' -> 'Haku'."""
    if tile in HONOR_NAMES:
        return HONOR_NAMES[tile]
    return tile[:2] + ("(red)" if tile.endswith("r") else "")
