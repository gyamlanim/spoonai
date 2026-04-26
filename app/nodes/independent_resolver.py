import json
from pathlib import Path
import anthropic

from app.core.config import ANTHROPIC_API_KEY
from app.core.safety import SAFETY_SYSTEM_PROMPT, safety_triggered
from app.graph.state import SpoonState
from app.schemas.responses import ResolverOutput
from app.utils.tracing import trace_step

_PROMPT = (Path(__file__).parent.parent / "prompts" / "independent_resolver.txt").read_text()
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=90.0)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def independent_resolver(state: SpoonState) -> dict:
    run_id   = state.get("run_id")
    answers  = state["model_answers"]
    clusters = state["claim_clusters"].clusters
    decision = state["arbitration_decision"]

    answers_block  = "\n".join(f"- {a.model_name}: {a.answer_text}" for a in answers)
    clusters_block = "\n".join(
        f"- {c.cluster_id} (support {c.support_count}/3): {c.canonical_claim}"
        for c in clusters
    )
    user_content = (
        f"QUESTION: {state['user_query']}\n\n"
        f"CONVERGENCE SUMMARY:\n{decision.reason}\n\n"
        f"MODEL ANSWERS:\n{answers_block}\n\n"
        f"CLAIM CLUSTERS:\n{clusters_block}\n\n"
        f"OUTLIER MODEL: {decision.outlier_model or 'none'}"
    )

    with trace_step(run_id, "independent_resolver",
                    input_data={
                        "question":            state["user_query"],
                        "convergence_summary": decision.reason,
                        "outlier":             decision.outlier_model,
                        "majority":            decision.majority_models,
                        "clusters":            clusters_block,
                        "answers":             {a.model_name: a.answer_text[:300] for a in answers},
                    },
                    model_name="claude-opus-4-7") as trace:
        response = _client.messages.create(
            model="claude-opus-4-7",
            system=SAFETY_SYSTEM_PROMPT,
            max_tokens=2048,
            messages=[{"role": "user", "content": f"{_PROMPT}\n\n{user_content}"}],
        )
        raw = json.loads(_strip_fences(response.content[0].text))
        result = ResolverOutput.model_validate(raw)
        trace["output"] = {"final_answer": raw.get("final_answer"), "slots": len(raw.get("slots", []))}
        trace["usage"] = {
            "prompt_tokens":     response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens":      response.usage.input_tokens + response.usage.output_tokens,
            "safety_triggered":  safety_triggered(raw.get("final_answer", "")),
        }

    return {"resolver_output": result}
