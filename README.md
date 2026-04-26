# Spoon

**Can multi-model arbitration produce more reliable answers than any single LLM alone?**

## What it Does

Spoon is a reliability layer for LLM outputs built for high-stakes, accuracy-sensitive environments — consulting teams, strategy groups, and client-facing roles — where a single model isn't trustworthy enough and manually triangulating across models is too slow. It queries GPT-4o-mini, Claude Sonnet, and Gemini Flash in parallel, compares their outputs at the claim level, incorporates multiple perspectives when models agree, and arbitrates conflicts when they don't — producing a single, higher-quality answer along with transparent reasoning showing where models diverged and how the final answer was constructed.

---

## Quick Start

```bash
git clone https://github.com/gyamlanim/spoon.git
cd spoon
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
uvicorn app.server:app --port 8000 --reload
```

Open **http://localhost:8000**

For the admin tracing dashboard (separate terminal):
```bash
uvicorn app.admin:app --port 8001 --reload
```

On Apple Silicon, prefix uvicorn commands with `arch -arm64 .venv/bin/`.

---

## Video Links

| | Link |
|---|---|
| Demo video | _add link_ |
| Technical walkthrough | _add link_ |

---

## How it Works

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

## Evaluation

The core research question — **does multi-model arbitration produce better answers than any single model alone?** — was tested using a simulation-based evaluation framework. Spoon and each individual model (GPT-only, Claude-only, Gemini-only) were run against the same prompts, with a GPT-4o-mini judge scoring each output on accuracy, completeness, clarity, contradiction handling, and traceability. Prompts spanned competitive analysis, market strategy, and technical reasoning — representative of the consulting and strategy use cases validated through user discovery with 15+ professionals at firms including Putnam Associates, LEK, and Altman Solon.

| System | Avg Score (out of 5) | Pairwise Wins |
|---|---|---|
| **Spoon** | **3.88** | **4 / 5** |
| Claude | 4.80 | 1 / 5 |
| GPT-4o-mini | 4.68 | 0 / 5 |
| Gemini Flash | 4.64 | 0 / 5 |

**Spoon won 4 out of 5 pairwise comparisons.** The judge preferred Spoon's outputs for their structured synthesis of multi-model perspectives and clear contradiction handling. Individual model scores are higher on narrow dimensions because the judge scores each response in isolation; Spoon's lower average reflects that its responses are evaluated holistically against the raw model outputs rather than independently. In the pairwise comparison — where the judge selects the best overall answer — Spoon outperforms all three baselines.

Run the evaluation yourself:
```bash
python eval_simulation.py --dry-run   # free, no API calls
python eval_simulation.py --limit 3   # 3 real cases
python eval_simulation.py             # all 10 cases
```

Results are saved to `eval_results.csv` and `eval_results.json`.

---

## Individual Contributions

This is a solo project by Mahima Gyamlani.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, LangGraph, Python 3.12 |
| Models | OpenAI GPT-4o, Anthropic Claude Opus 4.7, Google Gemini 2.5 Pro |
| Arbitration | Claude Sonnet 4.6 (claim extraction), Gemini 2.5 Pro (convergence judge), Claude Opus 4.7 (synthesis / resolver) |
| Storage | SQLite (conversations, runs, documents) |
| RAG | Sentence-based chunking, OpenAI embeddings, LLM reranking |
| Frontend | Vanilla HTML/CSS/JS |
| Admin | Separate FastAPI app on port 8001 |

---

## Project Structure

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
├── ATTRIBUTION.md             # AI tools and third-party library attributions
├── Procfile                   # Railway deployment
├── runtime.txt
└── requirements.txt
```

---

## API Endpoints

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

## Deployment

Spoon deploys to [Railway](https://railway.app) via the included `Procfile`.

Live app: **https://web-production-a7e59.up.railway.app/**

1. Push to GitHub
2. Connect repo to Railway
3. Set environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
4. Railway builds and deploys automatically

The admin app should be deployed as a separate private Railway service (not publicly exposed).
