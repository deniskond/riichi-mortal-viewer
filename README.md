# Mahjong analyzer

Reviews your riichi mahjong games with **Mortal** (via the public reviewer at
mjai.ekyu.moe), finds your mistakes, and replays the game in a web viewer.

## Workflow

1. Open https://mjai.ekyu.moe, paste a tenhou / Mahjong Soul log, choose Mortal and submit
   (the form has a captcha, so this step is manual).
2. Copy the result URL (`…/progress?task=<id>` or `…/killerducky/?data=/report/<id>.json`).
3. Paste it into the app (or the CLI).

## Run

```powershell
.\start.ps1            # backend on :8000 + frontend on :5173, opens the browser
```

CLI only (writes `data/analyses/<id>.json` and `<id>.mistakes.md`):

```powershell
cd backend
.\.venv\Scripts\python -m mjanalyzer "https://mjai.ekyu.moe/progress?task=<id>"
```

First-time setup:

```powershell
cd backend;  py -3.11 -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt
cd frontend; npm install
```

## Layout

- `backend/mjanalyzer/report.py` – fetch/cached Mortal report JSON
- `backend/mjanalyzer/replay.py` – tenhou log → board snapshots (frames)
- `backend/mjanalyzer/analyze.py` – attach Mortal decisions to frames, grade severity
- `backend/mjanalyzer/efficiency.py` – shanten / ukeire for each discard option
- `backend/mjanalyzer/describe.py` – text dump of mistakes with full context (for LLM/coach)
- `backend/server.py` – FastAPI: `POST /api/analyze`, `GET /api/games`, `GET /api/games/{id}`
- `frontend/` – React + Vite replay viewer

## Severity

Graded by Mortal's probability for the move you actually played:
`< 5%` big mistake · `< 20%` mistake · otherwise close call (any mismatch).

## Keyboard

← / → step · ↑ / ↓ previous/next own decision · PageUp / PageDown hand · `m` / `M` next/previous mistake
