from datasets import load_dataset
from app.main import run_spoon
import re
import time

# ── Prompt formatting ─────────────────────────────────────────────

def format_prompt(question, options):
    options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
    return f"""Question: {question}

Options:
{options_text}

Your answer must end with: "The answer is X." where X is the correct letter (A-J). No other letters should appear after that line."""

# ── Output cleaning ───────────────────────────────────────────────

def extract_letter(output):
    # Look for "The answer is X" pattern first (most reliable)
    match = re.search(r"the answer is ([A-J])", output, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Fall back to last standalone letter in the string
    matches = re.findall(r"\b([A-J])\b", output.upper())
    return matches[-1] if matches else ""

# ── Spoon model ───────────────────────────────────────────────────

def spoon_model(prompt):
    response = run_spoon(prompt, store=[])
    return extract_letter(response.final_answer)

# ── Evaluation loop ───────────────────────────────────────────────

def evaluate(model_fn, dataset, n=50, delay=15):
    correct = 0

    for i, item in enumerate(dataset.select(range(n))):
        prompt = format_prompt(item["question"], item["options"])

        try:
            pred = model_fn(prompt)
        except Exception as e:
            print(f"  Error on Q{i+1}: {e}")
            pred = ""

        answer = item["answer"]
        if pred == answer:
            correct += 1

        print(f"\nQ{i+1}")
        print("Pred:", pred, "| True:", answer)

        if i < n - 1:
            time.sleep(delay)

    accuracy = correct / n
    return accuracy

# ── Main runner ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading dataset...")
    dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")

    print("\nRunning spoon (15s between questions)...")
    spoon_acc = evaluate(spoon_model, dataset, n=50, delay=15)

    print("\n==============================")
    print("FINAL RESULTS")
    print("==============================")
    print(f"Spoon Accuracy: {spoon_acc:.4f}")
