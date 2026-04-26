import re as _re
import numpy as np
from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def chunk_sentence_based(text: str, sentences_per_chunk: int = 2,
                         overlap: int = 1) -> list[str]:
    sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    step = sentences_per_chunk - overlap
    chunks = []
    for i in range(0, len(sentences), step):
        chunk = " ".join(sentences[i : i + sentences_per_chunk])
        if chunk:
            chunks.append(chunk)
    return chunks


def build_store(text: str, sentences_per_chunk: int = 2,
                overlap: int = 1) -> list[dict]:
    chunks = chunk_sentence_based(text, sentences_per_chunk=sentences_per_chunk,
                                  overlap=overlap)
    return [{"text": c, "embedding": embed(c)} for c in chunks]


def build_store_from_file(file_path: str, sentences_per_chunk: int = 2,
                          overlap: int = 1) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        return build_store(f.read(), sentences_per_chunk=sentences_per_chunk,
                           overlap=overlap)


def embed(text: str) -> np.ndarray:
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return np.array(response.data[0].embedding)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom != 0 else 0.0


def retrieve(query: str, store: list[dict], top_k: int = 10) -> list[str]:
    q_emb = embed(query)
    scored = [(item["text"], cosine_sim(q_emb, item["embedding"])) for item in store]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scored[:top_k]]


def llm_rerank(query: str, chunks: list[str], top_n: int = 3) -> list[str]:
    if not chunks:
        return []
    formatted = "\n\n".join(f"{i}. {c[:300]}" for i, c in enumerate(chunks))
    prompt = (
        f"Question: {query}\n\n"
        f"Select ONLY the chunks that directly answer the question.\n"
        f"Do NOT include background, definitions, or unrelated topics.\n\n"
        f"{formatted}\n\n"
        f"Return only indices as space-separated integers (example: 0 2). "
        f"If no chunk is relevant, return: none"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content or ""
    if "none" in raw.lower():
        return chunks[:top_n]
    indices = [int(x) for x in raw.split() if x.isdigit() and int(x) < len(chunks)]
    return [chunks[i] for i in indices[:top_n]] or chunks[:top_n]


def rag_pipeline(query: str, store: list[dict]) -> str:
    retrieved = retrieve(query, store)
    reranked = llm_rerank(query, retrieved)
    return "\n\n".join(reranked)
