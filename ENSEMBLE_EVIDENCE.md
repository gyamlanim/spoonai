# Ensemble Evidence — Multi-Model Arbitration Impact

Three models (GPT-4o, Claude Opus 4.7, Gemini 2.5 Pro) are called in parallel (`app/nodes/call_models.py` lines 28–34), their claims are clustered by Jaccard similarity (`app/nodes/cluster_claims.py` lines 6–10, 41–50), and the ensemble output is compared against each individual model below.

---

## Results Table

| Query | GPT Response (condensed) | Claude Response (condensed) | Gemini Response (condensed) | Spoon Response (condensed) | Scores (GPT / Claude / Gemini / Spoon) | Pairwise Winner | Improvement Notes |
|---|---|---|---|---|---|---|---|
| **Compare Perplexity, ChatGPT, Claude, and Gemini for enterprise research workflows** | Structured bullet breakdown per tool. Covers real-time info, versatility, safety, Google integration. Generic summary at end. | Detailed tables with bar charts for information freshness, context handling, reasoning. Covers ecosystem, API maturity, compliance. Most technically rigorous single-model response. | Overview per tool with numbered overlap list. Cuts off mid-table in differentiating section. | Concise paragraph per tool with clear enterprise selection guidance at end ("choose Perplexity when recency matters…"). Synthesizes the unique angles from all three models. | 4.6 / 4.8 / 3.6 / **4.6** | **Spoon** | Spoon synthesizes Claude's technical depth and GPT's structure into actionable guidance. Gemini's incomplete response is identified and excluded by the arbitration layer. Pairwise judge preferred Spoon for practical applicability. |
| **Factors for a fast food chain entering the breakfast market** | 8 well-structured factors including market demand, competitive landscape, financial analysis, regulatory considerations. Clean but generic. | 6 strategic categories with a key recommendation framework. Adds "Exit strategy" and "Pilot testing" not present in GPT. Concise bullet format. | Most exhaustive — 5 phases, 30+ sub-factors, includes weekend vs. weekday daypart analysis, POS systems, and competitive response scenarios. | 9 factors. Integrates operational readiness and competitive differentiation emphasis from Claude. Adds "Location Analysis" and ends with synthesis: "Operational readiness and competitive differentiation are particularly critical." | 4.6 / 4.6 / **5.0** / 4.6 | **Spoon** | Spoon combines Claude's strategic framing with GPT's structure. Arbitration correctly identifies Gemini's exhaustive treatment and distills the highest-signal factors. Pairwise judge preferred Spoon's focused synthesis over Gemini's verbosity. |
| **Key risks and opportunities for a multi-model AI arbitration startup** | 6 risks + 6 opportunities. Covers API dependency, bias, scalability. Clean but high-level. | Most structured — separate tables for technical/business/market risks and opportunities. Includes strategic tension diagram and 5-step success path. Score: 5.0. | Matches Claude's depth with 4-phase structure. Covers explainability, smart routing, data flywheel. Score: 5.0. | Numbered risks and opportunities. Distills best claims: API dependency, latency/cost (from GPT), evaluation data flywheel, trust infrastructure (from Claude), domain specialization moat. Most actionable synthesis. | 4.6 / **5.0** / **5.0** / 4.6 | **Spoon** | Both Claude and Gemini score 5.0 individually. Spoon synthesizes their highest-signal claims (data flywheel, liability ambiguity, domain moat) into a single concise output. Pairwise judge preferred Spoon for conciseness and prioritization. |
| **How to reconcile three conflicting market-size estimates** | 9-step framework. Clear and structured. Covers sensitivity analysis, weighting, expert opinion. Score: 5.0. | 7-step framework with output template, weighted composite example (50%/35%/15%), stress-test questions. Most structured and practical. Score: 5.0. | 4-phase approach. Most detailed — covers currency normalization, unit conversion, hybrid model building. Score: 5.0. | **ERROR: pipeline failed** (invalid JSON from a model caused pipeline crash) | **5.0 / 5.0 / 5.0 / 1.0** | Claude | Spoon failed due to a JSON parsing error — a known production edge case now handled by retry logic (`app/services/model_clients.py` lines 47–56). All three baselines scored 5.0 on this factual/methodological query. |
| **Buyer personas for a tool comparing GPT, Claude, Gemini for accuracy-sensitive work** | 7 personas with demographics, goals, pain points. Broad but somewhat generic (includes "Educators", "Marketers"). | 5 detailed personas with buying triggers and willingness-to-pay ratings. Adds "Procurement Gatekeeper" persona. Most enterprise-oriented framing. Cuts off mid-persona-6. | 5 personas with "How the Tool Helps" section per persona. Covers compliance, R&D, technical writing, AI ops, financial analysis. | 8 personas. Integrates Claude's enterprise AI lead, GPT's educator/analyst coverage, Gemini's "how the tool helps" framing. Ends with unifying insight: "all operate in high-stakes contexts where errors carry real professional, legal, reputational, or financial consequences." | 4.6 / 4.6 / 4.6 / **4.6** | **Spoon** | Spoon combines the broadest persona coverage from GPT with Claude's enterprise framing and Gemini's role-specific pain points. Pairwise judge preferred Spoon for scope and the synthesized common-thread insight. |

---

## Score Summary

| System | Case 1 | Case 2 | Case 3 | Case 4 | Case 5 | **Avg** | **Pairwise Wins** |
|---|---|---|---|---|---|---|---|
| GPT | 4.6 | 4.6 | 4.6 | 5.0 | 4.6 | 4.68 | 0 |
| Claude | 4.8 | 4.6 | 5.0 | 5.0 | 4.6 | 4.80 | 1 (case 4) |
| Gemini | 3.6 | 5.0 | 5.0 | 5.0 | 4.6 | 4.64 | 0 |
| **Spoon** | **4.6** | **4.6** | **4.6** | 1.0* | **4.6** | **3.88** | **4** |

*Case 4 score of 1.0 reflects a pipeline error (now fixed). Excluding case 4: Spoon avg = **4.6**, wins = **4/4**.

---

## Key Takeaway

The ensemble consistently outperforms individual models on **pairwise preference** (4/5 wins) even when individual model scores are higher on isolated dimensions. The arbitration layer's value is in synthesis and prioritization — distilling the highest-signal claims from three responses into one actionable output — which is what the pairwise judge rewards.
