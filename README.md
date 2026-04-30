# 🚀 Badho AI — Agentic Career Coach

> A **streaming, tool-using, RAG-powered AI system** that guides engineers into AI careers —
> built from scratch with no LangChain, no LlamaIndex, direct SDK calls throughout.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Anthropic](https://img.shields.io/badge/Claude-Haiku%204.5-CC785C?style=flat&logo=anthropic&logoColor=white)](https://anthropic.com)
[![OpenAI](https://img.shields.io/badge/Embeddings-text--embedding--3--small-412991?style=flat&logo=openai&logoColor=white)](https://openai.com)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-FF6B35?style=flat)](https://trychroma.com)
[![Railway](https://img.shields.io/badge/Deployed-Railway-0B0D0E?style=flat&logo=railway&logoColor=white)](https://railway.app)
[![Total Cost](https://img.shields.io/badge/3--Day%20API%20Cost-$2.70-27AE60?style=flat)](https://anthropic.com)

---

## 🧠 What This Actually Is

This is **not a ChatGPT wrapper**.

This is a **controlled agentic AI system** that:

- 📚 Uses **RAG** to ground every answer in a curated 15-document career corpus
- 🔧 Dynamically **decides when to call tools** via the Anthropic tool-use API
- 🧵 Maintains **multi-turn conversation context** with automatic summarization at 12 turns
- 📊 Enforces quality via a **12-case eval suite** — programmatic + LLM-as-judge
- ⚡ Tracks **per-request latency and cost** with a live `/metrics` endpoint
- 🛡️ Implements **fallback model + per-conversation $0.10 budget cap**
- 🔄 Streams **true token-level SSE** — one frame per text delta, not chunked

> 💡 **Real cost signal:** The entire 3-day project — development, debugging the
> agentic loop, running evals, and demo recording — cost **$2.70 in API calls**.
> This is intentional. **Claude Haiku 4.5** at $0.80/1M input tokens makes
> production-grade AI engineering accessible without sacrificing quality
> for a career coaching use case.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vanilla HTML/JS)                │
│         SSE token stream · tool badges · /metrics UI        │
└──────────────────────────┬──────────────────────────────────┘
                           │  POST /chat/stream (SSE)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Gateway                         │
│         /chat/stream   /metrics   /health   GET /           │
│              budget guard · session routing                 │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│     RAG Pipeline     │    │      Agent Controller           │
│ ─────────────────── │    │      (app/core/llm.py)          │
│  1. Embed query      │    │ ─────────────────────────────── │
│  2. ChromaDB search  │    │  • Prompt construction          │
│     (top-10)         │    │  • Multi-turn context injection │
│  3. Cross-encoder    │    │  • Tool-use loop (max 5 iters)  │
│     rerank (top-3)   │    │  • Token-level streaming        │
│  4. Format context   │    │  • TTFT measurement             │
│  5. Inject to prompt │    │  • Fallback model swap          │
└──────────┬───────────┘    └──────────────┬──────────────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│      ChromaDB        │    │         Tool Engine             │
│  (Vector Store)      │    │      (app/core/tools.py)        │
│ ─────────────────── │    │ ─────────────────────────────── │
│  • 15 documents      │    │  🔍 lookup_role()               │
│  • ~95 chunks        │    │  💰 estimate_salary_range()     │
│  • 1536-dim vectors  │    │  📊 score_job_fit()             │
│  • cosine similarity │    │  🗺️  generate_career_roadmap()  │
└──────────────────────┘    └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │         Model Layer             │
                            │ ─────────────────────────────── │
                            │  Primary : Claude Haiku 4.5     │
                            │  Fallback: Claude Sonnet 4.6    │
                            │  (auto-swap on 529/rate limit)  │
                            └──────────────┬──────────────────┘
                                           │
┌──────────────────────────────────────────▼──────────────────┐
│              Telemetry Layer (In-Memory Aggregation)        │
│  • Input/output tokens    • Cost per turn ($)               │
│  • TTFT ms                • Tool latency ms per call        │
│  • Retrieval ms           • Rerank ms                       │
│  • Budget tracking        • GET /metrics  (p50/p95 TTFT)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 End-to-End Request Flow

```
User message
     │
     ▼
[1] Budget check ──────────────► Over $0.10? → stream error, stop
     │
     ▼
[2] RAG retrieval
     │  embed query (OpenAI text-embedding-3-small)
     │  vector search top-10 (ChromaDB)
     │  cross-encoder rerank → top-3
     │  emit: SSE  event: retrieval_done
     ▼
[3] Summarize if needed (>12 turns → Haiku 4.5 compression call)
     │
     ▼
[4] Agentic tool-use loop (max 5 iterations)
     │
     ├─► LLM call (non-streaming) to detect intent
     │
     ├─► stop_reason == "tool_use"?
     │       │
     │       ├─ emit: SSE  event: tool_called  {tool_name, input}
     │       ├─ execute tool
     │       ├─ emit: SSE  event: tool_done    {latency_ms, status}
     │       └─ append result to history → loop back
     │
     └─► stop_reason == "end_turn"?
             │
             └─ switch to streaming mode
                emit: SSE  event: token  (one frame per text delta)
                emit: SSE  event: done   {total_ms, ttft_ms, cost_usd}
     │
     ▼
[5] Update in-memory session state + user profile
[6] Record turn in telemetry store
```

---

## ⚡ Key Features

### 🔧 Agentic Tool System

The LLM dynamically decides which tool to call based on user intent.
No hardcoded routing — the Anthropic tool-use API selects from schemas.

| Tool | Trigger | Output |
|------|---------|--------|
| `lookup_role()` | "What does an AI engineer do?" | RAG-backed role info with citations |
| `estimate_salary_range()` | "What salary in Bangalore with 4 YoE?" | Structured range with YoE multiplier applied |
| `score_job_fit()` | "Am I a good fit for AI roles?" | JSON: fit 0–100, strengths, gaps, recommendation |
| `generate_career_roadmap()` | "Give me a 90-day plan" | JSON: day_30/60/90 goals + actions |

Tool calls are visible in the SSE stream as `tool_called` and `tool_done` events
with individual latency measurements — not hidden, not post-processed.

---

### 📚 RAG Pipeline

**Corpus:** 15 curated documents — 8 original, 7 scraped with attribution headers.
Topics: role comparisons, salary data, JDs, interview prep, transition guides, career stories.

**Chunking strategy:** 512 tokens, 64-token overlap, `tiktoken` (`cl100k_base`).

| Design choice | Reasoning |
|---|---|
| 512 tokens | Captures a complete career concept without fragmentation |
| 64 overlap | Concepts spanning chunk boundaries stay retrievable by both adjacent chunks |
| `cl100k_base` | Consistent tokenization with the OpenAI embedding model |

**Two-stage retrieval:**
```
query → embed → ChromaDB top-10 (recall) → cross-encoder rerank → top-3 (precision)
```

Embedding similarity casts wide for recall. The cross-encoder
(`cross-encoder/ms-marco-MiniLM-L-6-v2`) re-scores query+document pairs jointly
for precision. Without reranking, top results often mention the keyword but
don't answer the question.

**What I would change with more time:**
- Offline Recall@3 eval with a 50-question golden dataset
- Hybrid search: BM25 + vector for better exact-term matching on role names
- Semantic chunking for section-structured documents

---

### 🧵 Multi-Turn Conversation State

State lives **in-memory** — a deliberate choice for fast iteration and
zero infrastructure overhead at demo scale:

```python
session = {
    "messages"    : [...],       # full Anthropic message history
    "summary"     : "...",       # compressed older turns (after 12 turns)
    "user_profile": {            # extracted facts accumulated across turns
        "current_role"      : "backend engineer",
        "years_experience"  : 4,
        "target_role"       : "AI engineer",
        "location"          : "Bangalore"
    },
    "budget_used" : 0.042,       # running $ total
    "turn_count"  : 7
}
```

**Summarization trigger:** At 12 turns, a single Haiku 4.5 call compresses
older messages into ~150 words. Full history replaced with summary + last 4
raw turns — context window stays manageable.

**Profile extraction:** Per-turn Haiku call extracts structured career facts
and merges them into `user_profile`. Tools use this without re-reading history.

---

### 📊 Telemetry (In-Memory)

All metrics run **in-memory** — aggregated on demand at `GET /metrics`.
Chosen for simplicity: no SQLite, no file I/O, zero dependencies.
The tradeoff: metrics reset on server restart, which is acceptable for a demo.

**`GET /metrics` response:**
```json
{
  "total_turns"         : 47,
  "total_sessions"      : 12,
  "ttft_p50_ms"         : 420,
  "ttft_p95_ms"         : 890,
  "total_cost_usd"      : 0.094,
  "avg_cost_per_session": 0.0078,
  "avg_retrieval_ms"    : 145,
  "avg_llm_ms"          : 1240,
  "most_used_tools"     : ["estimate_salary_range", "generate_career_roadmap"],
  "status"              : "healthy"
}
```

**Status field:** `healthy` if p95 TTFT < 1500ms, `degraded` if not.

---

### 💰 Real Cost Breakdown

> The complete 3-day project — development, debugging, 4 eval runs,
> and demo recording — cost **$2.70 total in API calls**.

| Activity | Cost |
|---|---|
| Corpus ingestion (5 re-runs during dev) | < $0.01 |
| Day 1 — RAG pipeline + streaming dev | ~$0.30 |
| Day 2 — Agentic loop debugging + tools | ~$1.20 |
| Day 3 — Eval suite (×4 runs) + demo | ~$1.20 |
| **Total** | **$2.70** |

**Claude Haiku 4.5** ($0.80/1M input, $4.00/1M output) made 3 days of
intensive development cost less than a coffee. **Claude Sonnet 4.6** as
fallback — triggered only on deliberate overload testing.

---

### ⏱️ Latency Benchmarks

| Environment | p50 TTFT | p95 TTFT | Target |
|---|---|---|---|
| Local (development) | ~380ms | ~820ms | < 1500ms ✅ |
| Deployed (Railway) | ~650ms | ~1200ms | < 1500ms ✅ |

*TTFT = time from request received to first SSE `event: token` sent.
Measured over 10 requests, no cache warming.*

---

### 🛡️ Fallback Model

```python
try:
    async with client.messages.stream(model="claude-haiku-4-5", ...):
        ...
except anthropic.APIStatusError:          # 529 overload / rate limit
    active_model = "claude-sonnet-4-6"   # upgrade transparently
    yield sse("info", {"message": "Switched to fallback model"})
    async with client.messages.stream(model=active_model, ...):
        ...
```

Switch is logged in telemetry (`model_used` field) and visible as
an `info` SSE event in the client stream.

---

## ✅ Eval Suite

12 test cases. Run with `python evals/run_evals.py`.

| Category | Count | Method | What it tests |
|---|---|---|---|
| Factual | 3 | Programmatic | Source citation, salary figures, 3+ skill keywords |
| Reasoning | 3 | LLM-as-judge | Concrete recommendations, multi-dimension analysis |
| Multi-turn | 2 | LLM-as-judge | Context persistence, early constraint respect |
| Adversarial | 2 | Programmatic | Off-topic refusal, prompt injection resistance |
| Tool-use | 2 | Programmatic | Correct tool firing checked via SSE event stream |

**Programmatic:** keyword/regex on response text + SSE events. Deterministic, zero cost.

**LLM-as-judge:** Single Haiku 4.5 call scores 0 or 1 against explicit written criteria.
Non-deterministic — explicitly labelled in the report.

```
EVAL RESULT: 12 / 12 ✅     Suite cost: ~$0.05
```

**Honest weaknesses:**
- LLM-as-judge non-determinism — human labels would be more reliable
- No isolation Recall@3 — retrieval quality is inferred not measured
- 2 adversarial cases is shallow — production needs 20+
- Tool firing has phrasing-dependent edge cases

---

## 🗂️ Project Structure

```
badho-ai/
├── app/
│   ├── main.py                 # FastAPI entry, lifespan, router mounting
│   ├── routers/
│   │   ├── chat.py             # POST /chat/stream — SSE endpoint
│   │   ├── metrics.py          # GET /metrics
│   │   └── health.py           # GET /health
│   ├── core/
│   │   ├── llm.py              # Agentic tool-use loop + streaming
│   │   ├── rag.py              # Retrieve + cross-encoder rerank
│   │   ├── tools.py            # 4 tools + TOOL_SCHEMAS + executor
│   │   ├── state.py            # In-memory session state + summarization
│   │   ├── telemetry.py        # In-memory telemetry + /metrics aggregation
│   │   └── budget.py           # Per-conversation $0.10 budget guard
│   └── models/
│       └── schemas.py          # Pydantic models for all I/O
├── corpus/                     # 15 .md career documents
├── evals/
│   ├── test_cases.py           # 12 structured test cases
│   └── run_evals.py            # Runner → writes EVAL_REPORT.md
├── frontend/
│   └── index.html              # Vanilla HTML/JS SSE chat UI
├── tests/
│   ├── test_budget.py          # Budget guard unit tests
│   └── test_multi_turn.py      # Multi-turn coherence tests
├── ingest.py                   # Corpus → ChromaDB (re-runnable)
├── EVAL_REPORT.md              # Auto-generated by run_evals.py
├── POSTMORTEM.md
├── requirements.txt
├── runtime.txt                 # python-3.11.x for Railway
└── .env.example
```

---

## ⚙️ Local Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/badho-ai
cd badho-ai

# 2. Virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Mac / Linux:
# source venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Add ANTHROPIC_API_KEY and OPENAI_API_KEY

# 5. Build vector index
python ingest.py
# → "Ingested X chunks from 15 documents"

# 6. Run
uvicorn app.main:app --reload
# Open http://localhost:8000
```

---

## 🔑 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | required |
| `OPENAI_API_KEY` | OpenAI key (embeddings only) | required |
| `PRIMARY_MODEL` | `claude-haiku-4-5` | required |
| `FALLBACK_MODEL` | `claude-sonnet-4-6` | required |
| `CHROMA_PATH` | ChromaDB local path | `./chroma_db` |
| `MAX_BUDGET_USD` | Per-conversation cap | `0.10` |
| `ENV` | `local` or `production` | `local` |

---

## 🚀 Deployment (Railway)

```
Live at: https://YOUR-URL.railway.app
```

1. Push repo to GitHub (public)
2. Railway → New Project → Deploy from GitHub
3. Add all env vars in Railway Variables tab
4. Railway runs `bash start.sh` → `python ingest.py` → `uvicorn`
5. Settings → Generate Domain → public HTTPS

---

## ⚠️ Known Limitations — Honest Tradeoffs

| Limitation | Why accepted | Production fix |
|---|---|---|
| **In-memory session state** | Zero infra, fast dev iteration | Redis with TTL |
| **In-memory telemetry** | Same — resets on restart, fine for demo | Append log or SQLite |
| **Single-node ChromaDB** | Free, zero-config, demo scale | Qdrant Cloud / pgvector |
| **Static salary data** | Illustrative — not a live product | Quarterly refresh pipeline |
| **No authentication** | Public demo scope | JWT + user identity |
| **Sync tool execution** | Simpler loop logic | `asyncio.gather()` |

Every item above was a **conscious tradeoff**, not an oversight.
A 3-day constraint forces prioritisation — deeper LLM engineering over infra polish.

---

## 🔮 Week 2 Roadmap

1. **Redis session store** — persistent context, TTL-based expiry
2. **Offline retrieval eval** — 50 golden Q&A pairs, Recall@3 measurement
3. **Resume PDF builder** — WeasyPrint, base64 download, from accumulated profile
4. **Semantic caching** — near-duplicate query detection (~30% cost reduction)
5. **Async parallel tools** — `asyncio.gather()` across tool calls in one turn

---

## 🧠 Interview Talking Points

> *"I built a deterministic agentic system where the LLM orchestrates tool calls
> via Anthropic's native tool-use API — no LangChain, no abstractions.
> The loop detects `stop_reason == tool_use`, executes tools, appends results
> to message history, and iterates — hard-capped at 5 to prevent runaway costs.
> Every tool call emits an SSE event with individual latency, visible in real time.
> The hardest part was the raw SDK message structure for multi-turn tool-use —
> the assistant message must include full content blocks, not just text.
> Frameworks hide this. Building without them forces you to understand it.
> The entire 3-day build including all debugging and eval runs cost $2.70."*

---

## 📦 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI | Async-native, `StreamingResponse` for SSE, Pydantic |
| LLM primary | Claude Haiku 4.5 | $0.80/1M input — lowest cost, fastest TTFT |
| LLM fallback | Claude Sonnet 4.6 | Higher quality on overload events |
| Embeddings | OpenAI text-embedding-3-small | $0.02/1M tokens, 1536-dim |
| Vector store | ChromaDB | Zero-config, cosine similarity, persistent |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Free, strong precision lift |
| Session + telemetry | In-memory Python | Zero dependencies, demo-scale appropriate |
| Deployment | Railway.app | Free tier, GitHub deploy, auto-HTTPS |

---

## 👨‍💻 Author

**Abhinav Jajoo**
AI + Data Engineer Take-Home — Nudgit / Badho AI

---

*No LangChain. No LlamaIndex. No magic. Direct SDK calls throughout.*
*Total API cost across 3 days of development: **$2.70.***
