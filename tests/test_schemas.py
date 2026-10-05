from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from agent.schemas import Source, Fact, Claim, BriefDraft, ClaimVerdict, FinalBrief

def test_source_model():
    s = Source(id=1, title="Test Source", url="https://example.com", domain="example.com", text="Sample text")
    assert s.id == 1
    assert s.url == "https://example.com"

def test_fact_model():
    f = Fact(fact="Revenue grew 20%", quote="revenue grew by 20%", source_id=1, confidence="high")
    assert f.source_id == 1
    assert f.confidence == "high"

def test_claim_model_validation():
    # Valid claim with non-empty citation_ids
    c = Claim(claim_id=1, text="Mistral charges $2 per million tokens.", citation_ids=[1, 2], section="summary")
    assert c.citation_ids == [1, 2]

    # Invalid claim with empty citation_ids
    with pytest.raises(ValidationError):
        Claim(claim_id=2, text="Invalid claim without citation.", citation_ids=[], section="key_findings")

def test_final_brief_markdown_serialization():
    now = datetime.now(timezone.utc)
    s1 = Source(id=1, title="Mistral Docs", url="https://docs.mistral.ai", domain="mistral.ai")
    cv1 = ClaimVerdict(
        claim_id=1,
        text="Mistral Large costs $2 per million input tokens.",
        citation_ids=[1],
        section="summary",
        verdict="SUPPORTED",
        reason="Matched exact pricing table in documentation.",
        supporting_quotes=["Input: $2.00 / 1M tokens"]
    )
    brief = FinalBrief(
        question="What is Mistral pricing?",
        title="Mistral Pricing Brief",
        generated_at=now,
        model_used="gemini-2.5-flash",
        claims=[cv1],
        gaps_and_conflicts=["Enterprise SLA pricing is unlisted."],
        sources=[s1],
        total_claims=1,
        supported=1,
        partial=0,
        unsupported=0,
        dropped_uncited_claims=0,
        dropped_invalid_quotes=0,
        llm_calls=5,
        elapsed_s=22.4
    )

    md = brief.to_markdown()
    assert "# Brief: Mistral Pricing Brief" in md
    assert "Mistral Large costs $2 per million input tokens. [1] — **✅ Supported**" in md
    assert "[1] Mistral Docs: https://docs.mistral.ai" in md
    assert "Enterprise SLA pricing is unlisted." in md
