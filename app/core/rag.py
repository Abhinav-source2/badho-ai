"""
RAG pipeline: retrieve → rerank → return top chunks (optimized)
"""
import os
import time
from typing import Any

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import CrossEncoder

load_dotenv()

CHROMA_PATH  = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION   = "career_coach"
EMBED_MODEL  = "text-embedding-3-small"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ⚡ Initialize once (good)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
cross_encoder = CrossEncoder(RERANK_MODEL)


def _get_collection():
    try:
        return chroma_client.get_collection(name=COLLECTION)
    except Exception:
        return chroma_client.create_collection(name=COLLECTION)


# ─────────────────────────────────────────────
# RETRIEVE (OPTIMIZED)
# ─────────────────────────────────────────────
def retrieve(query: str, top_k: int = 5) -> tuple[list[dict], float]:
    """
    Embed query, search ChromaDB, return top_k chunks + retrieval_ms.
    (reduced top_k for speed)
    """
    t0 = time.perf_counter()

    embedding = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=query,
    ).data[0].embedding

    collection = _get_collection()
    results    = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieval_ms = (time.perf_counter() - t0) * 1000

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text"        : doc,
            "source"      : meta.get("source", "unknown"),
            "doc_name"    : meta.get("doc_name", "unknown"),
            "chunk_index" : meta.get("chunk_index", 0),
            "score"       : round(1 - dist, 4),
        })

    return chunks, round(retrieval_ms, 2)


# ─────────────────────────────────────────────
# RERANK (OPTIMIZED)
# ─────────────────────────────────────────────
def rerank(
    query: str,
    chunks: list[dict],
    top_k: int = 3,
) -> tuple[list[dict], float]:
    """
    Cross-encoder rerank (optimized)
    """
    t0 = time.perf_counter()

    if not chunks:
        return [], 0.0

    pairs  = [[query, c["text"]] for c in chunks]

    # ⚡ Faster batch prediction
    scores = cross_encoder.predict(pairs, batch_size=8)

    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = round(float(score), 4)

    reranked  = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    rerank_ms = (time.perf_counter() - t0) * 1000

    return reranked[:top_k], round(rerank_ms, 2)


# ─────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────
def retrieve_and_rerank(
    query: str,
    top_k_retrieve: int = 5,
    top_k_rerank: int = 3,
) -> dict[str, Any]:
    """
    Full pipeline: retrieve → rerank → return result dict.
    """
    chunks, retrieval_ms = retrieve(query, top_k=top_k_retrieve)
    top_chunks, rerank_ms = rerank(query, chunks, top_k=top_k_rerank)

    return {
        "chunks"          : top_chunks,
        "retrieval_ms"    : retrieval_ms,
        "rerank_ms"       : rerank_ms,
        "chunks_retrieved": len(chunks),
        "chunks_returned" : len(top_chunks),
    }


# ─────────────────────────────────────────────
# FORMAT CONTEXT
# ─────────────────────────────────────────────
def format_context(chunks: list[dict]) -> str:
    """Format chunks into prompt context"""
    lines = ["CONTEXT FROM KNOWLEDGE BASE:"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[{i}] Source: {chunk['doc_name']}")
        lines.append(chunk["text"].strip())
    return "\n".join(lines)