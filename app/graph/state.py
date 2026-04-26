from typing import TypedDict
from app.schemas.model_outputs import ModelAnswer
from app.schemas.claims import ClaimExtractionResult
from app.schemas.clusters import ClusterClaimsResult
from app.schemas.arbitration import ArbitrationDecision
from app.schemas.base_answer import DirectAnswerOutput
from app.schemas.responses import ResolverOutput, FinalResponse


class SpoonState(TypedDict, total=False):
    user_query: str
    run_id: str | None
    rag_context: str | None
    conversation_history: str | None
    model_answers: list[ModelAnswer]
    extracted_claims: ClaimExtractionResult | None
    claim_clusters: ClusterClaimsResult | None
    arbitration_decision: ArbitrationDecision | None
    synthesis_output: DirectAnswerOutput | None
    resolver_output: ResolverOutput | None
    final_response: FinalResponse | None
