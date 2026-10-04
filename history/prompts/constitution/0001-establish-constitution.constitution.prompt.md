---
id: 0001
title: Establish Project Constitution
stage: constitution
date: 2026-10-05
surface: agent
model: gemini-3.8-flash
feature: none
branch: master
user: Zainab Ashraf
command: /sp.constitution
labels: [constitution, principles, reliability, verification, anti-hallucination, sdd]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - constitution.md
tests: []
---

## Prompt

```text
Research Brief Agent i have added project folder in project section use it and also use these . Start using slash commands with your AI agent:                                                                   │
│     2.1 /sp.constitution - Establish project principles                                                              │
│     2.2 /sp.specify - Create baseline specification                                                                  │
│     2.3 /sp.plan - Create implementation plan                                                                        │
│     2.4 /sp.tasks - Generate actionable tasks                                                                        │
│     2.5 /sp.implement - Execute implementation 
and work carefully history should be added just do it step by step
```

## Response snapshot

Ratified the initial Project Constitution (v1.0.0) for the Research Brief Agent at `.specify/memory/constitution.md` and `constitution.md`. Defined the 6 core non-negotiable principles:
1. Traceability Over Fluency (every claim cited, uncited claims dropped)
2. Verification is the Feature (independent verifier, explicit verdicts)
3. Strict Number Exactness & Negation Preservation (exact quantities inside window, negation count matching)
4. Free-Tier Resilience & Hard Call Budgets (max 7 calls, pacing, QuotaExhausted fast-fail)
5. Multi-Tenant Key Isolation & Prompt Injection Defense (no os.environ, untrusted web data boundary)
6. Independent Ground-Truth Evaluation (35 human-labeled claims, 25 dev / 10 held-out)

## Outcome

- ✅ Impact: Ratified Research Brief Agent Constitution v1.0.0 establishing production-grade reliability, security, and verification principles.
- 🧪 Tests: None (governance & principles phase).
- 📁 Files: `.specify/memory/constitution.md`, `constitution.md`
- 🔁 Next prompts: `/sp.specify` - Create baseline specification
- 🧠 Reflection: Codifying anti-hallucination rules and free-tier economics as constitutional principles ensures all downstream code, prompts, and evals strictly adhere to verification discipline.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Run `/sp.specify` to generate baseline specification for the research pipeline.
