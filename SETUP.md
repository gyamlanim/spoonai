# Spoon — Setup Guide

Live app: **https://web-production-a7e59.up.railway.app/**

> The admin dashboard (run traces, step-level logs) runs locally only and is not deployed.

---

## Prerequisites

- Python 3.12
- Git
- API keys for OpenAI, Anthropic, and Google Gemini

---

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/gyamlanim/spoon.git
cd spoon
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
```

**Mac / Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

On Apple Silicon Macs, prefix pip commands with `arch -arm64`:
```bash
arch -arm64 pip install -r requirements.txt
```

### 4. Add your API keys

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

Where to get them:
- **OpenAI** → https://platform.openai.com/api-keys
- **Anthropic** → https://console.anthropic.com/settings/keys
- **Gemini** → https://aistudio.google.com/apikey

### 5. Start the app

**Mac / Linux:**
```bash
uvicorn app.server:app --port 8000 --reload
```

**Apple Silicon:**
```bash
arch -arm64 .venv/bin/uvicorn app.server:app --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

---

## Admin dashboard (local only)

The admin dashboard shows pipeline run traces, step durations, token counts, and per-step inputs/outputs. It runs as a separate server and is not publicly deployed.

Open a second terminal and run:

**Mac / Linux:**
```bash
uvicorn app.admin:app --port 8001 --reload
```

**Apple Silicon:**
```bash
arch -arm64 .venv/bin/uvicorn app.admin:app --port 8001 --reload
```

Open **http://localhost:8001** in your browser.

> Both servers read from the same `spoon.db` file. The main app must be running and receiving queries for run data to appear in the admin dashboard.

---

## Document upload (RAG)

Spoon supports document upload for retrieval-augmented generation. Uploaded files are stored in the `uploads/` folder as pickle files.

Supported formats: `.txt`, `.md`, `.pdf`

To upload via the UI: click the paperclip icon (📎) in the chat input bar.

To upload via curl:
```bash
curl -F "file=@your_document.pdf" http://localhost:8000/api/upload
```

---

## Evaluation

To run the simulation-based evaluation (compares GPT, Claude, Gemini, and Spoon across 10 realistic prompts):

```bash
# Dry run — no API calls, free
python eval_simulation.py --dry-run

# Test with 3 real cases
python eval_simulation.py --limit 3

# Full evaluation — all 10 cases
python eval_simulation.py
```

Results are saved to `eval_results.csv` and `eval_results.json`.

---

## Deployment (Railway)

The app is already deployed at **https://web-production-b028c.up.railway.app/**

To redeploy after changes:

```bash
git add .
git commit -m "your message"
git push
```

Railway auto-deploys on push to `main`.

If deploying from scratch:

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select the `spoon` repo
3. Go to **Variables** and add:
   ```
   OPENAI_API_KEY=...
   ANTHROPIC_API_KEY=...
   GEMINI_API_KEY=...
   ```
4. Railway will build and deploy using the `Procfile`

> The admin dashboard should **not** be deployed publicly. Run it locally only.

---

## Common issues

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'numpy'` | Run `pip install numpy` inside the venv |
| `ValueError: Missing required environment variable` | Check your `.env` file has all three API keys with no extra spaces |
| `ImportError: incompatible architecture (arm64 vs x86_64)` | Prefix all commands with `arch -arm64` |
| Server shows old UI after code changes | Hard reload in browser: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** |
| `git push` rejected | Run `git pull --rebase origin main` first, then push |
