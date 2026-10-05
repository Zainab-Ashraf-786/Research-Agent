from pathlib import Path
from typing import List, Set, Tuple, Union
from agent.config import LLMConfig
from agent.llm import LLMSession, generate_json
from agent.schemas import BriefDraft, Claim, Fact

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "writer.txt"

def write_brief_draft(
    question: str,
    facts: List[Fact],
    runner: Union[LLMConfig, LLMSession]
) -> Tuple[BriefDraft, int]:
    """
    Stage 5: Drafts structured research brief claims from verified facts.
    Enforces citation discipline: claims with missing or invalid citation IDs are dropped.
    
    Returns:
    - (BriefDraft, dropped_uncited_claims_count)
    """
    if not facts:
        return BriefDraft(
            title=f"Research Brief: {question}",
            claims=[],
            gaps_and_conflicts=["No verified facts were found to support this research topic."]
        ), 0

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    valid_source_ids: Set[int] = {f.source_id for f in facts}
    
    fact_lines = []
    for f in facts:
        fact_lines.append(f"- [Source {f.source_id}]: {f.fact} (Quote: \"{f.quote}\")")
    facts_payload = "\n".join(fact_lines)

    prompt = template.format(question=question.strip(), facts_text=facts_payload)
    system_msg = (
        "You are an analytical brief writer. Write only factual claims citing source IDs. "
        "Do not invent facts or cite nonexistent sources."
    )

    if isinstance(runner, LLMSession):
        data = runner.generate_json(prompt, system=system_msg)
    else:
        data = generate_json(prompt, runner, system=system_msg)

    title = data.get("title", f"Research Brief: {question}").strip()
    raw_claims = data.get("claims", [])
    gaps = [str(g).strip() for g in data.get("gaps_and_conflicts", []) if str(g).strip()]

    valid_claims: List[Claim] = []
    dropped_uncited_claims = 0

    for idx, c in enumerate(raw_claims, start=1):
        try:
            text = str(c.get("text", "")).strip()
            cites = [int(cid) for cid in c.get("citation_ids", []) if int(cid) in valid_source_ids]
            section = c.get("section", "key_findings")
            if section not in ("summary", "key_findings"):
                section = "key_findings"

            # Strict Traceability Gate: Dropping uncited claims
            if not text or not cites:
                dropped_uncited_claims += 1
                continue

            valid_claims.append(
                Claim(
                    claim_id=len(valid_claims) + 1,
                    text=text,
                    citation_ids=cites,
                    section=section
                )
            )
        except Exception:
            dropped_uncited_claims += 1

    draft = BriefDraft(
        title=title,
        claims=valid_claims,
        gaps_and_conflicts=gaps
    )
    return draft, dropped_uncited_claims
