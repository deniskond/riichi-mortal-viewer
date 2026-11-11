"""Render mistakes as a plain-text/markdown dump with full board context.

This is the hand-off to a human or an LLM coach: every mistake gets the
situation (scores, dora, hands, ponds, riichi state) and Mortal's options.
"""
from __future__ import annotations

from .tiles import dora_from_indicator, pretty

REL = {1: "Shimocha (right)", 2: "Toimen (across)", 3: "Kamicha (left)"}


def _tiles(ts):
    return " ".join(ts) if ts else "-"


def _pond(pond):
    out = []
    for d in pond:
        s = d["tile"]
        if d["riichi"]:
            s = f"[R]{s}"
        if d["tsumogiri"]:
            s += "'"
        if d["called"]:
            s = f"({s})"
        out.append(s)
    return " ".join(out) if out else "-"


def _melds(ms):
    return ", ".join(f"{m['type']}[{' '.join(m['tiles'])}]" for m in ms) or "none"


def describe_decision(an: dict, d: dict) -> str:
    pid = an["player_id"]
    k = an["kyokus"][d["kyoku_index"]]
    oya = k["oya"]
    lines = []
    head = (f"### {k['label']} · turn {d['junme']} · {d['tiles_left']} tiles left · "
            f"severity: {d['severity'].upper()}")
    lines.append(head)
    lines.append(f"- You played: **{d['actual_label']}** (Mortal prob {d['actual_prob']:.1%})")
    lines.append(f"- Mortal:     **{d['expected_label']}** (prob {d['expected_prob']:.1%})"
                 + (f", Q-loss {d['q_loss']:.3f}" if d["q_loss"] is not None else ""))
    top = [o for o in d["options"] if o["prob"] >= 0.01][:5]
    lines.append("- Options: " + "; ".join(
        f"{o['label']} {o['prob']:.1%} (Q {o['q']:.3f})" for o in top))
    shown = top + [o for o in d["options"] if o["label"] == d["actual_label"] and o not in top]
    for o in shown:
        if "ukeire" in o:
            lines.append(f"    - {o['label']}: shanten {o['shanten_after']}, ukeire {o['ukeire']} "
                         f"[{' '.join(o['accept'])}]")
    lines.append(f"- Shanten: {d['shanten']}" + (" · FURITEN" if d["furiten"] else ""))

    if d["frame"] is None:
        lines.append("- (board state unavailable)")
        return "\n".join(lines)
    f = k["frames"][d["frame"]]
    ev = f["event"]
    seat = "ESWN"[(pid - oya) % 4]
    lines.append(f"- Round wind {'ESWN'[k['kyoku'] // 4]}, your seat wind {seat}"
                 + (" (dealer)" if pid == oya else ""))
    lines.append(f"- Dora indicators: {_tiles(f['dora'])} -> dora "
                 f"{_tiles([dora_from_indicator(x) for x in f['dora']])}")
    sc = ", ".join(
        f"{'You' if p == pid else REL[(p - pid) % 4].split()[0]} {f['scores'][p]}"
        for p in range(4))
    lines.append(f"- Scores: {sc} · riichi sticks on table {f['kyotaku']}")
    if ev["type"] == "discard":
        lines.append(f"- Trigger: {REL[(ev['actor'] - pid) % 4]} discarded {pretty(ev['tile'])}")
    elif ev["type"] == "draw":
        lines.append(f"- Trigger: you drew {pretty(ev['tile'])}")
    else:
        lines.append(f"- Trigger: {ev['type']} {ev.get('tile', '')}")
    h = f["hands"][pid]
    lines.append(f"- Your hand: {_tiles(h['tiles'])}" + (f" + drew {h['drawn']}" if h["drawn"] else "")
                 + f" · melds: {_melds(f['melds'][pid])}")
    lines.append(f"- Your pond: {_pond(f['ponds'][pid])}")
    for off in (1, 2, 3):
        p = (pid + off) % 4
        tag = " **RIICHI**" if f["riichi"][p] else ""
        lines.append(f"- {REL[off]}{tag} · melds: {_melds(f['melds'][p])} · pond: {_pond(f['ponds'][p])}")
    return "\n".join(lines)


def describe(an: dict, severities=("major", "moderate", "minor")) -> str:
    pid = an["player_id"]
    out = [f"# Mortal review {an['id']} — {an['rule']} · model {an['model_tag']}",
           f"Player seat {pid} ({an['names'][pid]}). Agreement {an['total_matches']}/"
           f"{an['total_reviewed']} · rating {an['rating']:.3f} · mistakes {an['mistake_counts']}",
           f"Final scores: {an['final_scores']}",
           "Pond notation: [R]=riichi tile, '=tsumogiri, ()=called away.", ""]
    for k in an["kyokus"]:
        res = k["result"]
        rtxt = res["label"]
        for w in res.get("wins", []):
            who = "You" if w["winner"] == pid else f"seat {w['winner']}"
            rtxt += f" — {who} {'tsumo' if w['tsumo'] else 'ron from seat %d' % w['from']}: {w['points']}"
        ms = [d for d in k["decisions"] if d["severity"] in severities]
        out.append(f"## {k['label']} — {rtxt} — deltas {res['deltas']} — {len(ms)} mistakes")
        for d in ms:
            out.append(describe_decision(an, d))
            out.append("")
    return "\n".join(out)
