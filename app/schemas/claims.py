from pydantic import BaseModel


class ExtractedClaim(BaseModel):
    id: str
    text: str


class ClaimSet(BaseModel):
    claims: list[ExtractedClaim]


class ClaimExtractionResult(BaseModel):
    llm_1: ClaimSet
    llm_2: ClaimSet
    llm_3: ClaimSet
