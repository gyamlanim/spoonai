from langgraph.graph import StateGraph, START, END

from app.graph.state import SpoonState
from app.nodes.call_models import call_models
from app.nodes.extract_claims import extract_claims
from app.nodes.cluster_claims import cluster_claims
from app.nodes.score_support import score_support
from app.nodes.synthesis import synthesis
from app.nodes.independent_resolver import independent_resolver
from app.nodes.final_answer import final_answer


def _route(state: SpoonState) -> str:
    return state["arbitration_decision"].route


def build_graph():
    graph = StateGraph(SpoonState)

    graph.add_node("call_models", call_models)
    graph.add_node("extract_claims", extract_claims)
    graph.add_node("cluster_claims", cluster_claims)
    graph.add_node("score_support", score_support)
    graph.add_node("synthesis", synthesis)
    graph.add_node("independent_resolver", independent_resolver)
    graph.add_node("final_answer", final_answer)

    graph.add_edge(START, "call_models")
    graph.add_edge("call_models", "extract_claims")
    graph.add_edge("extract_claims", "cluster_claims")
    graph.add_edge("cluster_claims", "score_support")

    graph.add_conditional_edges(
        "score_support",
        _route,
        {
            "synthesis": "synthesis",
            "independent_resolver": "independent_resolver",
        },
    )

    graph.add_edge("synthesis", "final_answer")
    graph.add_edge("independent_resolver", "final_answer")
    graph.add_edge("final_answer", END)

    return graph.compile()
