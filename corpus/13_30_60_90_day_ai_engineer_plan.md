# SOURCE: original
# SCRAPED: n/a
# LICENSE: original

# 30-60-90 Day Plan for a New AI Engineer

## Days 1-30: Learn the Codebase and Ship One Thing

### Week 1: Orientation
- Shadow every system: data pipelines, model serving, evaluation runs
- Read all AI-related code, even if you don't understand it yet
- Map out the full AI stack: what models, what stores, what eval metrics
- Ask: "What is the most painful AI quality problem right now?"

### Week 2: First Contribution
- Pick the smallest meaningful task in the AI codebase
- Fix a bug, improve a prompt, add a test case — something real
- Ship it through the full process: code review, staging, production
- The goal is to learn the deploy process, not to change the world

### Week 3-4: Understand the Eval System
- Run the existing eval suite end-to-end
- Add 3 new test cases that expose real failure modes
- Write a document: "State of AI Quality" — what works, what doesn't
- Present it to the team — even 5 minutes at a standup

### 30-Day Deliverable
One shipped improvement (no matter how small) + evaluation report

## Days 31-60: Own a Feature

### Week 5-6: Take Ownership
- Identify one AI feature to own completely
- Write the spec: problem, success metrics, approach, risks
- Build it with TDD: write evals before building the feature
- Iterate based on eval results, not gut feeling

### Week 7-8: Production Stability
- Add monitoring for your feature: latency, cost, quality drift
- Define alert thresholds
- Write a runbook: what to do when this feature degrades

### 60-Day Deliverable
One fully owned feature in production with monitoring

## Days 61-90: Drive an Initiative

### Week 9-10: Identify a Leverage Point
- Based on 60 days of observation, identify one high-leverage improvement
- Could be: better retrieval, cheaper inference, faster evaluation
- Propose it with data: estimated impact, effort, risk

### Week 11-12: Execute and Measure
- Build the initiative, measure the outcome
- Document what you learned
- Present results to the team with honest assessment of what worked

### 90-Day Deliverable
One initiative with measurable impact + documentation