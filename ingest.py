"""
ingest.py — Corpus ingestion pipeline for Badho AI Career Coach

Chunking strategy: 512 tokens per chunk, 64 token overlap, using tiktoken.
Why 512: Career documents are dense prose paragraphs. 512 tokens captures
a complete concept (a role description, a skill cluster, a salary range)
without fragmenting it mid-idea. Smaller chunks (256) lose context needed
to answer multi-part questions. Larger chunks (1024) reduce retrieval
precision — too much noise per chunk.

Why 64 overlap: Concepts that span a chunk boundary are captured by both
adjacent chunks. Without overlap, a sentence split across two chunks would
be retrievable by neither. 64 tokens (≈48 words) is enough to preserve
boundary context without bloating the index.

What I would change with more time: Test chunk sizes 256/512/768 with an
offline retrieval eval (golden Q&A dataset, measure Recall@3). Also test
semantic chunking using embedding similarity to detect topic boundaries —
likely better for our mixed-format corpus.

Re-runnable: deletes and recreates the ChromaDB collection on every run.
"""

import os
import re
import time
from pathlib import Path

import chromadb
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CORPUS_DIR    = Path("corpus")
CHROMA_PATH   = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION    = "career_coach"
CHUNK_TOKENS  = 512
OVERLAP_TOKEN = 64
EMBED_MODEL   = "text-embedding-3-small"
EMBED_BATCH   = 50   # OpenAI allows up to 100 per call; 50 is safe

# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
tokenizer     = tiktoken.get_encoding("cl100k_base")


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_metadata(text: str) -> dict:
    """Extract SOURCE / SCRAPED / LICENSE from the first 3 lines of a file."""
    meta = {"source": "unknown", "scraped": "n/a", "license": "unknown"}
    for line in text.splitlines()[:5]:
        line = line.strip()
        if line.startswith("# SOURCE:"):
            meta["source"] = line.replace("# SOURCE:", "").strip()
        elif line.startswith("# SCRAPED:"):
            meta["scraped"] = line.replace("# SCRAPED:", "").strip()
        elif line.startswith("# LICENSE:"):
            meta["license"] = line.replace("# LICENSE:", "").strip()
    return meta


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Sliding window chunker using tiktoken token counts.
    Returns list of decoded string chunks.
    """
    tokens = tokenizer.encode(text)
    chunks = []
    step   = chunk_size - overlap
    start  = 0

    while start < len(tokens):
        end   = min(start + chunk_size, len(tokens))
        chunk = tokenizer.decode(tokens[start:end])
        chunks.append(chunk)
        if end == len(tokens):
            break
        start += step

    return chunks


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, return list of float vectors."""
    response = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ── Main ingestion ─────────────────────────────────────────────────────────────

def ingest() -> None:
    # ── Step 1: Reset collection ──────────────────────────────────────────────
    print(f"\n{'='*55}")
    print("Badho AI — Corpus Ingestion Pipeline")
    print(f"{'='*55}")

    existing = [c.name for c in chroma_client.list_collections()]
    if COLLECTION in existing:
        chroma_client.delete_collection(COLLECTION)
        print(f"Deleted existing collection: {COLLECTION}")

    collection = chroma_client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Created fresh collection: {COLLECTION}")

    # ── Step 2: Load and chunk all documents ──────────────────────────────────
    doc_files = sorted(CORPUS_DIR.glob("*.md")) + sorted(CORPUS_DIR.glob("*.txt"))

    if not doc_files:
        print(f"ERROR: No .md or .txt files found in {CORPUS_DIR}/")
        return

    all_chunks   : list[str]  = []
    all_ids      : list[str]  = []
    all_metadatas: list[dict] = []

    total_docs   = 0
    total_chunks = 0

    for doc_path in doc_files:
        raw_text = doc_path.read_text(encoding="utf-8")
        meta     = parse_metadata(raw_text)
        meta["doc_name"] = doc_path.name

        chunks = chunk_text(raw_text, CHUNK_TOKENS, OVERLAP_TOKEN)
        total_docs   += 1
        total_chunks += len(chunks)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_path.stem}_chunk_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({**meta, "chunk_index": i})

        print(f"  Loaded: {doc_path.name:<50} → {len(chunks)} chunks")

    print(f"\nTotal: {total_docs} documents → {total_chunks} chunks")

    # ── Step 3: Embed in batches ──────────────────────────────────────────────
    print(f"\nEmbedding {total_chunks} chunks in batches of {EMBED_BATCH}...")
    all_embeddings: list[list[float]] = []

    for i in range(0, len(all_chunks), EMBED_BATCH):
        batch      = all_chunks[i : i + EMBED_BATCH]
        batch_num  = (i // EMBED_BATCH) + 1
        total_bat  = (total_chunks + EMBED_BATCH - 1) // EMBED_BATCH
        embeddings = embed_batch(batch)
        all_embeddings.extend(embeddings)
        print(f"  Batch {batch_num}/{total_bat} embedded ({len(batch)} chunks)")
        time.sleep(0.1)   # gentle rate limit buffer

    # ── Step 4: Store in ChromaDB ─────────────────────────────────────────────
    print("\nStoring in ChromaDB...")
    store_batch = 100

    for i in range(0, len(all_chunks), store_batch):
        collection.add(
            ids        = all_ids[i : i + store_batch],
            documents  = all_chunks[i : i + store_batch],
            embeddings = all_embeddings[i : i + store_batch],
            metadatas  = all_metadatas[i : i + store_batch],
        )

    # ── Step 5: Verify ────────────────────────────────────────────────────────
    stored_count = collection.count()
    print(f"\n{'='*55}")
    print(f"Ingestion complete.")
    print(f"  Documents : {total_docs}")
    print(f"  Chunks    : {total_chunks}")
    print(f"  Stored    : {stored_count} vectors in ChromaDB")
    print(f"  Location  : {CHROMA_PATH}")
    print(f"{'='*55}\n")

    # ── Step 6: Quick sanity test ─────────────────────────────────────────────
    print("Running sanity check query...")
    test_query     = "How to transition from backend engineer to AI engineer?"
    test_embedding = embed_batch([test_query])[0]

    results = collection.query(
        query_embeddings=[test_embedding],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    print(f"\nTop 3 results for: '{test_query}'")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        print(f"\n  [{i+1}] Score: {1 - dist:.3f} | Source: {meta['doc_name']}")
        print(f"       {doc[:120].strip()}...")

    print("\nSanity check passed. Ingest pipeline is working.\n")


if __name__ == "__main__":
    ingest()