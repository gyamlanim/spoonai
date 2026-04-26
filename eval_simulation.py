#!/usr/bin/env python3
"""
eval_simulation.py — Simulation-based evaluation for Spoon via counterfactual replay.

Core concept:
    The same realistic prompts are replayed through four systems:
        1. GPT-only baseline
        2. Claude-only baseline
        3. Gemini-only baseline
        4. Full Spoon pipeline (extraction → clustering → arbitration → final answer)

    An LLM-as-a-judge scores each output on a fixed rubric, and a pairwise judge
    ranks all four systems per case. This produces evidence that Spoon improves on
    single-model baselines in realistic consulting and research workflows.

Usage:
    python eval_simulation.py               # full run (all 10 cases)
    python eval_simulation.py --limit 3     # first 3 cases only
    python eval_simulation.py --dry-run     # no API calls, mocked outputs
    python eval_simulation.py --dry-run --limit 2
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────

EVAL_CASES_FILE = Path("eval_cases.json")
RESULTS_CSV     = Path("eval_results.csv")
RESULTS_JSON    = Path("eval_results.json")

# ── Neutral system prompt used for single-model baselines ─────────────────────

BASELINE_SYSTEM = (
    "You are a helpful research assistant. "
    "Answer the user's question clearly and accurately."
)

SYSTEMS = ["gpt", "claude", "gemini", "spoon"]

# ── Default eval cases (written to disk if eval_cases.json is missing) ────────

DEFAULT_CASES = [
    {"id": "case_001", "category": "competitive_analysis",
     "prompt": "Compare Perplexity, ChatGPT, Claude, and Gemini for enterprise research workflows. Identify where their value propositions overlap and differ."},
    {"id": "case_002", "category": "market_entry",
     "prompt": "A consulting team is evaluating whether a regional fast food chain should enter the breakfast market. What factors should they analyze?"},
    {"id": "case_003", "category": "startup_strategy",
     "prompt": "Summarize the key risks and opportunities for a startup building multi-model AI answer arbitration."},
    {"id": "case_004", "category": "market_sizing",
     "prompt": "Given three conflicting market-size estimates for the same product category, explain how you would reconcile them into one defensible estimate."},
    {"id": "case_005", "category": "buyer_personas",
     "prompt": "Identify likely buyer personas for a tool that compares GPT, Claude, and Gemini outputs for accuracy-sensitive work."},
    {"id": "case_006", "category": "competitive_landscape",
     "prompt": "Create a competitive landscape for AI research tools used by consultants and strategy teams."},
    {"id": "case_007", "category": "hypothesis_testing",
     "prompt": "Pressure-test this hypothesis: consulting teams will pay for verified LLM outputs if the tool saves time and improves confidence."},
    {"id": "case_008", "category": "go_to_market",
     "prompt": "Recommend an initial go-to-market strategy for Spoon targeting consulting firms."},
    {"id": "case_009", "category": "model_disagreement",
     "prompt": "Explain why model disagreement matters in high-stakes knowledge work."},
    {"id": "case_010", "category": "trust_and_traceability",
     "prompt": "Analyze how source attribution could increase trust in AI-generated consulting research."},
]

# ── Mock data for --dry-run ───────────────────────────────────────────────────

_MOCK_OUTPUTS = {
    "gpt":    "GPT mock response: A solid but generic answer covering the major points without deep analysis.",
    "claude": "Claude mock response: A well-structured answer with clear sections but limited contradiction handling.",
    "gemini": "Gemini mock response: A broad answer with some useful specifics but lacking traceability.",
    "spoon":  "Spoon mock response: A synthesized answer that reconciles model differences and clearly flags assumptions.",
}

_MOCK_SCORES = {
    "gpt":    {"accuracy": 3, "completeness": 3, "clarity": 4, "contradiction_handling": 2, "traceability": 2, "overall_score": 2.8, "strengths": "Clear structure", "weaknesses": "Generic", "explanation": "Mocked GPT score"},
    "claude": {"accuracy": 4, "completeness": 4, "clarity": 4, "contradiction_handling": 3, "traceability": 3, "overall_score": 3.6, "strengths": "Well structured", "weaknesses": "Mild hedging", "explanation": "Mocked Claude score"},
    "gemini": {"accuracy": 3, "completeness": 3, "clarity": 3, "contradiction_handling": 2, "traceability": 2, "overall_score": 2.6, "strengths": "Broad coverage", "weaknesses": "Shallow", "explanation": "Mocked Gemini score"},
    "spoon":  {"accuracy": 4, "completeness": 5, "clarity": 4, "contradiction_handling": 4, "traceability": 4, "overall_score": 4.2, "strengths": "Reconciles disagreement, flags assumptions", "weaknesses": "Slightly verbose", "explanation": "Mocked Spoon score"},
}

_MOCK_PAIRWISE = {
    "winner":  "spoon",
    "ranking": ["spoon", "claude", "gpt", "gemini"],
    "reason":  "Mocked pairwise: Spoon produced the most complete and traceable answer.",
}

# ── Load or create eval cases ─────────────────────────────────────────────────

def load_cases() -> list[dict]:
    if not EVAL_CASES_FILE.exists():
        print(f"eval_cases.json not found — creating with {len(DEFAULT_CASES)} default cases.")
        EVAL_CASES_FILE.write_text(json.dumps(DEFAULT_CASES, indent=2))
    with open(EVAL_CASES_FILE) as f:
        return json.load(f)

# ── Baseline runners ──────────────────────────────────────────────────────────

def run_gpt_baseline(prompt: str) -> str:
    from openai import OpenAI
    from app.core.config import OPENAI_API_KEY
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def run_claude_baseline(prompt: str) -> str:
    import anthropic
    from app.core.config import ANTHROPIC_API_KEY
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        system=BASELINE_SYSTEM,
        temperature=0,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def run_gemini_baseline(prompt: str) -> str:
    from google import genai
    from google.genai import types
    from app.core.config import GEMINI_API_KEY
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            system_instruction=BASELINE_SYSTEM,
        ),
    )
    return response.text.strip()


def run_spoon_pipeline(prompt: str) -> str:
    """Runs the full Spoon graph: model calls → extraction → clustering → arbitration → final answer."""
    from app.main import run_spoon
    result = run_spoon(prompt)
    return result.final_answer

# ── LLM-as-judge (individual scoring) ────────────────────────────────────────

_JUDGE_SYSTEM = """You are an impartial evaluator of AI-generated answers for high-stakes consulting and research workflows.

Evaluate the answer against the original user prompt. Use a 1 to 5 scale for each criterion.

Criteria:
1. accuracy: The answer is factually sound, avoids unsupported claims, and directly addresses the prompt.
2. completeness: The answer covers the major dimensions a strong consultant or strategy analyst would include.
3. clarity: The answer is structured, concise, and easy to understand.
4. contradiction_handling: The answer identifies uncertainty, tradeoffs, or conflicting assumptions when relevant.
5. traceability: The answer explains reasoning, assumptions, or sources enough that the user can validate the conclusion.

Return JSON only in this exact format with no markdown:
{"accuracy": 1, "completeness": 1, "clarity": 1, "contradiction_handling": 1, "traceability": 1, "overall_score": 1.0, "strengths": "...", "weaknesses": "...", "explanation": "..."}

Important rules:
- Do not favor Spoon because it is the target product.
- Judge only the answer quality.
- Penalize vague, generic, unsupported, or overconfident answers.
- Reward answers that clearly handle uncertainty and explain assumptions.
- Use the full 1 to 5 range.
- Return valid JSON only."""

_DEFAULT_SCORE = {
    "accuracy": 0, "completeness": 0, "clarity": 0,
    "contradiction_handling": 0, "traceability": 0,
    "overall_score": 0.0,
    "strengths": "", "weaknesses": "",
    "explanation": "judging failed",
}


def judge_output(prompt: str, model_name: str, output: str) -> dict:
    """Score a single system output using an LLM judge."""
    from openai import OpenAI
    from app.core.config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)
    user_msg = f"Original prompt: {prompt}\n\nSystem: {model_name}\n\nAnswer:\n{output}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=400,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        # Compute overall_score if missing or wrong
        dims = ["accuracy", "completeness", "clarity", "contradiction_handling", "traceability"]
        scores = [float(result.get(d, 0)) for d in dims]
        result["overall_score"] = round(mean(scores), 2)
        return result
    except Exception as exc:
        score = dict(_DEFAULT_SCORE)
        score["explanation"] = f"judging failed: {exc}"
        return score


# ── Pairwise judge ────────────────────────────────────────────────────────────

_PAIRWISE_SYSTEM = """You are an impartial evaluator comparing multiple AI systems answering the same prompt.

You will be given a prompt and four labeled answers (GPT, Claude, Gemini, Spoon). Your job is to:
1. Rank all four systems from best to worst for this prompt.
2. Pick the winner.
3. Briefly explain the ranking.

Rules:
- Do not favor any system by name or reputation.
- Base your decision entirely on answer quality: accuracy, completeness, clarity, handling of uncertainty, and traceability.
- Penalize generic or vague answers.

Return JSON only with no markdown:
{"winner": "spoon", "ranking": ["spoon", "claude", "gpt", "gemini"], "reason": "..."}"""


def judge_pairwise(prompt: str, outputs_by_system: dict) -> dict:
    """Compare all four system outputs side-by-side and return a ranking."""
    from openai import OpenAI
    from app.core.config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)
    sections = "\n\n".join(
        f"=== {name.upper()} ===\n{text}" for name, text in outputs_by_system.items()
    )
    user_msg = f"Prompt: {prompt}\n\n{sections}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=300,
            messages=[
                {"role": "system", "content": _PAIRWISE_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as exc:
        return {"winner": "unknown", "ranking": [], "reason": f"pairwise judging failed: {exc}"}


# ── Results persistence ───────────────────────────────────────────────────────

CSV_FIELDS = [
    "case_id", "category", "prompt", "system_name", "output",
    "accuracy", "completeness", "clarity", "contradiction_handling", "traceability",
    "overall_score", "strengths", "weaknesses", "explanation",
    "pairwise_winner", "pairwise_ranking", "pairwise_reason",
]


def save_results(all_results: list[dict]) -> None:
    # CSV — flat rows
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_results)
    print(f"\nSaved {len(all_results)} rows → {RESULTS_CSV}")

    # JSON — nested by case
    cases_map: dict[str, dict] = {}
    for row in all_results:
        cid = row["case_id"]
        if cid not in cases_map:
            cases_map[cid] = {
                "case_id": cid, "category": row["category"],
                "prompt": row["prompt"], "systems": {},
                "pairwise_winner": row["pairwise_winner"],
                "pairwise_ranking": row["pairwise_ranking"],
                "pairwise_reason": row["pairwise_reason"],
            }
        cases_map[cid]["systems"][row["system_name"]] = {
            "output": row["output"],
            "scores": {k: row[k] for k in ["accuracy", "completeness", "clarity",
                                            "contradiction_handling", "traceability",
                                            "overall_score", "strengths", "weaknesses",
                                            "explanation"]},
        }

    RESULTS_JSON.write_text(json.dumps(list(cases_map.values()), indent=2))
    print(f"Saved nested data  → {RESULTS_JSON}")


# ── Summary metrics ───────────────────────────────────────────────────────────

def print_summary(all_results: list[dict]) -> None:
    case_ids = sorted({r["case_id"] for r in all_results})
    n = len(case_ids)

    avg: dict[str, float] = {}
    for sys in SYSTEMS:
        scores = [r["overall_score"] for r in all_results
                  if r["system_name"] == sys and isinstance(r["overall_score"], (int, float))]
        avg[sys] = round(mean(scores), 2) if scores else 0.0

    pairwise_wins   = sum(1 for r in all_results if r["system_name"] == "spoon"
                          and r["pairwise_winner"] == "spoon")
    win_rate        = pairwise_wins / n if n else 0

    spoon_beats     = 0
    for cid in case_ids:
        rows = {r["system_name"]: r["overall_score"] for r in all_results if r["case_id"] == cid}
        best_baseline = max(rows.get("gpt", 0), rows.get("claude", 0), rows.get("gemini", 0))
        if rows.get("spoon", 0) > best_baseline:
            spoon_beats += 1

    spoon_rows = [r for r in all_results if r["system_name"] == "spoon"
                  and isinstance(r["overall_score"], (int, float))]
    strongest  = max(spoon_rows, key=lambda r: r["overall_score"], default=None)
    weakest    = min(spoon_rows, key=lambda r: r["overall_score"], default=None)

    bar = "=" * 60
    print(f"\n{bar}")
    print("EVALUATION SUMMARY")
    print(bar)
    print(f"Cases evaluated        : {n}")
    print(f"Avg score — GPT        : {avg['gpt']}")
    print(f"Avg score — Claude     : {avg['claude']}")
    print(f"Avg score — Gemini     : {avg['gemini']}")
    print(f"Avg score — Spoon      : {avg['spoon']}")
    print(f"Spoon pairwise wins    : {pairwise_wins} / {n}  ({win_rate:.0%})")
    print(f"Spoon beats best baseline (independent score): {spoon_beats} / {n}")
    if strongest:
        print(f"Strongest Spoon case   : {strongest['case_id']} ({strongest['category']}) — {strongest['overall_score']}")
    if weakest:
        print(f"Weakest Spoon case     : {weakest['case_id']} ({weakest['category']}) — {weakest['overall_score']}")
    print(bar)


# ── Main evaluation loop ──────────────────────────────────────────────────────

def run_evaluation(cases: list[dict], dry_run: bool = False) -> list[dict]:
    runners = {
        "gpt":    (lambda p: _MOCK_OUTPUTS["gpt"])    if dry_run else run_gpt_baseline,
        "claude": (lambda p: _MOCK_OUTPUTS["claude"]) if dry_run else run_claude_baseline,
        "gemini": (lambda p: _MOCK_OUTPUTS["gemini"]) if dry_run else run_gemini_baseline,
        "spoon":  (lambda p: _MOCK_OUTPUTS["spoon"])  if dry_run else run_spoon_pipeline,
    }

    all_results: list[dict] = []

    for case in cases:
        cid      = case["id"]
        category = case["category"]
        prompt   = case["prompt"]
        print(f"\nRunning {cid} [{category}] ...")

        # ── Collect outputs ──────────────────────────────────────────────────
        outputs: dict[str, str] = {}
        for sys in SYSTEMS:
            print(f"  Calling {sys} ...")
            try:
                outputs[sys] = runners[sys](prompt)
            except Exception as exc:
                outputs[sys] = f"ERROR: {exc}"
                print(f"  ⚠  {sys} failed: {exc}")

        # ── Score each output ────────────────────────────────────────────────
        scores: dict[str, dict] = {}
        for sys in SYSTEMS:
            print(f"  Scoring {sys} output ...")
            if dry_run:
                scores[sys] = dict(_MOCK_SCORES[sys])
            else:
                scores[sys] = judge_output(prompt, sys, outputs[sys])

        # ── Pairwise judgment ────────────────────────────────────────────────
        print(f"  Running pairwise judge ...")
        if dry_run:
            pairwise = dict(_MOCK_PAIRWISE)
        else:
            pairwise = judge_pairwise(prompt, outputs)

        p_winner  = pairwise.get("winner", "")
        p_ranking = json.dumps(pairwise.get("ranking", []))
        p_reason  = pairwise.get("reason", "")

        # ── Build rows ───────────────────────────────────────────────────────
        for sys in SYSTEMS:
            row = {
                "case_id":   cid,
                "category":  category,
                "prompt":    prompt,
                "system_name": sys,
                "output":    outputs[sys],
                "pairwise_winner":  p_winner,
                "pairwise_ranking": p_ranking,
                "pairwise_reason":  p_reason,
            }
            row.update(scores[sys])
            all_results.append(row)

        print(f"  ✓ {cid} done — pairwise winner: {p_winner}")

    return all_results


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulation-based evaluation for Spoon via counterfactual replay."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip all API calls and use mocked outputs/scores.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Run only the first N cases.")
    args = parser.parse_args()

    cases = load_cases()
    if args.limit:
        cases = cases[: args.limit]
        print(f"Limit mode: running {len(cases)} of {len(load_cases())} cases.")

    if args.dry_run:
        print("Dry-run mode: no API calls will be made.")

    t0 = time.perf_counter()
    all_results = run_evaluation(cases, dry_run=args.dry_run)
    elapsed = time.perf_counter() - t0

    save_results(all_results)
    print_summary(all_results)
    print(f"\nTotal time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
