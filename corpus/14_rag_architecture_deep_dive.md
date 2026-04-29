# SOURCE: original
# SCRAPED: n/a
# LICENSE: original

# RAG Architecture: Complete Technical Guide

## What is RAG?
Retrieval-Augmented Generation (RAG) is an AI architecture pattern that grounds
LLM responses in a specific document corpus. Instead of relying on the model's
training data (which has a cutoff date and may hallucinate), RAG retrieves
relevant documents at query time and injects them into the prompt.

## The Core Pipeline

### Step 1: Ingestion (offline)
- Load documents from source (files, URLs, databases)
- Chunk documents into smaller pieces
- Embed each chunk using an embedding model
- Store vectors + metadata in a vector database

### Step 2: Retrieval (online, per query)
- Embed the user's query using the same embedding model
- Search vector database for top-k most similar chunks
- (Optional) Rerank results using a cross-encoder
- Return top chunks with their metadata and similarity scores

### Step 3: Augmentation
- Format retrieved chunks as context
- Inject into the LLM prompt with clear source attribution
- Add instructions: "Answer based on the provided context only"

### Step 4: Generation
- LLM generates a response grounded in the retrieved context
- Response cites sources when configured to do so
- Output is validated or post-processed if needed

## Chunking Strategies

### Fixed-size chunking
Split by token count (e.g., every 512 tokens). Simple and fast. Works well
for uniform documents. Downside: may split mid-sentence or mid-concept.

### Sentence-based chunking
Split on sentence boundaries. Better semantic coherence. Variable chunk sizes.
Good for prose documents.

### Semantic chunking
Use embedding similarity to detect topic boundaries. Best quality, slowest.
Good for documents with clearly distinct sections.

### Overlap
All strategies benefit from overlap (e.g., 64 token overlap between chunks).
Overlap ensures concepts that span a chunk boundary are captured.

## Embedding Model Selection

| Model | Dims | Cost | Quality | Best For |
|-------|------|------|---------|----------|
| text-embedding-3-small | 1536 | $0.02/1M | Good | Most use cases |
| text-embedding-3-large | 3072 | $0.13/1M | Better | High precision needs |
| text-embedding-ada-002 | 1536 | $0.10/1M | Good | Legacy systems |
| nomic-embed-text | 768 | Free | Good | Self-hosted |
| voyage-large-2-instruct | 1024 | $0.12/1M | Best | Production RAG |

## Reranking
First-stage retrieval (embedding similarity) optimizes for recall.
Reranking optimizes for precision. A cross-encoder reads the query + each
document together and scores relevance more accurately than embedding similarity.

Popular rerankers:
- cross-encoder/ms-marco-MiniLM-L-6-v2 (fast, free, good quality)
- Cohere Rerank (paid, excellent quality)
- BGE Reranker (open source, strong quality)

Typical pipeline: retrieve top-20 → rerank → return top-3

## Evaluation Metrics for RAG

### Retrieval metrics
- Recall@k: Were the relevant chunks in the top-k results?
- Precision@k: Of the top-k results, how many were relevant?
- MRR (Mean Reciprocal Rank): How highly ranked was the first relevant result?

### Generation metrics
- Faithfulness: Does the answer stick to the retrieved context?
- Answer relevance: Does the answer actually address the question?
- Context utilization: Did the model use the retrieved context?

## Common RAG Failure Modes
1. Retrieval failure: Right answer not in top-k retrieved chunks
2. Context window overflow: Too many chunks, model loses early context
3. Hallucination despite context: Model ignores context, makes things up
4. Chunk boundary issues: Answer spans two chunks, neither has full info
5. Query-document mismatch: Query phrased differently than document language