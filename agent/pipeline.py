from datetime import datetime, timezone
from typing import Callable, Optional
from agent.config import LLMConfig, SearchConfig
from agent.extractor import extract_facts_from_sources
from agent.llm import LLMSession, StageError
from agent.planner import plan_queries
from agent.reader import prepare_sources
from agent.schemas import FinalBrief
from agent.search import search_sources
from agent.verifier import verify_claims
from agent.writer import write_brief_draft

def run(
    question: str,
    llm_cfg: LLMConfig,
    search_cfg: SearchConfig,
    on_progress: Optional[Callable[[str], None]] = None,
    use_cache: bool = True
) -> FinalBrief:
    """
    Executes the 6-stage Research Brief Agent pipeline.
    Enforces a hard ceiling of <= 7 LLM calls and guarantees per-claim verification.
    """
    def _notify(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    session = LLMSession(llm_cfg)

    # Stage 1: Query Planning (1 LLM call)
    _notify("Planning search queries...")
    queries = plan_queries(question, session)

    # Stage 2: Web Search (0 LLM calls)
    _notify(f"Searching web sources across {len(queries)} queries...")
    raw_sources = search_sources(queries, search_cfg, max_sources=8, use_cache=use_cache)
    if not raw_sources:
        raise StageError("Insufficient reliable sources found to research this topic.")

    # Stage 3: Content Reader & Cleanup (0 LLM calls)
    _notify("Reading and cleaning page contents...")
    sources = prepare_sources(raw_sources, max_chars_per_source=3500)
    if not sources:
        raise StageError("Source content could not be cleaned or was too thin to extract evidence.")

    # Stage 4: Fact Extraction with Quote Verification (2-3 LLM calls)
    _notify(f"Extracting atomic facts from {len(sources)} sources (batched in 3s)...")
    facts, dropped_quotes = extract_facts_from_sources(sources, session, batch_size=3)
    if not facts:
        raise StageError("No verifiable facts with valid source quotes could be extracted.")

    # Stage 5: Structured Brief Generation (1 LLM call)
    _notify("Drafting structured research brief...")
    draft, dropped_uncited = write_brief_draft(question, facts, session)

    # Stage 6: Batched Claim Verification (1 LLM call)
    _notify(f"Independently verifying {len(draft.claims)} claims against source quotes...")
    verdicts = verify_claims(draft, facts, session)

    # Compute summary metrics
    supported_cnt = sum(1 for v in verdicts if v.verdict == "SUPPORTED")
    partial_cnt = sum(1 for v in verdicts if v.verdict == "PARTIAL")
    unsupported_cnt = sum(1 for v in verdicts if v.verdict == "UNSUPPORTED")

    _notify("Finalizing verified research brief...")

    return FinalBrief(
        question=question.strip(),
        title=draft.title,
        generated_at=datetime.now(timezone.utc),
        model_used=llm_cfg.model,
        claims=verdicts,
        gaps_and_conflicts=draft.gaps_and_conflicts,
        sources=sources,
        total_claims=len(verdicts),
        supported=supported_cnt,
        partial=partial_cnt,
        unsupported=unsupported_cnt,
        dropped_uncited_claims=dropped_uncited,
        dropped_invalid_quotes=dropped_quotes,
        llm_calls=session.call_count,
        elapsed_s=session.elapsed_seconds
    )
