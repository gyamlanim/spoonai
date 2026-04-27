from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import json
import uuid
import pickle
import io

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import validate_keys
from app.core.safety import classify_prompt_safety
from app.graph.builder import build_graph
from app.utils.tracing import init_tables, create_run, complete_run, fail_run, trace_step

DB_PATH     = Path("spoon.db")
FRONTEND    = Path("frontend")
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

_graph = build_graph()

ALLOWED_SUFFIXES = {".txt", ".md", ".pdf"}


# ── DB setup ─────────────────────────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conv
            ON messages(conversation_id, timestamp)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                filetype TEXT NOT NULL,
                chunks INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    # Tracing tables live in the same DB but are managed by tracing.py
    init_tables()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_keys()
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Prevents duplicate expensive LLM calls per conversation and protects the
# production backend from concurrent multi-model pipeline executions.
active_conversations: set[str] = set()


# ── Request models ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    doc_id: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_text(content: bytes, suffix: str) -> str:
    if suffix == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(422, detail=f"PDF extraction failed: {e}")
    else:
        text = content.decode("utf-8", errors="replace")
    return text


def _load_rag_store(doc_id: str) -> list:
    path = UPLOADS_DIR / f"{doc_id}.pkl"
    if not path.exists():
        raise HTTPException(404, detail=f"Document not found: {doc_id}")
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        raise HTTPException(500, detail="Document store is corrupted or unreadable")


def _load_history(conn: sqlite3.Connection, conversation_id: str, turns: int = 5) -> str:
    cursor = conn.execute("""
        SELECT role, content FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (conversation_id, turns * 2))
    rows = list(reversed(cursor.fetchall()))
    if not rows:
        return ""
    lines = ["CONVERSATION HISTORY:"]
    for role, content in rows:
        lines.append(f"{'User' if role == 'user' else 'Assistant'}: {content}")
    return "\n".join(lines)


def _save_message(conn: sqlite3.Connection, conversation_id: str,
                  role: str, content: str, metadata: dict | None = None):
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, metadata_json) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, json.dumps(metadata) if metadata else None),
    )


def _build_analysis(state: dict) -> str:
    arbitration = state.get("arbitration_decision")
    clusters    = state.get("claim_clusters")
    if not arbitration or not clusters:
        return "spoon compared responses across three models and produced a unified answer."
    top = max(clusters.clusters, key=lambda c: c.support_count, default=None)
    if arbitration.route == "synthesis":
        return "All three models broadly agreed on the main claim. spoon synthesized their answers into one coherent response."
    majority = ", ".join(arbitration.majority_models)
    outlier  = arbitration.outlier_model or "one model"
    claim    = top.canonical_claim if top else "the main claim"
    return (
        f"{majority} agreed on \"{claim}\". "
        f"{outlier} offered a different perspective. "
        f"spoon's independent resolver evaluated both positions and selected the best-supported answer."
    )


def _format_response(query: str, state: dict, conversation_id: str,
                     rag_context: str = "", run_id: str = "") -> dict:
    final        = state.get("final_response")
    model_answers = state.get("model_answers") or []
    arbitration  = state.get("arbitration_decision")

    def answer_text(i):
        return model_answers[i].answer_text if i < len(model_answers) else ""

    return {
        "conversation_id": conversation_id,
        "run_id":          run_id,
        "final_answer":    final.final_answer if final else "",
        "analysis":        arbitration.reason if arbitration else _build_analysis(state),
        "route":           arbitration.route if arbitration else "",
        "supported_claims":   final.supported_claims if final else [],
        "unresolved_claims":  final.unresolved_claims if final else [],
        "original_responses": [
            {"model": "ChatGPT", "color": "gpt",    "answer": answer_text(0)},
            {"model": "Claude",  "color": "claude",  "answer": answer_text(1)},
            {"model": "Gemini",  "color": "gemini",  "answer": answer_text(2)},
        ],
        "trace": {
            "run_id":           run_id,
            "route":            arbitration.route if arbitration else "",
            "supported_claims": final.supported_claims if final else [],
            "rag_used":         bool(rag_context),
        },
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, detail=f"Unsupported file type '{suffix}'. Use .txt, .md, or .pdf.")

    content = await file.read()
    if not content:
        raise HTTPException(400, detail="Uploaded file is empty.")

    text = _extract_text(content, suffix)
    if not text.strip():
        raise HTTPException(400, detail="No readable text found in document.")

    from app.services.rag import build_store
    store = build_store(text)
    if not store:
        raise HTTPException(400, detail="Document produced no chunks after processing.")

    doc_id = str(uuid.uuid4())
    with open(UPLOADS_DIR / f"{doc_id}.pkl", "wb") as f:
        pickle.dump(store, f)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO documents (doc_id, filename, filetype, chunks) VALUES (?, ?, ?, ?)",
            (doc_id, file.filename, suffix, len(store)),
        )

    return {"doc_id": doc_id, "filename": file.filename, "chunks": len(store)}


_SAFETY_MESSAGES = {
    "self_harm": (
        "It sounds like you might be going through something really difficult, and I want you to know that support is available. "
        "Please reach out to the 988 Suicide & Crisis Lifeline by calling or texting 988 — they're available 24/7 and are there to help. "
        "If you're outside the US, the International Association for Suicide Prevention maintains a directory of crisis centres at https://www.iasp.info/resources/Crisis_Centres/. "
        "You don't have to go through this alone."
    ),
    "profanity": (
        "Hey — let's keep things respectful. Spoon is here to help with research, analysis, and knowledge work. "
        "Try rephrasing your question and I'll do my best to give you a great answer."
    ),
}

_DEFAULT_SAFETY_MESSAGE = (
    "This prompt couldn't be processed because it appears to violate our content policy. "
    "Please rephrase your question and try again."
)


@app.post("/api/query")
async def process_query(req: QueryRequest):
    # Guardrail #2 — classify prompt before touching the pipeline or memory
    safety = classify_prompt_safety(req.query)
    if not safety["is_allowed"]:
        category = safety["category"]
        raise HTTPException(
            status_code=400,
            detail={
                "error":      "unsafe_prompt",
                "category":   category,
                "reason":     safety["reason"],
                "confidence": safety["confidence"],
                "message":    _SAFETY_MESSAGES.get(category, _DEFAULT_SAFETY_MESSAGE),
            },
        )

    conversation_id = req.conversation_id or str(uuid.uuid4())

    if conversation_id in active_conversations:
        raise HTTPException(
            status_code=409,
            detail="A response is already being generated for this conversation. Please wait until it finishes.",
        )

    active_conversations.add(conversation_id)
    run_id = create_run(conversation_id, req.query, req.doc_id)

    try:
        # Load conversation history
        with trace_step(run_id, "load_history",
                        input_data={"conversation_id": conversation_id}) as trace:
            with sqlite3.connect(DB_PATH) as conn:
                history = _load_history(conn, conversation_id)
                _save_message(conn, conversation_id, "user", req.query)
            trace["output"] = {"turns_loaded": history.count("\n") if history else 0}

        initial: dict = {
            "user_query":           req.query,
            "run_id":               run_id,
            "conversation_history": history or None,
        }

        # Retrieve RAG context
        rag_context = ""
        if req.doc_id:
            with trace_step(run_id, "retrieve_rag",
                            input_data={"doc_id": req.doc_id, "query": req.query}) as trace:
                store = _load_rag_store(req.doc_id)
                from app.services.rag import rag_pipeline
                rag_context = rag_pipeline(req.query, store)
                initial["rag_context"] = rag_context or None
                trace["output"] = {"context_chars": len(rag_context),
                                   "context_preview": rag_context[:200]}

        state    = _graph.invoke(initial)
        response = _format_response(req.query, state, conversation_id, rag_context, run_id)

        with sqlite3.connect(DB_PATH) as conn:
            _save_message(conn, conversation_id, "assistant", response["final_answer"],
                          metadata={"route": response["route"], "run_id": run_id})
            conn.execute(
                "INSERT INTO queries (query, response) VALUES (?, ?)",
                (req.query, json.dumps(response)),
            )

        complete_run(run_id, response["final_answer"])
        return response

    except Exception as exc:
        fail_run(run_id, str(exc))
        raise

    finally:
        active_conversations.discard(conversation_id)


@app.get("/api/runs")
async def list_runs(limit: int = 20):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT id, conversation_id, user_prompt, status,
                   started_at, completed_at, total_duration_ms
            FROM runs ORDER BY started_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(404, detail=f"Run {run_id} not found")
        steps = conn.execute("""
            SELECT id, step_name, input_json, output_json, started_at, completed_at,
                   duration_ms, model_name, prompt_tokens, completion_tokens, total_tokens, error
            FROM run_steps WHERE run_id=? ORDER BY id ASC
        """, (run_id,)).fetchall()
        return {
            "run":   dict(run),
            "steps": [dict(s) for s in steps],
        }


@app.get("/api/history")
async def get_history():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT id, query, created_at FROM queries ORDER BY created_at DESC LIMIT 20"
        )
        return [{"id": r[0], "query": r[1], "created_at": r[2]} for r in cursor.fetchall()]


@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT role, content, timestamp FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """, (conversation_id,))
        return {
            "conversation_id": conversation_id,
            "messages": [{"role": r[0], "content": r[1], "timestamp": r[2]}
                         for r in cursor.fetchall()],
        }


app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(FRONTEND / "index.html"))
