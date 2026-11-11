"""HTTP API for the React viewer.

Run:  .venv\\Scripts\\python -m uvicorn server:app --port 8000 --reload
"""
from __future__ import annotations

import json
import os
import shutil

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mjanalyzer.__main__ import DATA, REPO, run
from mjanalyzer.report import ReportError, report_id

app = FastAPI(title="Mahjong analyzer")
ANALYSES = os.path.join(DATA, "analyses")
SEED = os.path.join(REPO, "seed", "analyses")
FRONTEND = os.environ.get("FRONTEND_DIST") or os.path.join(REPO, "frontend", "dist")


def _seed_analyses() -> None:
    """Copy committed seed analyses into DATA (Render has no persistent disk)."""
    os.makedirs(ANALYSES, exist_ok=True)
    os.makedirs(os.path.join(DATA, "reports"), exist_ok=True)
    if not os.path.isdir(SEED):
        return
    for fn in os.listdir(SEED):
        dst = os.path.join(ANALYSES, fn)
        if fn.endswith(".json") and not os.path.exists(dst):
            shutil.copy2(os.path.join(SEED, fn), dst)


_seed_analyses()


class AnalyzeRequest(BaseModel):
    source: str


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        an = run(req.source)
    except ReportError as e:
        raise HTTPException(400, str(e))
    return {"id": an["id"]}


@app.get("/api/games")
def games():
    out = []
    if os.path.isdir(ANALYSES):
        files = [f for f in os.listdir(ANALYSES) if f.endswith(".json")]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(ANALYSES, f)), reverse=True)
        for fn in files:
            with open(os.path.join(ANALYSES, fn), encoding="utf-8") as f:
                an = json.load(f)
            pid = an["player_id"]
            scores = an.get("final_scores") or [0, 0, 0, 0]
            place = 1 + sum(1 for s in scores if s > scores[pid])
            out.append({"id": an["id"], "rule": an["rule"], "rating": an["rating"],
                        "matches": an["total_matches"], "reviewed": an["total_reviewed"],
                        "mistakes": an["mistake_counts"], "place": place,
                        "score": scores[pid]})
    return out


@app.get("/api/games/{gid}")
def game(gid: str):
    rid = report_id(gid)
    path = os.path.join(ANALYSES, f"{rid}.json")
    if not rid or not os.path.isfile(path):
        raise HTTPException(404, "Game not analyzed yet")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Serve the built React app (production). Mounted last so /api/* routes win.
# Skipped in local development, where Vite serves the frontend and proxies /api.
if os.path.isdir(FRONTEND):
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
