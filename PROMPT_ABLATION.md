# Claim Extraction Prompt Ablation

## Prompt Versions

| Version | Full Prompt Text |
|---|---|
| **V1 — Basic** | WHO: You extract claims from answers.<br>INSTRUCTIONS: Extract the important claims from each answer. Return them as a list.<br>INPUT: llm_1_answer, llm_2_answer, llm_3_answer<br>OUTPUT FORMAT: `{ "llm_1": [], "llm_2": [], "llm_3": [] }` |
| **V2 — Improved** | WHO: You are a claim extractor.<br>INSTRUCTIONS: Extract the main claims from each answer. Each claim should be concise. Avoid unnecessary explanation.<br>STEPS: Identify key ideas. Write each as a short statement.<br>INPUT: llm_1_answer, llm_2_answer, llm_3_answer<br>OUTPUT FORMAT: `{ "llm_1": { "claims": [] }, "llm_2": { "claims": [] }, "llm_3": { "claims": [] } }` |
| **Final — Engineered** | WHO: You are a Claim Extractor.<br>INSTRUCTIONS: Extract only the most important, top-level explicit claims asserted in the answer. A top-level claim materially affects the answer's conclusion. Do not extract supporting details, explanations, examples, or restatements. A claim must be a standalone assertion that can be agreed with or contradicted.<br>MULTI-LLM HANDLING: Treat each LLM answer independently.<br>STEPS: Identify explicit assertions. Select the 2–5 most central claims. Remove reasoning and stylistic language. Normalize into neutral declarative lowercase statements. Ensure each claim contains one atomic idea. Do not infer unstated claims.<br>INPUT: llm_1_answer, llm_2_answer, llm_3_answer<br>OUTPUT FORMAT (JSON ONLY): `{ "llm_1": { "claims": [] }, "llm_2": { "claims": [] }, "llm_3": { "claims": [] } }` |

---

## Output Comparison

| Version | llm_1 Output | llm_2 Output | llm_3 Output |
|---|---|---|---|
| **V1** | "use SoA layout", "align data", "process in blocks", "tradeoff exists", "may fail" | "use SoA", "batch processing", "two-pass updates", "avoid false sharing", "NUMA issues" | "use SoA", "align to 64 bytes", "branchless selection", "batch updates", "TLB pressure" |
| **V2** | SoA layout; cache-line alignment; cache-sized blocks; locality vs branch tradeoff | SoA layout; sequential batching; two-pass updates; avoid false sharing | SoA layout; alignment; branchless selection; batched updates |
| **Final** | "use a structure of arrays layout"; "partition data into cache-line-aligned per-thread chunks"; "process data in cache-sized blocks" | "use a structure of arrays layout"; "process data in sequential batches"; "separate scanning and updates into two passes" | "use a structure of arrays layout"; "align data to cache line boundaries to prevent false sharing"; "use branchless selection for conditional updates" |

---

## Observations

| Version | Observations |
|---|---|
| **V1** | Over-extraction — too many claims. Includes vague or non-atomic ideas. No consistency across LLMs. No filtering of importance → noisy output. |
| **V2** | More structured and readable. Still mixes abstraction levels (strategy + detail). Some claims bundle multiple ideas. No strict definition of "important" → inconsistency remains. |
| **Final** | High signal, no noise. Strictly atomic and comparable claims. Consistent structure across LLMs. Removes explanations and redundancy. Directly supports downstream clustering and disagreement detection. |

---

## Conclusion

The progression V1 → V2 → Final shows a shift from unconstrained extraction to structured but inconsistent outputs, and finally to a normalized, high-signal representation. The final prompt performs best because it:

- Precisely defines what counts as a claim
- Enforces atomicity and normalization
- Eliminates non-essential information
- Produces outputs that are directly comparable across LLMs

This makes it significantly more effective for downstream claim clustering and disagreement resolution.

The final prompt is live at `app/prompts/extract_claims.txt`.
