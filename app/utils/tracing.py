from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("spoon.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ms_since(started_at_iso: str) -> int:
    start = datetime.fromisoformat(started_at_iso)
    return int((datetime.now(timezone.utc) - start).total_seconds() * 1000)


def init_tables() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                user_prompt TEXT NOT NULL,
                doc_id TEXT,
                final_answer TEXT,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                total_duration_ms INTEGER,
                error TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                input_json TEXT,
                output_json TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                model_name TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                error TEXT,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_steps_run_id
            ON run_steps(run_id)
        """)


def create_run(conversation_id: str, user_prompt: str,
               doc_id: str | None = None) -> str:
    run_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO runs (id, conversation_id, user_prompt, doc_id, status, started_at)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (run_id, conversation_id, user_prompt, doc_id, _now()),
        )
    return run_id


def complete_run(run_id: str, final_answer: str) -> None:
    now = _now()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT started_at FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        duration_ms = _ms_since(row[0]) if row else None
        conn.execute(
            """UPDATE runs SET final_answer=?, status='completed',
               completed_at=?, total_duration_ms=? WHERE id=?""",
            (final_answer, now, duration_ms, run_id),
        )


def fail_run(run_id: str, error: str) -> None:
    now = _now()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT started_at FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        duration_ms = _ms_since(row[0]) if row else None
        conn.execute(
            """UPDATE runs SET status='failed', completed_at=?,
               total_duration_ms=?, error=? WHERE id=?""",
            (now, duration_ms, error, run_id),
        )


@contextmanager
def trace_step(
    run_id: str | None,
    step_name: str,
    input_data: dict | None = None,
    model_name: str | None = None,
):
    """
    Context manager that records a pipeline step into run_steps.

    Usage:
        with trace_step(run_id, "extract_claims", input_data={...}) as trace:
            result = do_work()
            trace["output"] = result
            trace["usage"] = {"prompt_tokens": ..., ...}   # optional
    """
    if not run_id:
        trace: dict = {}
        yield trace
        return

    started_at = _now()
    t0 = time.perf_counter()
    trace: dict = {}

    try:
        yield trace

        completed_at = _now()
        duration_ms = int((time.perf_counter() - t0) * 1000)
        usage = trace.get("usage", {})
        output = trace.get("output")

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO run_steps
                   (run_id, step_name, input_json, output_json, started_at,
                    completed_at, duration_ms, model_name,
                    prompt_tokens, completion_tokens, total_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id, step_name,
                    json.dumps(input_data, default=str) if input_data is not None else None,
                    json.dumps(output, default=str) if output is not None else None,
                    started_at, completed_at, duration_ms, model_name,
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    usage.get("total_tokens"),
                ),
            )

    except Exception as exc:
        completed_at = _now()
        duration_ms = int((time.perf_counter() - t0) * 1000)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO run_steps
                   (run_id, step_name, input_json, started_at,
                    completed_at, duration_ms, model_name, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id, step_name,
                    json.dumps(input_data, default=str) if input_data is not None else None,
                    started_at, completed_at, duration_ms, model_name, str(exc),
                ),
            )
        raise
