from app.graph.state import SpoonState
from app.schemas.clusters import ClaimCluster, ClusterMember, ClusterClaimsResult
from app.utils.tracing import trace_step


def _jaccard(a: str, b: str) -> float:
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def cluster_claims(state: SpoonState) -> dict:
    run_id    = state.get("run_id")
    extracted = state["extracted_claims"]

    flat: list[tuple[str, str, str]] = []
    for llm_key in ("llm_1", "llm_2", "llm_3"):
        for claim in getattr(extracted, llm_key).claims:
            flat.append((llm_key, claim.id, claim.text))

    extract_claims_output = {
        llm_key: [{"id": c.id, "text": c.text}
                  for c in getattr(extracted, llm_key).claims]
        for llm_key in ("llm_1", "llm_2", "llm_3")
    }

    with trace_step(run_id, "cluster_claims",
                    input_data=extract_claims_output) as trace:
        buckets: list[list[tuple[str, str, str]]] = []
        for item in flat:
            placed = False
            for bucket in buckets:
                if _jaccard(item[2], bucket[0][2]) >= 0.25:
                    bucket.append(item)
                    placed = True
                    break
            if not placed:
                buckets.append([item])

        clusters = []
        for i, bucket in enumerate(buckets):
            distinct_models = {llm for llm, _, _ in bucket}
            clusters.append(ClaimCluster(
                cluster_id=f"cl{i + 1}",
                canonical_claim=bucket[0][2],
                members=[ClusterMember(model_name=llm, claim_id=cid, claim_text=ct)
                         for llm, cid, ct in bucket],
                support_count=len(distinct_models),
            ))

        result = ClusterClaimsResult(clusters=clusters)
        trace["output"] = {
            "num_clusters": len(clusters),
            "clusters": [{"id": c.cluster_id, "claim": c.canonical_claim,
                          "support": c.support_count} for c in clusters],
        }

    return {"claim_clusters": result}
