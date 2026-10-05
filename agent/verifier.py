from pathlib import Path
from typing import Dict, List, Union
from agent.config import LLMConfig
from agent.llm import LLMSession, generate_json
from agent.schemas import BriefDraft, ClaimVerdict, Fact

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "verifier.txt"

def verify_claims(
    draft: BriefDraft,
    facts: List[Fact],
    runner: Union[LLMConfig, LLMSession]
) -> List[ClaimVerdict]:
    """
    Stage 6: Independently verifies every claim against the quotes of its cited facts.
    Evaluates all claims in a single batched call to respect free-tier call budgets.
    
    Returns:
    - List[ClaimVerdict] containing per-claim verdicts, reasons, and supporting quotes.
    """
    if not draft.claims:
        return []

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # Index quotes by source_id
    quotes_by_source: Dict[int, List[str]] = {}
    for f in facts:
        quotes_by_source.setdefault(f.source_id, []).append(f.quote)

    # Format claims and cited quotes payload
    claim_blocks = []
    for c in draft.claims:
        cited_quotes = []
        for sid in c.citation_ids:
            for q in quotes_by_source.get(sid, []):
                cited_quotes.append(f"  - [Source {sid}]: \"{q}\"")

        quotes_str = "\n".join(cited_quotes) if cited_quotes else "  - (No specific quote found for cited source IDs)"
        block = (
            f"Claim ID: {c.claim_id}\n"
            f"Claim Text: {c.text}\n"
            f"Cited Source Evidence:\n{quotes_str}\n"
        )
        claim_blocks.append(block)

    claims_payload = "\n---\n".join(claim_blocks)
    prompt = template.format(claims_payload=claims_payload)
    system_msg = (
        "You are an impartial fact-checking judge. Verify claims strictly against provided evidence quotes. "
        "Do not invent support. Return valid JSON only."
    )

    if isinstance(runner, LLMSession):
        data = runner.generate_json(prompt, system=system_msg)
    else:
        data = generate_json(prompt, runner, system=system_msg)

    raw_verdicts = []
    if isinstance(data, dict) and "verdicts" in data and isinstance(data["verdicts"], list):
        raw_verdicts = data["verdicts"]
    elif isinstance(data, list):
        raw_verdicts = data

    verdicts_by_id: Dict[int, dict] = {}
    for v in raw_verdicts:
        try:
            cid = int(v.get("claim_id", -1))
            verdicts_by_id[cid] = v
        except Exception:
            pass

    final_verdicts: List[ClaimVerdict] = []
    for c in draft.claims:
        v_data = verdicts_by_id.get(c.claim_id)
        if v_data:
            verdict_str = str(v_data.get("verdict", "UNSUPPORTED")).upper().strip()
            if verdict_str not in ("SUPPORTED", "PARTIAL", "UNSUPPORTED"):
                verdict_str = "PARTIAL"
            reason_str = str(v_data.get("reason", "Verification verdict assigned based on cited passages.")).strip()
            supporting = [str(q).strip() for q in v_data.get("supporting_quotes", []) if str(q).strip()]
        else:
            verdict_str = "UNSUPPORTED"
            reason_str = "No verdict returned by verification engine."
            supporting = []

        final_verdicts.append(
            ClaimVerdict(
                claim_id=c.claim_id,
                text=c.text,
                citation_ids=c.citation_ids,
                section=c.section,
                verdict=verdict_str, # type: ignore
                reason=reason_str,
                supporting_quotes=supporting
            )
        )

    return final_verdicts
