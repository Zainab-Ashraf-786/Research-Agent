# Architecture Research & Decisions: Research Brief Agent

**Branch**: `001-research-brief-pipeline`  
**Date**: 2026-10-05

This document details the trade-offs, evaluated alternatives, and final architectural decisions for the core components of the Research Brief Agent.

---

## 1. Quote Matching & Numeric Verification (`match_quote.py`)

- **Context**: A pure substring match (`quote in page_text`) fails when free-tier LLMs clean whitespace, fix smart quotes (`”` vs `"`), or replace dashes (`—` vs `-`). Conversely, a loose fuzzy match ($\le 0.88$) allows subtle hallucination swaps like `$25/month` passing for `$20/month`, or dropping `"not"` (e.g. `"drug was not approved"` passing as `"drug was approved"`). Furthermore, checking if a number exists anywhere in the source document allows false grounding if that number appeared in a header or footer.
- **Decision**: Multi-tier window verification:
  1. Token-level normalization: lowercase, unify smart quotes, dashes, and strip comma separators inside numbers (`1,000` $\to$ `1000`).
  2. Exact contiguous token run match first. If absent, slide window across source tokens with strict $\ge 0.93$ similarity threshold.
  3. Window-restricted number matching: Extract all numbers, percentages, and currencies from the quote; every single one must exist within the matched window, not merely somewhere on the page.
  4. Negation equality: Count of negation words (`not`, `no`, `never`, `none`, `without`, `cannot`, and contractions ending in `n't`) in quote must equal the count in the matched window.
- **Alternatives Considered**:
  - *Regex substring only*: Dropped 40% of valid LLM quotes due to typographic quote variations.
  - *Pure Levenshtein / SequenceMatcher without number checks*: Permitted hallucinated numbers and dropped negations.

---

## 2. LLM Provider Gateway (`llm.py`)

- **Context**: The application must run on free tiers (Google Gemini, Groq, OpenRouter) without hardcoding proprietary SDKs or fragile provider-specific branches. The gateway must survive rate limits (`HTTP 429`) while avoiding pointless retries on hard daily quota limits.
- **Decision**:
  - Single `OpenAI` client interface: switching providers requires only setting `base_url`, `model`, and `api_key`.
  - Custom retry handler with exponential backoff ($2s, 4s, 8s$) for transient 429s and connection errors.
  - Quota inspection: Immediately raises `QuotaExhausted` without retrying if error text mentions `"daily"` or `"per day"`.
  - Pacing delay (`min_interval_s = 2.0s`) to remain under per-minute rate limits.
  - Robust JSON extraction with code-fence stripping and single-retry repair fallback.
- **Alternatives Considered**:
  - *`tenacity` library*: Obscured inner exceptions behind generic `RetryError` and could not differentiate daily quota exhaustion from transient per-minute rate limits.
  - *Direct LangChain / LiteLLM*: Added unnecessary dependencies (50+ MB) and abstract framework layers violating Constitution Principle VII.

---

## 3. Call Budget & Extraction Batching (`extractor.py`)

- **Context**: Free-tier models have strict requests-per-minute (RPM) limits (often 5 to 15 RPM). Extracting facts one source at a time with 8 sources consumed 8 calls, easily hitting rate limits during single-minute runs.
- **Decision**:
  - Batch sources into groups of 3 (at most 2-3 extraction calls for 8 sources).
  - Truncate each source to a strict character budget ($\le 3,500$ characters).
  - Caps the entire pipeline at a hard maximum of 7 LLM calls:
    - 1 call: Planner
    - 2-3 calls: Extractor
    - 1 call: Writer
    - 1 call: Verifier
    - (Max 1 optional retry for JSON repair)
- **Alternatives Considered**:
  - *Single prompt for all 8 sources*: Context length caused free-tier models to lose attention and hallucinate or omit citations from middle sources.
  - *1 source per call*: Hit 15 RPM rate limits and caused runs to exceed the 90-second latency target.

---

## 4. Multi-Tenant Key Security & BYOK Architecture (`app.py`)

- **Context**: When deployed on shared hosting (e.g. Streamlit Community Cloud), writing keys to `os.environ` creates a severe vulnerability where one user's key leaks to subsequent visitors.
- **Decision**:
  - Store visitor keys exclusively in `st.session_state`.
  - Pass keys explicitly into `LLMConfig(base_url=..., api_key=..., model=...)`.
  - Add an automated unit test (`test_pipeline_mock.py`) asserting that `os.environ` remains completely unmodified during and after pipeline execution.
- **Alternatives Considered**:
  - *`os.environ` injection*: Extremely common in tutorials, but critically vulnerable on multi-tenant servers.

---

## 5. Independent Verifier Evaluation Benchmark (`eval/labeled_claims.json`)

- **Context**: Evaluating an LLM verifier using LLM-generated ground truth is circular and untrustworthy.
- **Decision**:
  - Author and personally review 35 real-world claim-excerpt pairs (14 `SUPPORTED`, 10 `PARTIAL`, 11 `UNSUPPORTED`).
  - Partition into 25 dev claims (used for tuning verifier prompts) and 10 held-out claims (strictly untouched during tuning).
  - Publish confusion matrix, agreement rate, and false-`SUPPORTED` rates in the README.
