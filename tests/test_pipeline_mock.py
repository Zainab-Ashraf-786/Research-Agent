import copy
import os
from unittest.mock import MagicMock, patch
import pytest
from agent.config import LLMConfig, SearchConfig
from agent.pipeline import run
from agent.schemas import FinalBrief, Source

@pytest.fixture
def dummy_configs():
    llm_cfg = LLMConfig(
        base_url="https://api.openai.com/v1",
        api_key="sk-test-secret-never-in-environ",
        model="mock-gemini",
        min_interval_s=0.01
    )
    search_cfg = SearchConfig(api_key="tvly-secret-never-in-environ")
    return llm_cfg, search_cfg

@patch("agent.pipeline.search_sources")
@patch("agent.llm.OpenAI")
def test_pipeline_end_to_end_mock(mock_openai_cls, mock_search, dummy_configs):
    llm_cfg, search_cfg = dummy_configs

    # Record baseline os.environ snapshot for multi-tenant security verification
    env_before = copy.deepcopy(dict(os.environ))

    # Mock searcher output: 3 realistic sources
    mock_search.return_value = [
        Source(
            id=1,
            title="Mistral Official Docs",
            url="https://docs.mistral.ai",
            domain="mistral.ai",
            text="Mistral Large 2 features a 128k context window and costs $2.00 per million input tokens."
        ),
        Source(
            id=2,
            title="TechCrunch Mistral Launch",
            url="https://techcrunch.com/mistral",
            domain="techcrunch.com",
            text="Mistral AI was founded in 2023 in Paris by Arthur Mensch and former DeepMind researchers."
        )
    ]

    # Mock LLM completions sequentially for:
    # 1. Planner (queries)
    # 2. Extractor (facts from batch 1)
    # 3. Writer (draft brief containing 1 cited claim and 1 uncited claim)
    # 4. Verifier (verdicts)
    planner_resp = '{"queries": ["Mistral pricing", "Mistral founding 2023"]}'
    
    extractor_resp = (
        '{"facts": ['
        '  {"fact": "Mistral Large 2 features a 128k context window.", "quote": "Mistral Large 2 features a 128k context window", "source_id": 1, "confidence": "high"},'
        '  {"fact": "Mistral costs $2.00 per million tokens.", "quote": "costs $2.00 per million input tokens", "source_id": 1, "confidence": "high"},'
        '  {"fact": "Corrupted quote", "quote": "costs $500 per seat", "source_id": 1, "confidence": "low"}'  # Must be dropped!
        ']}'
    )

    writer_resp = (
        '{"title": "Mistral AI Research Brief",'
        ' "claims": ['
        '   {"claim_id": 1, "text": "Mistral Large 2 has a 128k context window.", "citation_ids": [1], "section": "summary"},'
        '   {"claim_id": 2, "text": "Mistral charges $2.00 per million tokens.", "citation_ids": [1], "section": "key_findings"},'
        '   {"claim_id": 3, "text": "Uncited speculative sentence.", "citation_ids": [], "section": "key_findings"}'  # Must be dropped!
        ' ],'
        ' "gaps_and_conflicts": ["Enterprise on-premise licensing is unverified."]}'
    )

    verifier_resp = (
        '{"verdicts": ['
        '  {"claim_id": 1, "verdict": "SUPPORTED", "reason": "Directly backed by docs quote.", "supporting_quotes": ["128k context window"]},'
        '  {"claim_id": 2, "verdict": "SUPPORTED", "reason": "Exact price confirmed.", "supporting_quotes": ["$2.00 per million input tokens"]}'
        ']}'
    )

    mock_client = MagicMock()
    responses = [planner_resp, extractor_resp, writer_resp, verifier_resp]
    
    def side_effect(**kwargs):
        mock_choice = MagicMock()
        mock_choice.message.content = responses.pop(0) if responses else "{}"
        mock_res = MagicMock(choices=[mock_choice])
        return mock_res

    mock_client.chat.completions.create.side_effect = side_effect
    mock_openai_cls.return_value = mock_client

    progress_events = []
    def on_progress(msg: str):
        progress_events.append(msg)

    brief = run(
        question="What is Mistral AI product and pricing?",
        llm_cfg=llm_cfg,
        search_cfg=search_cfg,
        on_progress=on_progress,
        use_cache=False
    )

    # 1. Assertions on Brief Structure
    assert isinstance(brief, FinalBrief)
    assert brief.title == "Mistral AI Research Brief"
    assert len(brief.claims) == 2
    assert brief.total_claims == 2
    assert brief.supported == 2

    # 2. Call Budget Assertion: Must not exceed 7 calls
    assert brief.llm_calls <= 7
    assert brief.llm_calls == 4

    # 3. Trust Filters Assertions
    assert brief.dropped_invalid_quotes >= 1  # Corrupted quote was dropped
    assert brief.dropped_uncited_claims >= 1  # Uncited claim was dropped

    # 4. Progress Callbacks
    assert len(progress_events) >= 5
    assert any("Planning" in ev for ev in progress_events)
    assert any("Finalizing" in ev for ev in progress_events)

    # 5. Multi-Tenant Key Security: os.environ must be completely unmodified!
    env_after = dict(os.environ)
    assert env_before == env_after
    assert "sk-test-secret-never-in-environ" not in os.environ.values()
    assert "tvly-secret-never-in-environ" not in os.environ.values()
