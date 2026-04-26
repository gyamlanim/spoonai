from pydantic import BaseModel


class ResolutionNote(BaseModel):
    target: str
    analysis: str


class ResolvedSlot(BaseModel):
    slot_id: str
    verdict: str
    selected_claim: str
    resolution_note: ResolutionNote


class ResolverOutput(BaseModel):
    final_answer: str
    slots: list[ResolvedSlot]


class FinalResponse(BaseModel):
    final_answer: str
    supported_claims: list[str]
    unresolved_claims: list[str]
