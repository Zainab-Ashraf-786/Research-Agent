import re
from typing import List
from agent.schemas import Source

def clean_and_budget_text(text: str, max_chars: int = 3500) -> str:
    """
    Cleans raw markdown or HTML text, removing excess blank lines and whitespace,
    and budgets it to a safe character ceiling.
    """
    if not text:
        return ""
        
    # Replace multiple spaces/newlines with single equivalents
    cleaned = re.sub(r"\n{3,}", "\n\n", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned) > max_chars:
        # Cut cleanly at nearest paragraph or newline
        truncated = cleaned[:max_chars]
        last_nl = truncated.rfind("\n")
        if last_nl > max_chars * 0.75:
            cleaned = truncated[:last_nl].strip()
        else:
            cleaned = truncated.strip()

    return cleaned

def prepare_sources(sources: List[Source], max_chars_per_source: int = 3500, min_chars: int = 50) -> List[Source]:
    """
    Stage 3: Cleans and budgets raw source contents.
    Filters out empty or unreadable sources and re-indexes sequentially.
    Consumes 0 LLM calls.
    """
    valid_sources: List[Source] = []
    
    for s in sources:
        cleaned_text = clean_and_budget_text(s.text or "", max_chars=max_chars_per_source)
        # Drop thin pages with less than min_chars of content
        if len(cleaned_text) < min_chars:
            continue

        valid_sources.append(
            Source(
                id=len(valid_sources) + 1,
                title=s.title,
                url=s.url,
                domain=s.domain,
                published_date=s.published_date,
                text=cleaned_text
            )
        )

    return valid_sources
