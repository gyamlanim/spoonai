import json
from pathlib import Path
from openai import OpenAI
import anthropic
from google import genai
from google.genai import types

from app.core.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
from app.core.safety import SAFETY_SYSTEM_PROMPT, safety_triggered
from app.schemas.model_outputs import ModelAnswer

_PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "base_answer.txt").read_text()

_openai    = OpenAI(api_key=OPENAI_API_KEY)
_anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_gemini    = genai.Client(api_key=GEMINI_API_KEY)


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
    response = _openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
    )
    answer = json.loads(response.choices[0].message.content)["answer"]
    usage = {
        "prompt_tokens":     response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens":      response.usage.total_tokens,
        "safety_triggered":  safety_triggered(answer),
    }
    return ModelAnswer(model_name="gpt-4o-mini", answer_text=answer), usage


def call_claude(prompt: str, word_count: int = 150, context: str = "",
                conversation_history: str = "") -> tuple[ModelAnswer, dict]:
    user_prompt = _build_prompt(prompt, word_count, context, conversation_history)
    response = _anthropic.messages.create(
        model="claude-sonnet-4-6",
        system=SAFETY_SYSTEM_PROMPT,
        temperature=0,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_prompt}],
    )
    answer = json.loads(response.content[0].text)["answer"]
    usage = {
        "prompt_tokens":     response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens":      response.usage.input_tokens + response.usage.output_tokens,
        "safety_triggered":  safety_triggered(answer),
    }
    return ModelAnswer(model_name="claude-sonnet-4-6", answer_text=answer), usage


def call_gemini(prompt: str, word_count: int = 150, context: str = "",
                conversation_history: str = "") -> tuple[ModelAnswer, dict]:
    user_prompt = _build_prompt(prompt, word_count, context, conversation_history)
    response = _gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            system_instruction=SAFETY_SYSTEM_PROMPT,
        ),
    )
    answer = json.loads(response.text)["answer"]
    meta = getattr(response, "usage_metadata", None)
    usage = {
        "prompt_tokens":     getattr(meta, "prompt_token_count",     None) if meta else None,
        "completion_tokens": getattr(meta, "candidates_token_count", None) if meta else None,
        "total_tokens":      getattr(meta, "total_token_count",      None) if meta else None,
        "safety_triggered":  safety_triggered(answer),
    }
    return ModelAnswer(model_name="gemini-2.5-flash", answer_text=answer), usage
