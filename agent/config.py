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
