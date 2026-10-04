# Programmatic API Contract: Research Brief Pipeline

**Branch**: `001-research-brief-pipeline`  
**Date**: 2026-10-05

This document defines the entry-point contract for orchestrating the research brief pipeline.

---

## 1. Orchestrator Contract (`agent/pipeline.py`)

### Function Signature

```python
def run(
    question: str,
    llm_cfg: LLMConfig,
    search_cfg: SearchConfig,
    on_progress: Optional[Callable[[str], None]] = None,
    use_cache: bool = True
) -> FinalBrief:
    """
    Executes the 6-stage research brief generation pipeline.

    Parameters:
    - question (str): The research question submitted by user.
    - llm_cfg (LLMConfig): Immutable configuration holding base_url, api_key, model.
    - search_cfg (SearchConfig): Configuration holding Tavily API key.
    - on_progress (Optional[Callable[[str], None]]): Callback invoked with stage descriptions
      (e.g., "Planning search queries...", "Searching sources...", "Extracting facts...",
      "Drafting brief...", "Verifying claims...").
    - use_cache (bool): Whether to read/write search and reader disk caches (default True).

    Returns:
    - FinalBrief: The complete verified brief containing structured claims, badges,
      sources, and execution metrics.

    Raises:
    - QuotaExhausted: If provider daily quota is depleted.
    - StageError: If unrecoverable upstream failures occur (e.g. unreachable provider,
      zero search results found).
    """
```

---

## 2. Stage Contracts

| Stage | Module | Input Contract | Output Contract | LLM Calls |
|---|---|---|---|---|
| **1. Planner** | `agent/planner.py` | `(question: str, cfg: LLMConfig)` | `List[str]` (3 to 5 queries) | 1 |
| **2. Searcher** | `agent/search.py` | `(queries: List[str], cfg: SearchConfig, use_cache: bool)` | `List[Source]` ($\le 8$ deduplicated) | 0 |
| **3. Reader** | `agent/reader.py` | `(sources: List[Source], use_cache: bool)` | `List[Source]` (with text $\le 3,500$ chars) | 0 |
| **4. Extractor** | `agent/extractor.py` | `(sources: List[Source], cfg: LLMConfig)` | `(List[Fact], dropped_invalid_quotes: int)` | 2–3 |
| **5. Writer** | `agent/writer.py` | `(facts: List[Fact], cfg: LLMConfig)` | `(BriefDraft, dropped_uncited_claims: int)` | 1 |
| **6. Verifier** | `agent/verifier.py` | `(draft: BriefDraft, facts: List[Fact], cfg: LLMConfig)` | `List[ClaimVerdict]` | 1 |
