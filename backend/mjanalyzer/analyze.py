"""Combine a Mortal review report with a replay of the game."""
from __future__ import annotations

from .efficiency import discard_table
from .replay import replay_kyoku
from .tiles import norm, pretty

# Severity is graded by how likely Mortal thought *your* move was.
SEVERITY_THRESHOLDS = [("major", 0.05), ("moderate", 0.20)]


def action_label(a: dict) -> str:
    t = a.get("type")
    if t == "dahai":
        return f"Discard {pretty(a['pai'])}" + (" (tsumogiri)" if a.get("tsumogiri") else "")
    if t == "reach":
        return "Riichi"
    if t == "none":
        return "Pass"
    if t in ("chi", "pon", "daiminkan"):
        cons = " ".join(pretty(c) for c in a.get("consumed", []))
        return f"{t.capitalize()} {pretty(a['pai'])} with {cons}"
    if t in ("ankan", "kakan"):
        return f"{t.capitalize()} {pretty(a.get('pai') or a.get('consumed', ['?'])[0])}"
    if t == "hora":
        return "Win (Ron/Tsumo)"
    if t == "ryukyoku":
        return "Abort (nine terminals)"
    return t or "?"


def action_kind(a: dict) -> str:
    t = a.get("type")
    if t in ("chi", "pon", "daiminkan", "none"):
        return "call"
    return {"dahai": "discard", "reach": "riichi"}.get(t, t or "?")


def _same(a: dict, b: dict) -> bool:
    keys = ("type", "pai", "consumed", "tsumogiri")
    return all(a.get(k) == b.get(k) for k in keys if k in a or k in b)


def _severity(is_equal: bool, actual_prob: float) -> str:
    if is_equal:
        return "ok"
    for name, th in SEVERITY_THRESHOLDS:
        if actual_prob < th:
            return name
    return "minor"


def _attach_efficiency(options, frame, pid):
    hand = frame["hands"][pid]
    tiles = hand["tiles"] + ([hand["drawn"]] if hand["drawn"] else [])
    if len(tiles) % 3 != 2:
        return
    visible = list(frame["dora"])
    for p in range(4):
        visible += [d["tile"] for d in frame["ponds"][p] if not d["called"]]
        for m in frame["melds"][p]:
            visible += m["tiles"]
    table = discard_table(tiles, len(frame["melds"][pid]), visible)
    for o in options:
        a = o["action"]
        if a.get("type") == "dahai":
            row = table.get(norm(a["pai"]))
            if row:
                o["shanten_after"] = row["shanten"]
                o["ukeire"] = row["ukeire"]
                o["accept"] = [t for t, _ in row["accept"]]


def _find_frame(frames, entry, pid):
    tl, actor = entry["tiles_left"], entry["last_actor"]
    want = ("draw", "chi", "pon", "daiminkan", "ankan", "kakan") if actor == pid \
        else ("discard", "kakan")
    best = None
    for i, f in enumerate(frames):
        ev = f["event"]
        if ev.get("actor") == actor and ev["type"] in want and f["tiles_left"] == tl:
            best = i
    return best


def analyze(report: dict, report_id: str = None) -> dict:
    pid = report["player_id"]
    rev = report["review"]
    logs = report["split_logs"]
    names = logs[0].get("name", ["P0", "P1", "P2", "P3"])

    kyokus, mistakes = [], []
    unmatched = 0
    for ki, (klog, krev) in enumerate(zip(logs, rev["kyokus"])):
        k = replay_kyoku(klog["log"][0])
        decisions = []
        for ei, e in enumerate(krev["entries"]):
            details = e.get("details", [])
            options = [{"action": d["action"], "label": action_label(d["action"]),
                        "prob": d.get("prob", 0.0), "q": d.get("q_value")}
                       for d in details]
            ai = e.get("actual_index")
            if ai is None:
                ai = next((i for i, o in enumerate(options) if _same(o["action"], e["actual"])), None)
            actual_prob = options[ai]["prob"] if ai is not None else 0.0
            actual_q = options[ai]["q"] if ai is not None else None
            best = options[0] if options else None
            q_loss = (best["q"] - actual_q) if best and actual_q is not None and best["q"] is not None else None
            fi = _find_frame(k["frames"], e, pid)
            if fi is None:
                unmatched += 1
            elif any(o["action"].get("type") == "dahai" for o in options):
                _attach_efficiency(options, k["frames"][fi], pid)
            sev = _severity(e["is_equal"], actual_prob)
            d = {
                "id": f"{ki}-{ei}",
                "kyoku_index": ki,
                "frame": fi,
                "junme": e["junme"],
                "tiles_left": e["tiles_left"],
                "kind": action_kind(e["expected"]) if action_kind(e["expected"]) != "call" else action_kind(e["actual"]),
                "actual": e["actual"], "actual_label": action_label(e["actual"]),
                "expected": e["expected"], "expected_label": action_label(e["expected"]),
                "is_equal": e["is_equal"],
                "actual_prob": actual_prob,
                "expected_prob": best["prob"] if best else None,
                "q_loss": q_loss,
                "severity": sev,
                # Mortal reports shanten before the draw; prefer our post-draw value.
                "shanten": min((o["shanten_after"] for o in options if "shanten_after" in o),
                               default=e.get("shanten")),
                "shanten_before_draw": e.get("shanten"),
                "furiten": e.get("at_furiten"),
                "options": options,
            }
            decisions.append(d)
            if sev != "ok":
                mistakes.append(d)
        k["decisions"] = decisions
        if ki < len(rev.get("relative_phi_matrix", [])):
            k["placement_probs"] = rev["relative_phi_matrix"][ki]
        kyokus.append(k)

    final_scores = kyokus[-1]["frames"][-1].get("scores_after") if kyokus else None
    counts = {s: sum(1 for m in mistakes if m["severity"] == s)
              for s in ("major", "moderate", "minor")}
    return {
        "id": report_id,
        "player_id": pid,
        "names": names,
        "dan": logs[0].get("dan"),
        "rate": logs[0].get("rate"),
        "rule": logs[0].get("rule", {}).get("disp"),
        "engine": report.get("engine"),
        "model_tag": rev.get("model_tag"),
        "rating": rev.get("rating"),
        "total_reviewed": rev.get("total_reviewed"),
        "total_matches": rev.get("total_matches"),
        "mistake_counts": counts,
        "final_scores": final_scores,
        "unmatched_decisions": unmatched,
        "kyokus": kyokus,
        "mistakes": [m["id"] for m in mistakes],
    }
