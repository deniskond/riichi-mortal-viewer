"""Replay a tenhou-format kyoku log into a list of board snapshots (frames).

Tenhou kyoku log layout (one entry of `log`):
  [0] [kyoku, honba, kyotaku]
  [1] start scores
  [2] dora indicators, [3] ura indicators
  [4 + 3p] haipai, [5 + 3p] draws, [6 + 3p] discards  for p in 0..3
  [16] result
Draw lists contain call strings ("c175116", "17p1717", "m39393939");
discard lists contain 60 (tsumogiri), "r<t>" (riichi), ankan "a" / kakan "k"
strings, and 0 placeholders after a daiminkan.
"""
from __future__ import annotations

import copy
import re

from .tiles import norm, sort_tiles, t2m

YAKU_EN = {
    "立直": "Riichi", "ダブル立直": "Double riichi", "一発": "Ippatsu",
    "門前清自摸和": "Menzen tsumo", "平和": "Pinfu", "断幺九": "Tanyao",
    "一盃口": "Iipeikou", "二盃口": "Ryanpeikou", "役牌 白": "Yakuhai (haku)",
    "役牌 發": "Yakuhai (hatsu)", "役牌 中": "Yakuhai (chun)",
    "自風 東": "Seat wind (E)", "自風 南": "Seat wind (S)",
    "自風 西": "Seat wind (W)", "自風 北": "Seat wind (N)",
    "場風 東": "Round wind (E)", "場風 南": "Round wind (S)",
    "場風 西": "Round wind (W)", "場風 北": "Round wind (N)",
    "ドラ": "Dora", "赤ドラ": "Aka dora", "裏ドラ": "Ura dora",
    "嶺上開花": "Rinshan kaihou", "槍槓": "Chankan", "海底摸月": "Haitei",
    "河底撈魚": "Houtei", "三色同順": "Sanshoku", "三色同刻": "Sanshoku doukou",
    "一気通貫": "Ittsu", "混全帯幺九": "Chanta", "純全帯幺九": "Junchan",
    "七対子": "Chiitoitsu", "対々和": "Toitoi", "三暗刻": "Sanankou",
    "三槓子": "Sankantsu", "混一色": "Honitsu", "清一色": "Chinitsu",
    "小三元": "Shousangen", "混老頭": "Honroutou", "大三元": "Daisangen",
    "国士無双": "Kokushi", "四暗刻": "Suuankou", "字一色": "Tsuuiisou",
}

RESULT_EN = {
    "和了": "Win", "流局": "Exhaustive draw", "全員聴牌": "Draw (all tenpai)",
    "全員不聴": "Draw (all noten)", "流し満貫": "Nagashi mangan",
    "九種九牌": "Abort: nine terminals", "四風連打": "Abort: four winds",
    "四家立直": "Abort: four riichi", "三家和了": "Abort: triple ron",
    "四槓散了": "Abort: four kans",
}

CALL_RE = re.compile(r"[a-z]")


def _parse_call(s: str):
    """Return (letter, letter_index, called_tile_int, all_tile_ints)."""
    m = CALL_RE.search(s)
    letter, i = m.group(0), m.start()
    called = int(s[i + 1:i + 3])
    digits = s[:i] + s[i + 1:]
    tiles = [int(digits[j:j + 2]) for j in range(0, len(digits), 2)]
    return letter, i, called, tiles


def _call_source(letter: str, idx: int, caller: int) -> int:
    """Absolute seat the tile was called from."""
    if letter == "c":
        return (caller + 3) % 4
    if letter in "pk":
        return (caller + {0: 3, 2: 2, 4: 1}.get(idx, 1)) % 4
    if letter == "m":
        return (caller + {0: 3, 2: 2, 6: 1}.get(idx, 1)) % 4
    return caller


def _remove(hand: list, tile: int):
    if tile in hand:
        hand.remove(tile)
        return
    # tolerate red/non-red mismatch
    target = norm(t2m(tile))
    for h in hand:
        if norm(t2m(h)) == target:
            hand.remove(h)
            return
    raise ValueError(f"tile {tile} not in hand {hand}")


def _parse_result(res: list, names_en=None):
    if not res:
        return {"type": "unknown", "label": "?"}
    kind = res[0]
    out = {"type": "win" if kind == "和了" else "draw",
           "label": RESULT_EN.get(kind, kind), "raw": kind, "wins": [],
           "deltas": [0, 0, 0, 0]}
    rest = res[1:]
    if kind == "和了":
        # pairs of (deltas, info) - multiple for double ron
        for k in range(0, len(rest) - 1, 2):
            deltas, info = rest[k], rest[k + 1]
            out["deltas"] = [a + b for a, b in zip(out["deltas"], deltas)]
            who, frm = info[0], info[1]
            pts = info[3] if len(info) > 3 else ""
            yaku = []
            for y in info[4:]:
                m = re.match(r"(.+?)\((\d+)飜\)", y)
                if m:
                    yaku.append({"name": YAKU_EN.get(m.group(1), m.group(1)),
                                 "han": int(m.group(2))})
                else:
                    yaku.append({"name": YAKU_EN.get(y, y), "han": None})
            out["wins"].append({
                "winner": who, "from": frm, "tsumo": who == frm,
                "points": pts.replace("符", " fu ").replace("飜", " han ")
                             .replace("点", "").replace("満貫", "Mangan ")
                             .replace("跳満", "Haneman ").replace("倍満", "Baiman ")
                             .replace("三倍満", "Sanbaiman ").replace("役満", "Yakuman ")
                             .replace("∀", " all").strip(),
                "yaku": yaku,
            })
    else:
        if rest and isinstance(rest[0], list):
            out["deltas"] = rest[0]
    return out


def replay_kyoku(log: list) -> dict:
    (kyoku, honba, kyotaku), scores = log[0], list(log[1])
    dora_inds = [t2m(t) for t in log[2]]
    ura_inds = [t2m(t) for t in log[3]]
    hands = [list(log[4 + 3 * p]) for p in range(4)]
    draws = [log[5 + 3 * p] for p in range(4)]
    discs = [log[6 + 3 * p] for p in range(4)]
    result = _parse_result(log[16] if len(log) > 16 else [])

    oya = kyoku % 4
    melds = [[] for _ in range(4)]
    ponds = [[] for _ in range(4)]
    riichi = [False] * 4
    drawn = [None] * 4
    di, xi = [0] * 4, [0] * 4
    tiles_left = 70
    kans = 0
    frames = []

    def snap(event: dict):
        frames.append({
            "event": event,
            "tiles_left": tiles_left,
            "scores": list(scores),
            "kyotaku": kyotaku,
            "dora": dora_inds[:1 + kans],
            "riichi": list(riichi),
            "hands": [
                {"tiles": sort_tiles([t2m(t) for t in _without_drawn(hands[p], drawn[p])]),
                 "drawn": t2m(drawn[p]) if drawn[p] is not None else None}
                for p in range(4)
            ],
            "melds": copy.deepcopy(melds),
            "ponds": copy.deepcopy(ponds),
        })

    snap({"type": "start"})

    cur, need_draw, pending_riichi = oya, True, None
    while True:
        if need_draw:
            if di[cur] >= len(draws[cur]):
                break
            d = draws[cur][di[cur]]
            if isinstance(d, str):  # should not happen; desync guard
                break
            if pending_riichi is not None:
                scores[pending_riichi] -= 1000
                kyotaku += 1
                pending_riichi = None
            di[cur] += 1
            hands[cur].append(d)
            drawn[cur] = d
            tiles_left -= 1
            snap({"type": "draw", "actor": cur, "tile": t2m(d)})
        if xi[cur] >= len(discs[cur]):
            break
        x = discs[cur][xi[cur]]
        xi[cur] += 1

        if isinstance(x, str) and ("a" in x or "k" in x):
            letter, idx, called, tiles = _parse_call(x)
            if letter == "a":
                for t in tiles:
                    _remove(hands[cur], t)
                melds[cur].append({"type": "ankan", "tiles": [t2m(t) for t in tiles],
                                   "from": cur, "called_index": None})
            else:
                added = called
                _remove(hands[cur], added)
                for m in melds[cur]:
                    if m["type"] == "pon" and norm(m["tiles"][0]) == norm(t2m(added)):
                        m["type"] = "kakan"
                        m["tiles"].append(t2m(added))
                        break
            drawn[cur] = None
            kans += 1
            snap({"type": "ankan" if letter == "a" else "kakan", "actor": cur,
                  "tile": t2m(called)})
            need_draw = True
            continue
        if x == 0:
            continue

        is_riichi = isinstance(x, str) and x.startswith("r")
        if is_riichi:
            x = int(x[1:])
        tsumogiri = x == 60
        tile = drawn[cur] if tsumogiri else x
        _remove(hands[cur], tile)
        drawn[cur] = None
        if is_riichi:
            riichi[cur] = True
            pending_riichi = cur
        ponds[cur].append({"tile": t2m(tile), "tsumogiri": tsumogiri,
                           "riichi": is_riichi, "called": False})
        snap({"type": "discard", "actor": cur, "tile": t2m(tile),
              "tsumogiri": tsumogiri, "riichi": is_riichi})

        # Did anyone call this tile? pon/kan has priority over chi.
        caller = parsed = None
        for off in (1, 2, 3):
            q = (cur + off) % 4
            if di[q] < len(draws[q]) and isinstance(draws[q][di[q]], str):
                p = _parse_call(draws[q][di[q]])
                if p[0] in "pm" and _call_source(p[0], p[1], q) == cur \
                        and norm(t2m(p[2])) == norm(t2m(tile)):
                    caller, parsed = q, p
                    break
        if caller is None:
            q = (cur + 1) % 4
            if di[q] < len(draws[q]) and isinstance(draws[q][di[q]], str):
                p = _parse_call(draws[q][di[q]])
                if p[0] == "c" and norm(t2m(p[2])) == norm(t2m(tile)):
                    caller, parsed = q, p

        if caller is None:
            cur, need_draw = (cur + 1) % 4, True
            continue

        if pending_riichi is not None:
            scores[pending_riichi] -= 1000
            kyotaku += 1
            pending_riichi = None
        letter, idx, called, tiles = parsed
        di[caller] += 1
        consumed = list(tiles)
        consumed.remove(called)
        for t in consumed:
            _remove(hands[caller], t)
        ponds[cur][-1]["called"] = True
        mtype = {"c": "chi", "p": "pon", "m": "daiminkan"}[letter]
        melds[caller].append({"type": mtype,
                              "tiles": [t2m(called)] + [t2m(t) for t in consumed],
                              "from": cur, "called_index": 0})
        cur = caller
        if letter == "m":
            kans += 1
            if xi[caller] < len(discs[caller]) and discs[caller][xi[caller]] == 0:
                xi[caller] += 1
            need_draw = True
        else:
            need_draw = False
        snap({"type": mtype, "actor": caller, "tile": t2m(called), "from": frames[-1]["event"]["actor"]})

    final_scores = [s + d for s, d in zip(scores, result["deltas"])]
    end = dict(frames[-1])
    end = copy.deepcopy(end)
    end["event"] = {"type": "end", "result": result}
    end["scores_after"] = final_scores
    end["ura"] = ura_inds[:1 + kans] if any(
        any(y["name"] == "Riichi" or y["name"] == "Double riichi" for y in w["yaku"])
        for w in result.get("wins", [])) else []
    frames.append(end)

    return {
        "kyoku": kyoku, "honba": honba, "oya": oya,
        "label": f"{'ESWN'[kyoku // 4]}{kyoku % 4 + 1}" + (f"-{honba}" if honba else ""),
        "start_scores": list(log[1]),
        "result": result,
        "frames": frames,
    }


def _without_drawn(hand, drawn):
    h = list(hand)
    if drawn is not None and drawn in h:
        h.remove(drawn)
    return h
