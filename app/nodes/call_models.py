from concurrent.futures import ThreadPoolExecutor

from app.graph.state import SpoonState
from app.services.model_clients import call_openai, call_claude, call_gemini
from app.utils.tracing import trace_step


def _traced_call(run_id, fn, step_name, query, context, history):
    with trace_step(run_id, step_name,
                    input_data={
                        "query":   query,
                        "context": context[:500] if context else None,
                        "history": history[:500] if history else None,
                    },
                    model_name=step_name) as trace:
        model_answer, usage = fn(query, 150, context, history)
        trace["output"] = {"answer": model_answer.answer_text}
        trace["usage"] = {k: v for k, v in usage.items() if k != "prompt"}
    return model_answer


def call_models(state: SpoonState) -> dict:
    run_id  = state.get("run_id")
    query   = state["user_query"]
    context = state.get("rag_context") or ""
    history = state.get("conversation_history") or ""

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_traced_call, run_id, call_openai, "call_gpt",    query, context, history),
            executor.submit(_traced_call, run_id, call_claude,  "call_claude", query, context, history),
            executor.submit(_traced_call, run_id, call_gemini,  "call_gemini", query, context, history),
        ]
        model_answers = [f.result() for f in futures]

    return {"model_answers": model_answers}
