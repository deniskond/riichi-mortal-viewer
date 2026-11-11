"""Fetch Mortal review reports from mjai.ekyu.moe.

The review itself must be submitted by the user in a browser (the form is
captcha protected). Once finished, the report JSON is public at
https://mjai.ekyu.moe/report/<id>.json. We accept any of:
  https://mjai.ekyu.moe/progress?task=<id>
  https://mjai.ekyu.moe/killerducky/?data=/report/<id>.json
  https://mjai.ekyu.moe/report/<id>.json
  <id>
  a local path to a saved report JSON
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

BASE = "https://mjai.ekyu.moe"
ID_RE = re.compile(r"(?:task=|/report/|^)([0-9a-f]{16})(?:\.json)?", re.I)


class ReportError(Exception):
    pass


def _ssl_context():
    # Use certifi's bundle: some Windows cert stores contain a malformed
    # certificate that breaks ssl.create_default_context().
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def report_id(src: str):
    m = ID_RE.search(src.strip())
    return m.group(1).lower() if m else None


def load_report(src: str, cache_dir: str = None):
    """Return (report_id, report_dict)."""
    src = src.strip()
    if os.path.isfile(src):
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        rid = report_id(os.path.basename(src)) or os.path.splitext(os.path.basename(src))[0]
        return rid, data

    rid = report_id(src)
    if not rid:
        raise ReportError(
            "Could not find a report id. Paste the mjai.ekyu.moe result URL "
            "(…/progress?task=<id> or …/killerducky/?data=/report/<id>.json).")

    if cache_dir:
        cached = os.path.join(cache_dir, f"{rid}.json")
        if os.path.isfile(cached):
            with open(cached, encoding="utf-8") as f:
                return rid, json.load(f)

    url = f"{BASE}/report/{rid}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mahjong-analyzer/0.1"})
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ReportError(
                f"Report {rid} not found. The review may still be running; "
                f"open {BASE}/progress?task={rid} and retry when it finishes.")
        raise ReportError(f"mjai.ekyu.moe returned HTTP {e.code} for {url}")
    except urllib.error.URLError as e:
        raise ReportError(f"Could not reach mjai.ekyu.moe: {e.reason}")

    data = json.loads(raw.decode("utf-8"))
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, f"{rid}.json"), "wb") as f:
            f.write(raw)
    return rid, data
