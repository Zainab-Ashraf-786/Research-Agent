# Data Models & Schemas: Research Brief Agent

**Branch**: `001-research-brief-pipeline`  
**Date**: 2026-10-05

This document defines all typed data contracts crossing system boundaries within the Research Brief Agent pipeline.

---

## 1. Configuration Dataclasses (`agent/config.py`)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    min_interval_s: float = 2.0

@dataclass(frozen=True)
class SearchConfig:
    api_key: str
```

---

## 2. Core Domain Schemas (`agent/schemas.py`)

```python
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Source(BaseModel):
    id: int = Field(..., description="Unique 1-based sequential source index")
    title: str = Field(..., description="Page or article title")
    url: str = Field(..., description="Full canonical source URL")
    domain: Optional[str] = Field(None, description="Extracted domain name")
    published_date: Optional[str] = Field(None, description="ISO date or publication string if provided")
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
    gaps_and_conflicts: List[str]
    sources: List[Source]
    total_claims: int
    supported: int
    partial: int
    unsupported: int
    dropped_uncited_claims: int
    dropped_invalid_quotes: int
    llm_calls: int
    elapsed_s: float
```

---

## 3. Evaluation Schemas (`eval/run_eval.py`)

```python
class LabeledClaim(BaseModel):
    id: str
    claim: str
    source_excerpt: str
    ground_truth_verdict: Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"]
    split: Literal["dev", "held_out"]
    notes: Optional[str] = None

class QuestionBenchmark(BaseModel):
    id: str
    question: str
    category: str
    must_appear_facts: List[str] # Regex patterns or keywords
```
