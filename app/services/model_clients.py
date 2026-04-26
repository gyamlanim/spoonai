import json
from pathlib import Path
from openai import OpenAI, RateLimitError as OpenAIRateLimitError
import anthropic
from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.core.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
from app.core.safety import SAFETY_SYSTEM_PROMPT, safety_triggered
from app.schemas.model_outputs import ModelAnswer

_PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "base_answer.txt").read_text()

_openai    = OpenAI(api_key=OPENAI_API_KEY)
_anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_gemini    = genai.Client(api_key=GEMINI_API_KEY)

_openai_retry = retry(
    retry=retry_if_exception_type((OpenAIRateLimitError, ValueError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(4),
    reraise=True,
)
_anthropic_retry = retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIStatusError, ValueError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(4),
    reraise=True,
)
_gemini_retry = retry(
    retry=retry_if_exception_type((Exception,)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(4),
    reraise=True,
)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _parse_answer(raw: str, model: str) -> str:
    text = _strip_fences(raw)
    if not text:
        raise ValueError(f"{model} returned empty response — will retry")
    try:
        # Use raw_decode to grab just the first JSON object and ignore trailing content
        obj, _ = json.JSONDecoder().raw_decode(text)
        return obj["answer"]
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"{model} returned non-JSON: {text[:100]!r}") from e


def _build_prompt(question: str, word_count: int, context: str = "",
                  conversation_history: str = "") -> str:
    parts = []
    if conversation_history:
        parts.append(conversation_history)
    if context:
        parts.append(f"DOCUMENT CONTEXT:\n{context}")
    parts.append(f"CURRENT USER QUESTION:\n{question}" if conversation_history or context else question)
    question_text = "\n\n".join(parts)
    return (
        _PROMPT_TEMPLATE
        .replace("{question_text}", question_text)
        .replace("{word_count}", str(word_count))
    )


def call_openai(prompt: str, word_count: int = 150, context: str = "",
                conversation_history: str = "") -> tuple[ModelAnswer, dict]:
    user_prompt = _build_prompt(prompt, word_count, context, conversation_history)

    @_openai_retry
    def _call():
        response = _openai.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        )
        answer = _parse_answer(response.choices[0].message.content or "", "gpt-4o")
        return response, answer

    response, answer = _call()
    usage = {
        "prompt_tokens":     response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens":      response.usage.total_tokens,
        "safety_triggered":  safety_triggered(answer),
    }
    return ModelAnswer(model_name="gpt-4o", answer_text=answer), usage


def call_claude(prompt: str, word_count: int = 150, context: str = "",
                conversation_history: str = "") -> tuple[ModelAnswer, dict]:
    user_prompt = _build_prompt(prompt, word_count, context, conversation_history)

    @_anthropic_retry
    def _call():
        response = _anthropic.messages.create(
            model="claude-opus-4-7",
            system=SAFETY_SYSTEM_PROMPT,
            max_tokens=1024,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text if response.content else ""
        answer = _parse_answer(raw, "claude-opus-4-7")
        return response, answer

    response, answer = _call()
    usage = {
        "prompt_tokens":     response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens":      response.usage.input_tokens + response.usage.output_tokens,
        "safety_triggered":  safety_triggered(answer),
    }
    return ModelAnswer(model_name="claude-opus-4-7", answer_text=answer), usage


def call_gemini(prompt: str, word_count: int = 150, context: str = "",
                conversation_history: str = "") -> tuple[ModelAnswer, dict]:
    user_prompt = _build_prompt(prompt, word_count, context, conversation_history)

    @_gemini_retry
    def _call():
        response = _gemini.models.generate_content(
            model="gemini-2.5-pro",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                system_instruction=SAFETY_SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        answer = _parse_answer(response.text or "", "gemini-2.5-pro")
        return response, answer

    response, answer = _call()
    meta = getattr(response, "usage_metadata", None)
    usage = {
        "prompt_tokens":     getattr(meta, "prompt_token_count",     None) if meta else None,
        "completion_tokens": getattr(meta, "candidates_token_count", None) if meta else None,
        "total_tokens":      getattr(meta, "total_token_count",      None) if meta else None,
        "safety_triggered":  safety_triggered(answer),
    }
    return ModelAnswer(model_name="gemini-2.5-pro", answer_text=answer), usage
