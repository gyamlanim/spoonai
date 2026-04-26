# Spoon

Spoon is a multi-model AI answer arbitration system. It sends every user query to GPT-4o, Claude Sonnet, and Gemini Flash simultaneously, extracts claim-level outputs from each, compares agreement and disagreement, and produces one final higher-confidence answer.

---

## How it works

```
User query
    │
    ├─ GPT-4o-mini ─┐
    ├─ Claude Sonnet ├──► Extract claims ──► Cluster claims ──► Convergence judge
    └─ Gemini Flash ─┘                                               │
                                                           ┌─────────┴──────────┐
                                                      Converged?           Diverged?
                                                           │                    │
                                                       Synthesis        Independent Resolver
                                                           └─────────┬──────────┘
                                                                 Final answer
```

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, LangGraph, Python 3.12 |
| Models | OpenAI GPT-4o-mini, Anthropic Claude Sonnet 4.6, Google Gemini 2.5 Flash |
| Arbitration | Claude Haiku (claim extraction), Gemini (convergence judge), Claude Sonnet (synthesis / resolver) |
| Storage | SQLite (conversations, runs, documents) |
| RAG | Sentence-based chunking, OpenAI embeddings, LLM reranking |
| Frontend | Vanilla HTML/CSS/JS |
| Admin | Separate FastAPI app on port 8001 |

---

## Setup

**1. Clone and create virtual environment**

```bash
git clone https://github.com/gyamlanim/spoon.git
cd spoon
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Add API keys**

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

---

## Running locally

```bash
# User-facing app (port 8000)
uvicorn app.server:app --port 8000 --reload

# Admin dashboard (port 8001) — separate terminal
uvicorn app.admin:app --port 8001 --reload
```

- **App:** http://localhost:8000
- **Admin:** http://localhost:8001

On Apple Silicon, prefix with `arch -arm64`:

```bash
arch -arm64 .venv/bin/uvicorn app.server:app --port 8000 --reload
```

---

## Project structure

```
spoon/
├── app/
│   ├── core/
│   │   ├── config.py          # API key loading and validation
│   │   └── safety.py          # Input classifier and safety system prompt
│   ├── graph/
│   │   ├── builder.py         # LangGraph pipeline definition
│   │   └── state.py           # SpoonState TypedDict
│   ├── nodes/
│   │   ├── call_models.py     # Parallel GPT / Claude / Gemini calls
│   │   ├── extract_claims.py  # Claim extraction (Claude Haiku)
│   │   ├── cluster_claims.py  # Jaccard-based claim clustering
│   │   ├── score_support.py   # Convergence judge (Gemini)
│   │   ├── synthesis.py       # Synthesis when models agree (Claude)
│   │   ├── independent_resolver.py  # Resolver when models disagree (Claude)
│   │   └── final_answer.py    # Final response assembly
│   ├── prompts/
│   │   ├── base_answer.txt         # System prompt for model calls
│   │   ├── extract_claims.txt      # Claim extraction prompt
│   │   ├── convergence_judge.txt   # Convergence/divergence classifier prompt
│   │   ├── synthesis.txt           # Synthesis prompt
│   │   └── independent_resolver.txt # Arbitration prompt
│   ├── schemas/               # Pydantic models for all pipeline data
│   ├── services/
│   │   ├── model_clients.py   # GPT / Claude / Gemini API wrappers
│   │   └── rag.py             # Sentence chunking, embeddings, LLM reranking
│   ├── utils/
│   │   └── tracing.py         # Run and step-level observability (SQLite)
│   ├── server.py              # Main FastAPI app (port 8000)
│   ├── admin.py               # Admin FastAPI app (port 8001)
│   └── main.py                # run_spoon() entry point
├── frontend/
│   ├── index.html             # User-facing SPA
│   ├── admin.html             # Admin run-trace dashboard
│   └── static/
│       ├── app.js
│       └── style.css
├── eval_simulation.py         # Counterfactual replay evaluation
├── eval_cases.json            # 10 realistic evaluation prompts
├── Procfile                   # Railway deployment
├── runtime.txt
└── requirements.txt
```

---

## API endpoints

### User app (port 8000)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/query` | Run a query through the Spoon pipeline |
| `POST` | `/api/upload` | Upload a document for RAG context |
| `GET` | `/api/history` | Recent queries |
| `GET` | `/api/conversation/{id}` | Full conversation message history |

**Query request body:**
```json
{
  "query": "Compare LangGraph and AutoGen for bounded workflows.",
  "conversation_id": "optional-uuid",
  "doc_id": "optional-doc-uuid"
}
```

### Admin app (port 8001)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/runs` | List recent pipeline runs with status and duration |
| `GET` | `/api/runs/{run_id}` | Full run trace with per-step inputs, outputs, and token counts |

---

## Safety

Spoon has five safety layers:

1. **Pre-flight input classifier** — GPT-4o-mini classifies every prompt before touching the pipeline. Blocks hate, violence, self-harm, cyber abuse, illegal activity, explicit sexual content, safety bypass attempts. No educational exceptions.
2. **Safety system prompt** — Injected into every model call (GPT, Claude, Gemini) and both arbitration steps.
3. **Response-level detection** — Logs `safety_triggered: true/false` per step in the admin trace.
4. **Concurrency lock** — One active request per conversation. Returns 409 if a response is already in progress.
5. **Frontend guard** — Send button disabled and Enter key blocked while a response is loading.

---

## Evaluation

Spoon includes a simulation-based evaluation system using counterfactual replay and an LLM-as-a-judge.

```bash
# Dry run — no API calls, proves script structure
python eval_simulation.py --dry-run

# Run first 3 cases with real APIs
python eval_simulation.py --limit 3

# Full evaluation — all 10 cases
python eval_simulation.py
```

Each case is run through GPT-only, Claude-only, Gemini-only, and full Spoon. A GPT-4o-mini judge scores each output on accuracy, completeness, clarity, contradiction handling, and traceability. Results saved to `eval_results.csv` and `eval_results.json`.

---

## Deployment

Spoon deploys to [Railway](https://railway.app) via the included `Procfile`.

1. Push to GitHub
2. Connect repo to Railway
3. Set environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
4. Railway builds and deploys automatically

The admin app should be deployed as a separate private Railway service (not publicly exposed).
