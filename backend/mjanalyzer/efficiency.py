"""Shanten and tile acceptance (ukeire) for discard options."""
from __future__ import annotations

from functools import lru_cache

from .tiles import HONORS, norm

TILE_NAMES = [f"{n}{s}" for s in "mps" for n in range(1, 10)] + list(HONORS)
IDX = {t: i for i, t in enumerate(TILE_NAMES)}


def to_counts(tiles):
    c = [0] * 34
    for t in tiles:
        c[IDX[norm(t)]] += 1
    return c


@lru_cache(maxsize=None)
def _regular(c: tuple, open_melds: int) -> int:
    counts = list(c)
    best = [8]
    limit = 4 - open_melds

    def dfs(i, m, t, head):
        while i < 34 and counts[i] == 0:
            i += 1
        if i >= 34:
            tt = min(t, limit - m)
            sh = 8 - 2 * (m + open_melds) - tt - head
            if sh < best[0]:
                best[0] = sh
            return
        # set: triplet
        if counts[i] >= 3 and m < limit:
            counts[i] -= 3; dfs(i, m + 1, t, head); counts[i] += 3
        # set: sequence
        if i < 27 and i % 9 <= 6 and counts[i + 1] and counts[i + 2] and m < limit:
            counts[i] -= 1; counts[i + 1] -= 1; counts[i + 2] -= 1
            dfs(i, m + 1, t, head)
            counts[i] += 1; counts[i + 1] += 1; counts[i + 2] += 1
        # head
        if counts[i] >= 2 and not head:
            counts[i] -= 2; dfs(i, m, t, 1); counts[i] += 2
        if m + t < limit:
            if counts[i] >= 2:
                counts[i] -= 2; dfs(i, m, t + 1, head); counts[i] += 2
            if i < 27 and i % 9 <= 7 and counts[i + 1]:
                counts[i] -= 1; counts[i + 1] -= 1; dfs(i, m, t + 1, head); counts[i] += 1; counts[i + 1] += 1
            if i < 27 and i % 9 <= 6 and counts[i + 2]:
                counts[i] -= 1; counts[i + 2] -= 1; dfs(i, m, t + 1, head); counts[i] += 1; counts[i + 2] += 1
        # leave tile isolated
        counts[i] -= 1; dfs(i, m, t, head); counts[i] += 1

    dfs(0, 0, 0, 0)
    return best[0]


def shanten(c, open_melds: int = 0) -> int:
    sh = _regular(tuple(c), open_melds)
    if open_melds == 0:
        pairs = sum(1 for x in c if x >= 2)
        kinds = sum(1 for x in c if x >= 1)
        chiitoi = 6 - pairs + max(0, 7 - kinds)
        terminals = [0, 8, 9, 17, 18, 26] + list(range(27, 34))
        k_kinds = sum(1 for i in terminals if c[i])
        k_pair = any(c[i] >= 2 for i in terminals)
        kokushi = 13 - k_kinds - (1 if k_pair else 0)
        sh = min(sh, chiitoi, kokushi)
    return sh


def ukeire(c, open_melds: int, visible):
    """Tiles that lower shanten of a 13-tile hand. visible: 34 counts seen elsewhere."""
    base = shanten(c, open_melds)
    out = []
    total = 0
    for i in range(34):
        left = 4 - c[i] - visible[i]
        if left <= 0:
            continue
        c[i] += 1
        if shanten(c, open_melds) < base:
            out.append((TILE_NAMES[i], left))
            total += left
        c[i] -= 1
    return base, total, out


def discard_table(hand14, open_melds: int, visible_tiles):
    """For each distinct discard of a 14-tile hand: (tile, shanten_after, ukeire, accept list)."""
    c = to_counts(hand14)
    vis = to_counts(visible_tiles)
    res = {}
    for i in range(34):
        if c[i] == 0:
            continue
        c[i] -= 1
        sh, total, acc = ukeire(c, open_melds, vis)
        c[i] += 1
        res[TILE_NAMES[i]] = {"shanten": sh, "ukeire": total, "accept": acc}
    return res
