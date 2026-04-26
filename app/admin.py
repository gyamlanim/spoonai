"""
Standalone admin server — runs on a separate port from the main spoon app.

Start with:
    arch -arm64 .venv/bin/uvicorn app.admin:app --port 8001 --reload

Reads from the same spoon.db but is completely decoupled from the user-facing app.
Do not expose port 8001 publicly in production.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.utils.tracing import init_tables

DB_PATH  = Path("spoon.db")
FRONTEND = Path("frontend")

# Ensure tracing tables exist (safe to call multiple times)
init_tables()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="spoon admin", lifespan=lifespan, docs_url=None, redoc_url=None)


# ── Data endpoints ────────────────────────────────────────────────────────────

@app.get("/api/runs")
def list_runs(limit: int = 100):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, conversation_id, user_prompt, doc_id, status,
                   started_at, completed_at, total_duration_ms, error
            FROM runs ORDER BY started_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(404, detail=f"Run {run_id} not found")
        steps = conn.execute("""
            SELECT id, step_name, input_json, output_json, started_at, completed_at,
                   duration_ms, model_name,
                   prompt_tokens, completion_tokens, total_tokens, error
            FROM run_steps WHERE run_id=? ORDER BY id ASC
        """, (run_id,)).fetchall()
        return {"run": dict(run), "steps": [dict(s) for s in steps]}


# ── Serve the dashboard ───────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")


@app.get("/")
def serve_dashboard():
    return FileResponse(str(FRONTEND / "admin.html"))
