# Implementation Plan: Research Brief Agent

**Branch**: `001-research-brief-pipeline` | **Date**: 2026-10-05 | **Spec**: [specs/001-research-brief-pipeline/spec.md](file:///C:/Users/Zainab%20Ashraf/OneDrive/Desktop/Research%20Brief%20Agent/ResearchBriefAgent/specs/001-research-brief-pipeline/spec.md)  
**Input**: Feature specification from `specs/001-research-brief-pipeline/spec.md`

---

## Summary

Build an intermediate, reliable, and verifiable AI research brief generator that translates a research topic into a verified one-page summary. Every claim is bound to source citations and verified by an independent verification stage (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`). The system utilizes plain Python functions, Pydantic schemas, an OpenAI-compatible LLM gateway with strict rate-limit resilience ($\le 7$ calls per run), a hybrid quote matcher enforcing window-bounded numeric exactness and negation counts, and a Streamlit UI supporting both zero-quota pre-saved briefs and secure session-isolated BYOK mode.

---

## Technical Context

**Language/Version**: Python 3.10+ (tested on Windows 11)  
**Primary Dependencies**: `openai>=1.50.0`, `pydantic>=2.7.0`, `tavily-python>=0.5.0`, `streamlit>=1.35.0`, `python-dotenv>=1.0.0`, `pytest>=8.0.0`  
**Storage**: Local JSON disk cache for searches and URL extractions; 3 pre-saved JSON showcase briefs  
**Testing**: `pytest` for unit/mock test suites, `python eval/run_eval.py` for ground-truth benchmark  
**Target Platform**: Desktop browsers via Streamlit Community Cloud and local workstation execution  
**Project Type**: Python CLI library + Streamlit frontend application  
**Performance Goals**: Latency $< 90$ seconds per complete research brief; $\le 7$ LLM calls per run  
**Constraints**: Free-tier API compatible (Gemini, Groq, OpenRouter + Tavily free tier); zero `os.environ` pollution for user-supplied keys; strict numeric and negation verification  
**Scale/Scope**: Single-topic analyst briefs, 35 hand-labeled ground-truth evaluation claims, 10 benchmark test questions  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status | Verification Mechanism |
|---|---|---|---|
| **I. Traceability Over Fluency** | Every claim cites source IDs; uncited claims dropped | ✅ PASS | Writer emits structured JSON claims; pre-filter drops uncited claims before verification |
| **II. Verification is the Feature** | Per-claim verdicts (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`) + reasons | ✅ PASS | Independent batched Verifier stage with quote extraction |
| **III. Number Exactness & Negation** | Strict window number matching; negation word count equality | ✅ PASS | `match_quote.py` unit tested against number swaps and dropped negations |
| **IV. Free-Tier Resilience** | $\le 7$ LLM calls; pacing $\ge 2.0$s; fast-fail on daily quota | ✅ PASS | Batch 3 sources per extraction; pacing timer; custom retry distinguishing daily quota |
| **V. Multi-Tenant Key Isolation** | No `os.environ` key leakage; web prompt injection isolation | ✅ PASS | Keys passed strictly via `LLMConfig` dataclass; prompt injection guard headers |
| **VI. Independent Ground Truth** | 35 human-labeled claims (25 dev / 10 held-out) | ✅ PASS | Curated `eval/labeled_claims.json` with separate dev/held-out evaluation metrics |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-research-brief-pipeline/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Architecture decisions and trade-offs
├── data-model.md        # Pydantic entity specifications
├── quickstart.md        # Setup and run instructions
├── contracts/
│   └── pipeline-api.md  # Python programmatic API contract
└── tasks.md             # Actionable task list (/sp.tasks command)
```

### Source Code Layout

```text
ResearchBriefAgent/
├── constitution.md            # Ratified project constitution
├── README.md                  # Project overview, demo, and evaluation table
├── requirements.txt           # Minimal pinned dependencies
├── .env.example               # Provider configuration template
├── .gitignore                 # Git ignore for virtualenvs, caches, .env
├── app.py                     # Streamlit frontend with BYOK & 3 showcase briefs
├── agent/
│   ├── __init__.py
│   ├── config.py              # LLMConfig and SearchConfig frozen dataclasses
│   ├── schemas.py             # Pydantic models (Source, Fact, Claim, Brief, etc.)
│   ├── llm.py                 # OpenAI-compatible client with backoff & JSON repair
│   ├── match_quote.py         # Window-bounded number exactness & negation matching
│   ├── cache.py               # Disk cache for search queries & page text
│   ├── planner.py             # Stage 1: 3-5 query generation
│   ├── search.py              # Stage 2: Tavily search & URL deduplication
│   ├── reader.py              # Stage 3: Content cleanup & character budgeting
│   ├── extractor.py           # Stage 4: Batched source fact extraction + injection defense
│   ├── writer.py              # Stage 5: Structured brief generation & uncited filtering
│   ├── verifier.py            # Stage 6: Batched claim verification
│   └── pipeline.py            # End-to-end orchestrator with progress callbacks
├── prompts/
│   ├── planner.txt            # Stage 1 prompt
│   ├── extractor.txt          # Stage 4 prompt with injection guard
│   ├── writer.txt             # Stage 5 prompt
│   └── verifier.txt           # Stage 6 prompt with injection guard
├── eval/
│   ├── questions.json         # 10 test questions with expected facts
│   ├── labeled_claims.json    # 35 hand-labeled claims (25 dev / 10 held-out)
│   ├── labeling_guide.md      # Ground-truth decision documentation
│   └── run_eval.py            # Benchmark execution script
├── examples/                  # 3 pre-saved complete briefs
│   ├── example_1.json         # Mistral AI Business Model & Enterprise Pricing
│   ├── example_2.json         # CRISPR Casgevy Commercial Rollout & Approvals
│   └── example_3.json         # Stripe Crypto & Stablecoin Platform
└── tests/
    ├── test_match_quote.py    # Strict numbers, negation counts, fuzzy text
    ├── test_llm.py            # Pacing, backoff, QuotaExhausted, JSON repair
    ├── test_schemas.py        # Model serialization and validation
    └── test_pipeline_mock.py  # End-to-end pipeline run with mocked providers
```

---

## Phase 0: Research & Key Technical Decisions

*(See [specs/001-research-brief-pipeline/research.md](file:///C:/Users/Zainab%20Ashraf/OneDrive/Desktop/Research%20Brief%20Agent/ResearchBriefAgent/specs/001-research-brief-pipeline/research.md) for full analysis)*

1. **Quote Verification**: Combines token-level normalization, sliding window alignment ($\ge 0.93$ similarity), exact numeric subset verification within that window, and exact negation word counts.
2. **Unified LLM Gateway**: Standardized `OpenAI` client pointing to `LLM_BASE_URL` (default Google Gemini OpenAI endpoint or Groq) with backoff on transient errors and immediate `QuotaExhausted` raise on daily limits.
3. **Multi-Tenancy Security**: `LLMConfig` is instantiated directly from UI inputs in `app.py` or `.env` in CLI scripts. No keys are ever written to `os.environ`.
4. **Extraction Batching**: 3 sources per batch ($\le 3,500$ chars each) compresses extraction to 2-3 calls, ensuring total pipeline calls stay $\le 7$.

---

## Phase 1: Data Contracts & Execution Flow

*(See [specs/001-research-brief-pipeline/data-model.md](file:///C:/Users/Zainab%20Ashraf/OneDrive/Desktop/Research%20Brief%20Agent/ResearchBriefAgent/specs/001-research-brief-pipeline/data-model.md) and [specs/001-research-brief-pipeline/contracts/pipeline-api.md](file:///C:/Users/Zainab%20Ashraf/OneDrive/Desktop/Research%20Brief%20Agent/ResearchBriefAgent/specs/001-research-brief-pipeline/contracts/pipeline-api.md))*

- Pipeline accepts `(question: str, llm_cfg: LLMConfig, search_cfg: SearchConfig, on_progress: Optional[Callable[[str], None]]) -> FinalBrief`.
- Strict handoffs between stages using typed Pydantic models.
- Progress events reported at each stage transition for UI rendering.
