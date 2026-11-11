"""CLI: python -m mjanalyzer <mjai.ekyu.moe result URL | report id | report.json>"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .analyze import analyze
from .describe import describe
from .report import ReportError, load_report

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


def run(src: str, data_dir: str = DATA) -> dict:
    rid, rep = load_report(src, cache_dir=os.path.join(data_dir, "reports"))
    an = analyze(rep, rid)
    out_dir = os.path.join(data_dir, "analyses")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{rid}.json"), "w", encoding="utf-8") as f:
        json.dump(an, f, ensure_ascii=False)
    with open(os.path.join(out_dir, f"{rid}.mistakes.md"), "w", encoding="utf-8") as f:
        f.write(describe(an))
    return an


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("--data", default=DATA)
    a = ap.parse_args()
    try:
        an = run(a.source, a.data)
    except ReportError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    rid = an["id"]
    print(f"Analyzed {rid}: {an['total_matches']}/{an['total_reviewed']} matches, "
          f"mistakes {an['mistake_counts']}, unmatched {an['unmatched_decisions']}")
    print(f"  {os.path.join(a.data, 'analyses', rid + '.json')}")
    print(f"  {os.path.join(a.data, 'analyses', rid + '.mistakes.md')}")


if __name__ == "__main__":
    main()
