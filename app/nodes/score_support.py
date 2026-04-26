import json
from pathlib import Path

from google import genai
from google.genai import types

from app.core.config import GEMINI_API_KEY
from app.graph.state import SpoonState
from app.schemas.arbitration import ArbitrationDecision
from app.utils.tracing import trace_step

_PROMPT_TEMPLATE = (
    Path(__file__).parent.parent / "prompts" / "convergence_judge.txt"
).read_text()

_client = genai.Client(api_key=GEMINI_API_KEY)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _format_claims(clusters) -> dict:
    """Convert ClusterClaimsResult into the JSON shape the prompt expects."""
    return {
        "num_clusters": len(clusters),
        "clusters": [
            {
                "id":      c.cluster_id,
                "claim":   c.canonical_claim,
                "support": c.support_count,
            }
            for c in clusters
        ],
    }


def score_support(state: SpoonState) -> dict:
    run_id   = state.get("run_id")
    clusters = state["claim_clusters"].clusters

    claims_payload = _format_claims(clusters)
    prompt = _PROMPT_TEMPLATE.replace(
        "{claims_json}", json.dumps(claims_payload, indent=2)
    )

    with trace_step(run_id, "score_support",
                    input_data=claims_payload,
                    model_name="gemini-2.5-pro") as trace:

        response = _client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0),
        )

        raw, _ = json.JSONDecoder().raw_decode(_strip_fences(response.text))
        converged = str(raw.get("converged", "false")).lower() == "true"
        summary   = raw.get("summary", "")

        meta = getattr(response, "usage_metadata", None)
        trace["usage"] = {
            "prompt_tokens":     getattr(meta, "prompt_token_count",     None) if meta else None,
            "completion_tokens": getattr(meta, "candidates_token_count", None) if meta else None,
            "total_tokens":      getattr(meta, "total_token_count",      None) if meta else None,
        }

        if converged:
            decision = ArbitrationDecision(
                route="synthesis",
                reason=summary,
                majority_models=[],
            )
        else:
            decision = ArbitrationDecision(
                route="independent_resolver",
                reason=summary,
                majority_models=[],
            )

        trace["output"] = {
            "converged": converged,
            "route":     decision.route,
            "summary":   summary,
        }

    return {"arbitration_decision": decision}
