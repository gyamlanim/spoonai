# MMLU-Pro Benchmark Results

## Summary

| Metric | Value |
|---|---|
| **Spoon Accuracy** | **88.0%** (44/50 correct) |
| Top 25% threshold | ~75–78% |
| Average model on leaderboard | ~70.6% |
| Near state-of-the-art range | ~88–90% |
| **Conclusion** | Meets and exceeds top 25% requirement; performs at the top end of evaluated models |

Leaderboard reference: https://huggingface.co/spaces/TIGER-Lab/MMLU-Pro

---

## Methodology

- **Dataset:** TIGER-Lab/MMLU-Pro (test split)
- **Sample size:** 50 questions
- **Delay between questions:** 15 seconds (to manage rate limits across 3 parallel model calls)
- **Evaluation script:** `eval_mmlu.py`
- **Extraction:** answer letter parsed from Spoon's `final_answer` using `"The answer is X."` pattern, falling back to last standalone letter A–J

---

## Per-Question Results

| Q | Pred | True | Correct |
|---|---|---|---|
| 1 | I | I | ✓ |
| 2 | F | F | ✓ |
| 3 | J | J | ✓ |
| 4 | C | C | ✓ |
| 5 | G | G | ✓ |
| 6 | A | A | ✓ |
| 7 | D | D | ✓ |
| 8 | J | J | ✓ |
| 9 | E | E | ✓ |
| 10 | F | F | ✓ |
| 11 | E | E | ✓ |
| 12 | C | G | ✗ |
| 13 | J | J | ✓ |
| 14 | B | D | ✗ |
| 15 | F | F | ✓ |
| 16 | J | J | ✓ |
| 17 | J | F | ✗ |
| 18 | A | A | ✓ |
| 19 | B | B | ✓ |
| 20 | D | D | ✓ |
| 21 | J | J | ✓ |
| 22 | I | I | ✓ |
| 23 | E | E | ✓ |
| 24 | H | H | ✓ |
| 25 | J | J | ✓ |
| 26 | J | J | ✓ |
| 27 | H | H | ✓ |
| 28 | F | F | ✓ |
| 29 | H | H | ✓ |
| 30 | C | C | ✓ |
| 31 | E | E | ✓ |
| 32 | H | H | ✓ |
| 33 | J | J | ✓ |
| 34 | I | I | ✓ |
| 35 | I | I | ✓ |
| 36 | B | I | ✗ |
| 37 | H | H | ✓ |
| 38 | A | A | ✓ |
| 39 | H | H | ✓ |
| 40 | J | J | ✓ |
| 41 | G | G | ✓ |
| 42 | A | A | ✓ |
| 43 | G | G | ✓ |
| 44 | C | A | ✗ |
| 45 | B | B | ✓ |
| 46 | F | J | ✗ |
| 47 | J | J | ✓ |
| 48 | I | I | ✓ |
| 49 | G | G | ✓ |
| 50 | F | F | ✓ |

**Correct: 44 / 50 — Accuracy: 88.0%**

Incorrect questions: 12, 14, 17, 36, 44, 46
