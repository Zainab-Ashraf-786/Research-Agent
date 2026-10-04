<!--
Sync Impact Report:
- Version change: [CONSTITUTION_VERSION] -> 1.0.0
- List of modified principles:
  - Added Principle I: Traceability Over Fluency (NON-NEGOTIABLE)
  - Added Principle II: Verification is the Feature
  - Added Principle III: Strict Number Exactness & Negation Preservation
  - Added Principle IV: Free-Tier Resilience & Hard Call Budgets
  - Added Principle V: Multi-Tenant Key Isolation & Prompt Injection Defense
  - Added Principle VI: Independent Ground-Truth Evaluation
- Added sections:
  - Technical Constraints & Stack
  - Development Workflow & Quality Gates
- Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ aligned
  - .specify/templates/spec-template.md: ✅ aligned
  - .specify/templates/tasks-template.md: ✅ aligned
- Follow-up TODOs: None. All placeholders resolved.
-->

# Research Brief Agent Constitution

This document defines the core principles, architectural boundaries, and non-negotiable quality rules for the Research Brief Agent project. Every specification, implementation plan, task list, prompt, and code change must comply with this constitution.

---

## Core Principles

### I. Traceability Over Fluency (NON-NEGOTIABLE)
- A factual claim without an explicit source citation must never appear in the final brief.
- The Writer stage must output structured JSON where every claim is an explicit object paired with its source citation IDs (`citation_ids`).
- Any claim generated without a valid citation ID is dropped prior to verification and recorded in pipeline telemetry (`dropped_uncited_claims`).
- A beautifully written but untraceable sentence is treated as a critical bug.

### II. Verification is the Feature
- The Verifier is an independent, non-optional pipeline stage that scrutinizes every claim against the exact quoted passages of cited sources.
- Every claim receives an explicit status badge in the final output:
  - `SUPPORTED`: The source quote directly and completely backs the claim, matching in scope and numbers.
  - `PARTIAL`: The source quote backs part of the claim, or the claim overstates or generalizes the evidence.
  - `UNSUPPORTED`: The source quote does not back the claim.
- Each verdict must include a concise, one-sentence explanatory reason and the supporting quote.
- Unsupported claims are flagged visibly in the UI and never quietly hidden or deleted by the verifier.

### III. Strict Number Exactness & Negation Preservation (Anti-Hallucination)
- **Exact Numeric Matching**: All quantities, currencies (e.g. `$25`), percentages (e.g. `15.5%`), and dates in an extracted quote or claim must exist verbatim in the local matched source window. A claim of `"$25/month"` must instantly fail verification if the source text states `"$20/month"` or `"$250/month"`.
- **Negation Count Preservation**: Negation words (`not`, `no`, `never`, `none`, `without`, `cannot`, and contractions ending in `n't`) must match exactly in frequency between the quote and source text window to prevent semantic inversion.
- **Honesty Over Plausibility**: If sources conflict or evidence is missing, the brief must explicitly state "not found" or report the discrepancy in a dedicated `Gaps and Conflicts` section.

### IV. Free-Tier Resilience & Hard Call Budgets
- The pipeline is engineered to operate reliably on free-tier LLM API endpoints and Tavily search:
  - Maximum 5 search queries per run.
  - Maximum 8 unique deduplicated sources.
  - Sources are budgeted at $\le 3,500$ characters and batched in groups of 3 during extraction.
  - **Hard ceiling of at most 7 LLM calls per research run**.
  - Pacing enforced by a minimum inter-call delay (`LLM_MIN_INTERVAL_SECONDS = 2.0s`).
- Transient errors (`HTTP 429` rate limits, connection timeouts) retry up to 3 times with exponential backoff (2s, 4s, 8s).
- Daily quota exhaustion errors (`QuotaExhausted`) short-circuit immediately with a clean, friendly error message—never an unhandled exception or crash.

### V. Multi-Tenant Key Isolation & Prompt Injection Defense
- **Zero os.environ Key Storage**: Bring-Your-Own-Key (BYOK) inputs reside strictly in temporary UI session state (`st.session_state`) and are passed explicitly via immutable `LLMConfig` and `SearchConfig` objects. No user-supplied API key is ever written to `os.environ` or persistent storage.
- **Untrusted Web Isolation**: Web page content is treated strictly as untrusted data, never instructions. Prompts must include an explicit security boundary instructing models to ignore commands, system overrides, or directives embedded in scraped web text.

### VI. Independent Ground-Truth Evaluation
- Self-grading LLM evaluation is rejected as circular.
- The evaluation suite relies on a human-labeled ground-truth benchmark of 35 diverse claims (`eval/labeled_claims.json`) partitioned into:
  - **25 Dev Claims**: Used for verifier prompt engineering and error analysis.
  - **10 Held-Out Claims**: Strictly isolated from prompt development to evaluate out-of-sample generalization.
- The evaluation harness (`eval/run_eval.py`) measures and publishes:
  - Verifier Agreement Rate and Confusion Matrix against human labels (highlighting false-`SUPPORTED` rates).
  - End-to-end Fact Recall against expected ground-truth facts across 10 benchmark queries.
  - Citation Rate, Supported Rate, and Uncited-Claim Drop Rate.

---

## Technical Scope & Constraints

### In Scope (MVP)
- Single research topic/question input via web interface.
- Automated web search and URL deduplication via Tavily free tier.
- Page text cleaning and character budgeting.
- Source-batched atomic fact extraction with quote verification (`match_quote.py`).
- Structured brief generation using extracted facts only.
- Batched claim verification producing per-claim verdicts and reasons.
- Streamlit web UI supporting BYOK mode, interactive verdict badges, quote drill-downs, and 3 pre-saved offline example briefs.
- Markdown export of the completed brief.
- Automated test suite (`pytest`) and evaluation harness (`eval/run_eval.py`).

### Out of Scope (Deferred to Future Work)
- Heavy orchestration frameworks (LangChain, CrewAI, AutoGen).
- Persistent relational databases and user accounts.
- Document/PDF file uploads.
- Background asynchronous workers or recurring cron jobs.
- Multi-turn conversational memory.

---

## Development Workflow & Quality Gates

1. **Test-First Engine Validation**: Core trust mechanisms (`match_quote.py`, `llm.py` backoff, schema validation) must have complete unit test coverage before stage assembly.
2. **Deterministic Data Contracts**: All data crossing pipeline boundaries must conform to typed Pydantic models (`Source`, `Fact`, `Claim`, `ClaimVerdict`, `FinalBrief`).
3. **Graceful Degradation**: If sources are thin or unavailable, the pipeline must return a structured "insufficient evidence" response rather than failing or hallucinating.
4. **Offline Demo Readiness**: The UI must allow reviewers to evaluate 3 complete pre-saved briefs without supplying API keys or consuming live quotas.

---

## Governance

- This constitution is the ultimate source of truth for the project. Code or prompts that violate these principles must be amended or the constitution revised deliberately.
- Any amendment requires updating this document, logging the rationale in the amendment history below, and verifying all dependent templates remain in synchronization.

**Version**: 1.0.0 | **Ratified**: 2026-10-05 | **Last Amended**: 2026-10-05

### Amendment Log
| Version | Date | Description | Rationale |
|---|---|---|---|
| 1.0.0 | 2026-10-05 | Initial ratification of Research Brief Agent Constitution | Codify reliability, verification, anti-hallucination, and free-tier operational rules. |
