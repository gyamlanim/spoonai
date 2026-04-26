from pydantic import BaseModel


class ClusterMember(BaseModel):
    model_name: str
    claim_id: str
    claim_text: str


class ClaimCluster(BaseModel):
    cluster_id: str
    canonical_claim: str
    members: list[ClusterMember]
    support_count: int


class ClusterClaimsResult(BaseModel):
    clusters: list[ClaimCluster]
