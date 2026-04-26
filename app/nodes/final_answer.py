from app.graph.state import SpoonState
from app.schemas.responses import FinalResponse
from app.utils.tracing import trace_step


def final_answer(state: SpoonState) -> dict:
    run_id = state.get("run_id")

    arbitration = state.get("arbitration_decision")
    synthesis_out = state.get("synthesis_output")
    resolver_out  = state.get("resolver_output")

    with trace_step(run_id, "final_answer",
                    input_data={
                        "route": arbitration.route if arbitration else None,
                        "synthesis_answer": synthesis_out.answer if synthesis_out else None,
                        "resolver_final_answer": resolver_out.final_answer if resolver_out else None,
                        "resolver_slots": [
                            {"slot_id": s.slot_id, "verdict": s.verdict, "claim": s.selected_claim}
                            for s in resolver_out.slots
                        ] if resolver_out else None,
                    }) as trace:
        if state.get("synthesis_output"):
            synthesis = state["synthesis_output"]
            response = FinalResponse(
                final_answer=synthesis.answer,
                supported_claims=[],
                unresolved_claims=[],
            )
        else:
            resolved = state["resolver_output"]
            supported = [
                s.selected_claim for s in resolved.slots
                if s.verdict in ("claim_confirmed", "alternative_correct")
            ]
            unresolved = [
                s.selected_claim for s in resolved.slots
                if s.verdict == "unresolved"
            ]
            response = FinalResponse(
                final_answer=resolved.final_answer,
                supported_claims=supported,
                unresolved_claims=unresolved,
            )

        trace["output"] = {
            "final_answer":    response.final_answer[:300],
            "supported_count": len(response.supported_claims),
            "unresolved_count": len(response.unresolved_claims),
        }

    return {"final_response": response}
