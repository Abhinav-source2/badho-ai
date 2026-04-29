# SOURCE: https://www.techinterviewhandbook.org/resume/
# SCRAPED: 2024-01-15
# LICENSE: fair-use-educational

# Technical Resume Writing Guide (AI/ML Focus)

## The FAANG Resume Format
The clean single-column resume format used by top tech companies has become
the industry standard. Key principles:
- Single page for under 10 years experience
- Reverse chronological order
- Bullet points starting with strong action verbs
- Every bullet must have a measurable outcome

## Action Verbs That Work for AI Roles
Built, Designed, Implemented, Optimized, Reduced, Increased, Deployed,
Architected, Evaluated, Fine-tuned, Integrated, Automated, Shipped, Led,
Improved, Developed, Created, Scaled, Migrated, Refactored

## The XYZ Formula (Google's recommended format)
"Accomplished [X] as measured by [Y], by doing [Z]"

Examples for AI engineers:
- "Reduced customer support ticket volume by 34% (measured by monthly ticket
  count) by building RAG-powered chatbot using GPT-4 and ChromaDB"
- "Improved retrieval accuracy by 28% (measured by RAGAS faithfulness score)
  by implementing cross-encoder reranking on top of vector search"
- "Cut LLM inference costs by 60% (measured by monthly API spend) by
  migrating from GPT-4 to fine-tuned GPT-4o-mini for classification tasks"

## Skills Section for AI Engineer Roles
Order matters — put most relevant first.

For AI Engineer applying to LLM-focused roles:
Languages: Python, SQL
AI/ML: LLM APIs (Anthropic Claude, OpenAI GPT-4), RAG, Embeddings,
       Vector Databases (Qdrant, ChromaDB), Prompt Engineering
Frameworks: FastAPI, PyTorch, scikit-learn, Hugging Face Transformers
Infrastructure: Docker, AWS/GCP, PostgreSQL, Redis, GitHub Actions

## Red Lines — Never Do These
- Never list a skill you cannot be interviewed on in the next 48 hours
- Never use vague phrases: "worked on AI projects", "familiar with ML"
- Never skip GitHub link if you have public AI projects
- Never include a photo (in US/UK resumes)
- Never use tables or columns — ATS systems cannot parse them

## ATS Keywords for AI Engineer 2024
machine learning, artificial intelligence, LLM, large language model,
GPT, Claude, Gemini, RAG, retrieval augmented generation, vector database,
embeddings, semantic search, prompt engineering, fine-tuning, MLOps,
model evaluation, Python, FastAPI, transformer, RLHF, LangChain

## Portfolio Projects Section
If you have under 2 years of AI experience, a strong projects section
outweighs additional work experience bullet points.

Each project entry needs:
1. Project name (linked to GitHub)
2. Tech stack in parentheses
3. One line: what it does
4. One line: scale and metrics

Example:
CareerCoach AI (FastAPI, Anthropic Claude, ChromaDB, Qdrant)
RAG-powered career coaching API with streaming responses and tool use.
Deployed on Railway — p95 TTFT 820ms, $0.003/conversation avg cost.