from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Source(BaseModel):
    id: int = Field(..., description="Unique 1-based sequential source index")
    title: str = Field(..., description="Page or article title")
    url: str = Field(..., description="Full canonical source URL")
    domain: Optional[str] = Field(None, description="Extracted domain name")
    published_date: Optional[str] = Field(None, description="Publication date string if available")
    text: Optional[str] = Field(None, description="Cleaned, truncated text content (<= 3,500 chars)")

class Fact(BaseModel):
    fact: str = Field(..., description="Atomic factual assertion")
    quote: str = Field(..., description="Exact quoted text from the source passage")
    source_id: int = Field(..., description="Foreign key mapping to Source.id")
    confidence: Literal["high", "medium", "low"] = "medium"

class Claim(BaseModel):
    claim_id: int = Field(..., description="Sequential claim identifier")
    text: str = Field(..., description="Sentence asserting a fact")
    citation_ids: List[int] = Field(..., min_length=1, description="List of source IDs backing this claim")
    section: Literal["summary", "key_findings"]

class BriefDraft(BaseModel):
    title: str = Field(..., description="Concise brief headline")
    claims: List[Claim] = Field(..., description="List of structured claims with citations")
    gaps_and_conflicts: List[str] = Field(default_factory=list, description="Missing facts or contradictions")

class ClaimVerdict(BaseModel):
    claim_id: int
    text: str
    citation_ids: List[int]
    section: Literal["summary", "key_findings"]
    verdict: Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"]
    reason: str = Field(..., description="One-sentence rationale explaining the verdict")
    supporting_quotes: List[str] = Field(default_factory=list, description="Passages cited from sources")

class FinalBrief(BaseModel):
    question: str
    title: str
    generated_at: datetime
    model_used: str
    claims: List[ClaimVerdict]
    gaps_and_conflicts: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    total_claims: int
    supported: int
    partial: int
    unsupported: int
    dropped_uncited_claims: int = 0
    dropped_invalid_quotes: int = 0
    llm_calls: int = 0
    elapsed_s: float = 0.0

    def to_markdown(self) -> str:
        """Serializes the verified research brief into clean Markdown format."""
        badge_icons = {
            "SUPPORTED": "✅ Supported",
            "PARTIAL": "⚠️ Partial",
            "UNSUPPORTED": "❌ Unsupported"
        }
        
        md_lines = [
            f"# Brief: {self.title}",
            f"\n*Research Question: {self.question}*",
            f"*Generated at: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | Model: {self.model_used}*",
            f"*Summary Metrics: {self.supported}/{self.total_claims} claims supported ({self.partial} partial, {self.unsupported} unsupported) | LLM Calls: {self.llm_calls} | Time: {self.elapsed_s:.1f}s*",
            "\n## Summary"
        ]

        summary_claims = [c for c in self.claims if c.section == "summary"]
        for c in summary_claims:
            cites = "".join(f"[{cid}]" for cid in c.citation_ids)
            badge = badge_icons.get(c.verdict, c.verdict)
            md_lines.append(f"- {c.text} {cites} — **{badge}** ({c.reason})")

        md_lines.append("\n## Key Findings")
        key_claims = [c for c in self.claims if c.section == "key_findings"]
        for c in key_claims:
            cites = "".join(f"[{cid}]" for cid in c.citation_ids)
            badge = badge_icons.get(c.verdict, c.verdict)
            md_lines.append(f"- {c.text} {cites} — **{badge}** ({c.reason})")

        if self.gaps_and_conflicts:
            md_lines.append("\n## Gaps and Conflicts")
            for gap in self.gaps_and_conflicts:
                md_lines.append(f"- {gap}")

        md_lines.append("\n## Sources")
        for s in self.sources:
            date_str = f" ({s.published_date})" if s.published_date else ""
            md_lines.append(f"[{s.id}] {s.title}: {s.url}{date_str}")

        return "\n".join(md_lines)
