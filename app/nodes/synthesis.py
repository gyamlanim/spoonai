import json
from pathlib import Path
import anthropic

from app.core.config import ANTHROPIC_API_KEY
from app.core.safety import SAFETY_SYSTEM_PROMPT, safety_triggered
from app.graph.state import SpoonState
from app.schemas.base_answer import DirectAnswerOutput
from app.utils.tracing import trace_step

_PROMPT = (Path(__file__).parent.parent / "prompts" / "synthesis.txt").read_text()
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=60.0)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def synthesis(state: SpoonState) -> dict:
    run_id        = state.get("run_id")
    clusters      = state["claim_clusters"].clusters
    strong_claims = [c.canonical_claim for c in clusters if c.support_count >= 2]
    model_answers = state["model_answers"]

    claims_block  = "\n".join(f"- {c}" for c in strong_claims)
    answers_block = "\n".join(
        f"answer_{i + 1}: {a.answer_text}" for i, a in enumerate(model_answers)
    )
    user_content = f"SUPPORTED CLAIMS:\n{claims_block}\n\nMODEL ANSWERS:\n{answers_block}"

    with trace_step(run_id, "synthesis",
                    input_data={
                        "strong_claims": strong_claims,
                        "model_answers": {f"answer_{i+1}": a.answer_text
                                          for i, a in enumerate(model_answers)},
                    },
                    model_name="claude-sonnet-4-6") as trace:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            system=SAFETY_SYSTEM_PROMPT,
            temperature=0,
            max_tokens=1024,
            messages=[{"role": "user", "content": f"{_PROMPT}\n\n{user_content}"}],
        )
        raw = json.loads(_strip_fences(response.content[0].text))
        trace["output"] = raw
        trace["usage"] = {
            "prompt_tokens":     response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens":      response.usage.input_tokens + response.usage.output_tokens,
            "safety_triggered":  safety_triggered(raw.get("answer", "")),
        }

    return {"synthesis_output": DirectAnswerOutput(answer=raw["answer"])}
