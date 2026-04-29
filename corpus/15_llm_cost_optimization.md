# SOURCE: original
# SCRAPED: n/a
# LICENSE: original

# LLM Cost Optimization for Production AI Systems

## Why Cost Matters
At 1,000 queries/day with GPT-4: ~$50-200/day = $18,000-73,000/year.
At 1,000 queries/day with Haiku: ~$2-8/day = $730-2,920/year.
Model selection alone is a 10-25x cost lever.

## The Cost-Quality-Latency Triangle
Every optimization decision sits in a triangle:
- Optimize for cost → quality or latency may suffer
- Optimize for quality → cost and latency increase
- Optimize for latency → cost may increase (larger instance/cache)

The right operating point depends on your use case. Support chatbots can
tolerate lower quality. Medical AI cannot. Know your requirements before
optimizing.

## Model Selection Strategy
Use the cheapest model that meets your quality bar. Test in this order:
1. Start with the cheapest (Haiku, GPT-4o-mini, Gemini Flash)
2. Run your eval suite — measure quality
3. If quality meets bar, ship it
4. If not, upgrade to next tier and repeat

Never start with the most expensive model. You will anchor on that quality level
and never feel comfortable downgrading.

## Token Optimization Techniques

### System prompt compression
Audit your system prompt. Remove redundant instructions.
"Please make sure to always be helpful and answer questions in a friendly manner
and provide accurate information" → "Be helpful and accurate"
Savings: 20-40 tokens per request, multiplied by all requests.

### Context window management
Summarize conversation history rather than sending all messages.
Send only the last N turns raw + a summary of earlier turns.
Savings: 30-60% on long conversations.

### Caching
Cache responses for identical or near-identical queries.
Use semantic caching: if query embedding similarity > 0.95, return cached response.
Savings: 20-40% on repetitive query patterns.

### Retrieval optimization
Only send top-3 chunks, not top-10. Better retrieval quality = fewer chunks needed.
Savings: 300-700 tokens per request.

## Cost Tracking per Request
Log: input_tokens, output_tokens, model, timestamp, session_id.
Calculate: cost = (input_tokens * input_price) + (output_tokens * output_price)

Haiku pricing (2024): $0.80/1M input, $4.00/1M output
Sonnet pricing (2024): $3.00/1M input, $15.00/1M output
GPT-4o-mini: $0.15/1M input, $0.60/1M output

## Budget Caps
Implement hard budget caps per conversation and per user.
On cap exceeded: degrade to a cheaper model or refuse with a clear message.
Never let a single user or bug exhaust your monthly API budget.

## When to Fine-tune vs RAG
Fine-tune when: consistent style/format, domain-specific vocabulary,
shorter prompts possible after fine-tuning (saves tokens).
RAG when: frequently updated knowledge, need citations, knowledge is too large
for fine-tuning dataset.
Fine-tuning is often cheaper per-request but has high upfront cost.