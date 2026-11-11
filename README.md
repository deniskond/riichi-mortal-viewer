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

## Deploy (Render, free plan)

One Docker web service serves both the API and the built frontend
(`Dockerfile` at the repo root: Node builds `frontend/dist`, then a Python image runs uvicorn).
Render redeploys on every push to the connected GitHub branch.

1. Sign up at https://render.com with GitHub.
2. **New → Web Service** → pick this repo → Render detects the `Dockerfile` → instance type **Free**.
   (Or **New → Blueprint**, which reads `render.yaml`.)
3. Open `https://<name>.onrender.com/`.

Free-plan limits:

- The service sleeps after ~15 min idle; the first request then takes ~30–60 s.
- No persistent disk: analyses created on Render are lost on every restart / redeploy.
- Public: anyone with the link can run Analyze and see the game list (including opponents' nicknames).

**Seed analyses** – to ship games with every deploy, copy `data/analyses/<id>.json`
(not `.mistakes.md`, not `data/reports/`) into `seed/analyses/`, commit and push.
On startup the server copies any seed file that is not already in the data folder.

Environment variables:

- `DATA_DIR` – data folder (default `<repo>/data`; the Docker image uses `/app/data`).
- `FRONTEND_DIST` – built frontend to serve at `/` (default `<repo>/frontend/dist`;
  if the folder does not exist, nothing is served at `/`, as in local development).

Production-like local run: `cd frontend; npm run build`, then start uvicorn and open
http://localhost:8000/. Or `docker build -t mahjong .; docker run -p 8000:8000 mahjong`.

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
