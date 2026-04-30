# 🧠 POSTMORTEM.md — Badho AI (Agentic Career Coach)

This document captures the **engineering decisions, tradeoffs, failures, and lessons learned** while building a production-style agentic AI system.

This is not a feature list — it is a reflection of **what actually mattered technically**.

---

# 🎯 Project Goal

Build a **reliable, tool-using AI system** — not just a chatbot.

Constraints:
- No LangChain / LlamaIndex
- Must support RAG + tools + streaming
- Must behave deterministically (eval-driven)

---

# ❌ What I Deliberately Cut (and Why)

## 1. Resume PDF Generator Tool
**Estimated effort:** 3–4 hours  
**Why cut:**

- Would require:
  - HTML templating
  - WeasyPrint setup
  - binary streaming
- Adds **surface-level feature**, not system depth

**Decision:**
```text
Prioritized agent reliability + eval system over feature count
2. Qdrant / External Vector DB

Used instead: Local ChromaDB

Why:

External DB = network latency per query
Cold start issues on free-tier deployments
Added operational complexity

Tradeoff:

Scalability sacrificed → faster iteration + lower latency gained

Would switch to:

Qdrant / pgvector in production
3. Offline Retrieval Evaluation (Recall@K)

Skipped:

No golden dataset created
No independent retrieval scoring

Impact:

RAG quality is only validated indirectly via end-to-end tests

👉 This is the biggest blind spot in current system.

⚠️ What I Would NEVER Ship As-Is
1. In-Memory Session State

Current behavior:

Restart server → conversation lost

User impact:

Assistant becomes "amnesiac" mid-conversation

Production fix:

Redis with TTL (24 hours)
Session-based persistence
2. Static Salary Data
Hardcoded salary ranges
No real-time updates

Risk:

Data becomes outdated quickly

Production fix:

API integration OR scheduled refresh pipeline
3. No Authentication Layer
session_id is arbitrary
no user isolation

Risk:

Any user can access any session if ID is known
🔥 What Was Technically Hard (Real Challenges)
1. Agentic Tool Loop (Core Difficulty)

This looks simple conceptually:

User → LLM → Tool → LLM → Answer

Reality:

Message format must match Anthropic spec EXACTLY
Tool outputs must be injected correctly
Model may ignore tools even when needed
Problem:
Model inconsistently triggered tools
Solution:
Added heuristic tool gating
Added forced tool execution for roadmap queries
2. Tool Choice API Bug (Subtle but Critical)
Problem:
tool_choice = None

→ Anthropic API throws 400 error

Fix:
Only include tool_choice when required
Lesson:
APIs prefer "missing" over "null"
3. Multi-Turn Context Failure (Major Issue)
Problem:

Even with history passed, model ignored prior context

Root Cause:
LLMs don't reliably use history unless reinforced
Fix:
Inject previous user context into final message
Context → explicitly embedded → model forced to use it
4. Non-Deterministic Outputs
Problem:

Same query → different behavior
→ eval failures

Solution:
Built evaluation suite (12 cases)
Iteratively fixed:
tool triggering
citations
adversarial handling
📊 Evaluation System (Biggest Strength)
Coverage:
Category	Purpose
Factual	correctness + citations
Reasoning	decision quality
Multi-turn	memory consistency
Adversarial	safety
Tool-use	correct execution
Final Result:
12 / 12 PASS ✅
Why This Matters:
Most AI projects are demos  
This is a validated system
🧠 Key Engineering Insights
1. Prompt ≠ Control

Early mistake:

Tried solving everything via prompt

Reality:

Prompt = suggestion  
Code = guarantee
2. Tool Use Must Be Enforced (Sometimes)
Optional tools → unreliable
Critical tools → must be forced
3. Determinism is Hard in AI Systems
Small changes break behavior
Eval suite is essential
4. Agent Systems Are Stateful Systems
Memory is not optional
Context handling is core logic
🔄 What I Would Do Differently
1. Start with Evals First

Instead of:

Build → then test ❌

Better:

Define success → then build ✅
2. Design Tool System Earlier
Tool contracts should be first-class
Not added later
3. Separate Reasoning vs Execution Layers

Currently mixed:

LLM reasoning
tool orchestration

Would split:

planner → executor architecture
🚀 What I Would Build in Week 2
Redis-backed session memory
Offline retrieval eval (50+ golden Q&A)
Semantic caching (reduce cost ~30%)
Async tool streaming
User identity layer (auth + session binding)
🎯 Final Reflection

This project evolved from:

Chatbot → Agent → System

The biggest shift was:

Thinking in terms of SYSTEM BEHAVIOR, not responses
🧠 If I Had to Summarize in One Line

I built a deterministic agentic AI system by moving control from prompts to code, validated through a custom evaluation framework.