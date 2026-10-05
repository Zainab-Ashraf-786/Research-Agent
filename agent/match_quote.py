import re
from difflib import SequenceMatcher
from typing import List, Optional, Set

NEGATIONS = {"not", "no", "never", "none", "without", "cannot"}

def _normalize(text: str) -> str:
    """Lowercases, normalizes smart quotes/dashes, strips currency symbols and number commas."""
    text = (text.replace("\u2018", "'").replace("\u2019", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2013", "-").replace("\u2014", "-"))
    # Strip currency symbols preceding digits ($25 -> 25)
    text = re.sub(r"[\$€£¥](?=\d)", "", text)
    # Strip commas inside numbers (1,000 -> 1000)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    return text.lower()

def _tokens(text: str) -> List[str]:
    """Tokenizes normalized text into alphanumeric tokens, preserving percentage signs and decimals."""
    return re.findall(r"[a-z0-9%]+(?:[.'][a-z0-9%]+)*", _normalize(text))

def _numbers(tokens: List[str]) -> Set[str]:
    """Extracts all numeric tokens (integers, floats, percentages)."""
    return {t for t in tokens if re.fullmatch(r"\d+(?:\.\d+)?%?", t)}

def _negations(tokens: List[str]) -> int:
    """Counts negation words and negative contractions."""
    return sum(1 for t in tokens if t in NEGATIONS or t.endswith("n't"))

def _find_window(q: List[str], s: List[str], threshold: float) -> Optional[List[str]]:
    """
    Finds the best matching window in source tokens for the quote tokens.
    Checks exact contiguous run first; falls back to sliding-window SequenceMatcher >= threshold.
    """
    n = len(q)
    if n == 0 or len(s) < n:
        return None
        
    # 1. Exact contiguous run check
    for i in range(len(s) - n + 1):
        if s[i:i + n] == q:
            return s[i:i + n]
            
    # 2. Fuzzy sliding window fallback
    q_str = " ".join(q)
    best_ratio = 0.0
    best_window = None
    for i in range(len(s) - n + 1):
        win = s[i:i + n]
        ratio = SequenceMatcher(None, q_str, " ".join(win)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_window = win
            
    return best_window if best_ratio >= threshold else None

def is_quote_valid(quote: str, source_text: str, threshold: float = 0.93) -> bool:
    """
    Validates whether `quote` is genuinely grounded in `source_text`.
    
    Rules:
    1. Tokens in quote must match a contiguous run or high-similarity (>= threshold) window in source.
    2. Every number and percentage in the quote must exist within the MATCHED WINDOW (preventing
       numbers appearing elsewhere on the page from validating a fabricated quote).
    3. The count of negation words in the quote must equal the count in the matched window
       (preventing dropping 'not' or adding 'not' to invert truth).
    """
    if not quote or not source_text:
        return False
        
    q = _tokens(quote)
    s = _tokens(source_text)
    
    window = _find_window(q, s, threshold)
    if window is None:
        return False
        
    # Every number in the quote must exist in the matched window
    if not _numbers(q).issubset(_numbers(window)):
        return False
        
    # Negation counts must match exactly
    return _negations(q) == _negations(window)
