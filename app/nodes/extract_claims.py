import json
from pathlib import Path
import anthropic

from app.core.config import ANTHROPIC_API_KEY
from app.graph.state import SpoonState
from app.schemas.claims import ClaimExtractionResult
from app.utils.tracing import trace_step

_PROMPT  = (Path(__file__).parent.parent / "prompts" / "extract_claims.txt").read_text()
_client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=60.0)
_MODEL = "claude-sonnet-4-6"


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def extract_claims(state: SpoonState) -> dict:
    run_id  = state.get("run_id")
    answers = state["model_answers"]

    user_content = (
        f"llm_1_answer: {answers[0].answer_text}\n"
        f"llm_2_answer: {answers[1].answer_text}\n"
        f"llm_3_answer: {answers[2].answer_text}"
    )

    with trace_step(run_id, "extract_claims",
                    input_data={"answers": [a.answer_text[:200] for a in answers]},
                    model_name=_MODEL) as trace:
        response = _client.messages.create(
            model=_MODEL,
            temperature=0,
            max_tokens=1024,
            messages=[{"role": "user", "content": f"{_PROMPT}\n\n{user_content}"}],
        )
        raw = json.loads(_strip_fences(response.content[0].text))
        result = ClaimExtractionResult.model_validate(raw)
        trace["output"] = raw
        trace["usage"] = {
            "prompt_tokens":     response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens":      response.usage.input_tokens + response.usage.output_tokens,
        }

    return {"extracted_claims": result}
