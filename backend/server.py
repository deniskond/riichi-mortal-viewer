"""HTTP API for the React viewer.

Run:  .venv\\Scripts\\python -m uvicorn server:app --port 8000 --reload
"""
from __future__ import annotations

import json
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mjanalyzer.__main__ import DATA, run
from mjanalyzer.report import ReportError, report_id

app = FastAPI(title="Mahjong analyzer")
ANALYSES = os.path.join(DATA, "analyses")


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
