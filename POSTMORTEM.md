# 🧠 POSTMORTEM.md — Badho AI Agentic Career Coach

---

## What I Cut — and Why

**Resume PDF builder tool** (~4 hrs estimated) — cut to protect time for the eval suite.
A downloadable PDF is a visible feature. A validated agentic loop is a system.
I chose system depth over surface-area. Wrong call for a demo, right call for production.

**Qdrant Cloud as vector store** — stayed with local ChromaDB throughout.
External vector DB adds network latency per query and cold-start complexity on
Railway's free tier. ChromaDB gave faster iteration and lower p95 TTFT.
Would switch to Qdrant or pgvector the moment the system needs horizontal scaling.

**Offline retrieval eval (Recall@3)** — no golden Q&A dataset was built.
RAG quality is validated only indirectly through end-to-end eval cases.
This is the biggest blind spot in the current system. A 50-question golden
dataset with isolated retrieval scoring would have caught chunking issues
independently of generation quality.

---

## What I Would Never Ship As-Is

**In-memory session state.** On any pod restart or redeployment, all active
conversation context is permanently and silently lost. A user mid-conversation
gets a completely amnesiac assistant with no warning or graceful degradation.
Production fix: Redis with 24-hour TTL. One day of work. Consciously deferred
to spend time on the agentic loop and eval suite instead.

**In-memory telemetry.** Metrics reset on restart — meaning the `/metrics`
endpoint shows only data from the current process lifetime. Acceptable for a
demo where you control the server. Unacceptable in production where restarts
happen during deployments. Fix: append-only log file or SQLite — two hours of work.

---

## What Was Actually Hard

**The agentic tool-use loop.** The concept is simple — detect `tool_use`,
execute, append, loop. The raw SDK reality is not. The assistant message must
include the full content blocks array including `tool_use` blocks, not just
the text. Tool results must reference the exact `tool_use_id`. Getting this
wrong produces silent failures — the model just stops using tools. LangChain
hides all of this. Building without it forces you to understand every byte
of the message structure. That understanding is the point.

**Tool reliability.** The model inconsistently triggered tools when user
phrasing didn't match tool descriptions closely. Fixed via explicit system
prompt instructions per tool category and heuristic gating for the roadmap
tool. The lesson: optional tools are unreliable tools. Critical tools need
explicit triggering logic in code, not just prompts.

**Multi-turn context.** Even with full message history passed, the model
ignored prior context in longer conversations. Fix: inject a structured
context summary into the final user message before inference. Context
reinforcement via code, not trust in the model's attention.

---

## What I Would Do Differently

**Start with the eval suite.** I built features first, then wrote tests.
The right order is: define what "working" means, write the evals, then build
until they pass. Eval-first forces precision about requirements before a line
of application code is written.

**Design tool contracts first.** Tools were added as the system grew.
They should have been defined as first-class interfaces on Day 1 —
input schemas, output schemas, failure modes — before any implementation.
This would have made the agentic loop cleaner and the tests more targeted.

---

## Week 2 — What I Would Build

| Priority | Feature | Why |
|---|---|---|
| 1 | Redis session store | Eliminate the one thing I'd never ship |
| 2 | Offline Recall@3 eval | Close the biggest quality blind spot |
| 3 | Semantic caching | ~30% cost reduction on repeated queries |
| 4 | Resume PDF builder tool | The feature I cut that users would actually want |
| 5 | Async parallel tool calls | `asyncio.gather()` — latency improvement when multiple tools fire |

---

