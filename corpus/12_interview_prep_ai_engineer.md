# SOURCE: original
# SCRAPED: n/a
# LICENSE: original

# AI Engineer Interview Preparation Guide

## The 5 Categories of AI Engineer Interviews

### 1. LLM System Design (most common at Series A-C)
You will be given a product scenario and asked to design an AI system.
Example: "Design a customer support AI for an e-commerce company."

Framework to answer:
a) Clarify requirements: volume, latency, accuracy requirements, budget
b) Architecture: what components, what models, how they connect
c) Data: what corpus, how ingested, how kept fresh
d) Retrieval: embedding model, vector store, chunking strategy
e) Generation: model choice, system prompt structure, output validation
f) Evaluation: how do you know it's working? what metrics?
g) Cost: estimate tokens/query, monthly cost at scale, optimization levers
h) Failure modes: what breaks, how to detect, how to fallback

### 2. ML Fundamentals
Even if the role is LLM-focused, expect basics:
- What is a transformer? (attention mechanism, encoder/decoder)
- What are embeddings? (geometric intuition, dimensionality)
- What is fine-tuning vs RAG? (when to use each, tradeoffs)
- What is overfitting? (regularization, dropout, early stopping)
- Bias-variance tradeoff

### 3. Coding Interviews for AI Roles
Not typical LeetCode — expect:
- "Build a simple RAG pipeline" (live coding)
- "Write a function to chunk text by semantic boundaries"
- "Implement retry logic with exponential backoff for LLM API calls"
- "Write an eval function that uses an LLM as judge"

### 4. Past Project Deep Dive
They will ask: "Tell me about the most complex AI system you built."
Prepare a 10-minute story covering:
- The problem and why AI was the right solution
- Architecture decisions and why you made them
- The hardest technical problem you hit and how you solved it
- How you evaluated success
- What you would do differently

### 5. Behavioral for AI Roles
- "Tell me about a time your AI system failed in production"
- "How do you decide when to use a bigger model vs smaller model?"
- "How do you communicate AI uncertainty to non-technical stakeholders?"
- "Tell me about a time you improved AI quality through better evaluation"

## Questions to Ask the Interviewer
- What does your AI evaluation process look like?
- What is your biggest AI quality challenge right now?
- How do you decide between building vs buying AI capabilities?
- What is the ratio of AI infra work to AI feature work on this team?