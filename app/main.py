from dotenv import load_dotenv
load_dotenv()

from app.graph.builder import build_graph
from app.schemas.responses import FinalResponse

_graph = build_graph()


def run_spoon(query: str, store: list | None = None, **_) -> FinalResponse:
    initial: dict = {"user_query": query}
    if store:
        from app.services.rag import rag_pipeline
        initial["rag_context"] = rag_pipeline(query, store)
    result = _graph.invoke(initial)
    return result["final_response"]


if __name__ == "__main__":
    query = "how do i make pizza?"
    response = run_spoon(query)

    print("\n=== SPOON RESULT ===")
    print(f"Answer: {response.final_answer}")
    if response.supported_claims:
        print(f"Supported claims: {', '.join(response.supported_claims)}")
    if response.unresolved_claims:
        print(f"Unresolved claims: {', '.join(response.unresolved_claims)}")
