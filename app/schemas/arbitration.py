from pydantic import BaseModel


class ArbitrationDecision(BaseModel):
    route: str
    reason: str
    outlier_model: str | None = None
    majority_models: list[str]
