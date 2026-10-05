import json
import re
import time
from typing import Any, Dict, List, Optional
import openai
from openai import OpenAI
from agent.config import LLMConfig

class QuotaExhausted(Exception):
    """Raised when the LLM provider daily quota is depleted and retrying is futile."""
    pass

class StageError(Exception):
    """Raised when an unrecoverable stage error occurs."""
    pass

_last_call_time = 0.0

def _pace(cfg: LLMConfig) -> None:
    """Enforces minimum interval between consecutive LLM calls to respect RPM limits."""
    global _last_call_time
    wait = cfg.min_interval_s - (time.time() - _last_call_time)
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.time()

def _is_daily_quota(err: Exception) -> bool:
    """Detects whether a 429 error is a daily quota exhaustion vs transient RPM limit."""
    msg = str(err).lower()
    return "per day" in msg or "daily" in msg or "quota exceeded" in msg or "resource_exhausted" in msg

class LLMSession:
    """Wrapper that tracks call counts and latency for a research pipeline run."""
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.call_count = 0
        self.start_time = time.time()

    def generate(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        self.call_count += 1
        return generate(prompt, self.cfg, system=system, json_mode=json_mode)

    def generate_json(self, prompt: str, system: str = "") -> Any:
        self.call_count += 1
        return generate_json(prompt, self.cfg, system=system)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

def generate(prompt: str, cfg: LLMConfig, system: str = "", json_mode: bool = False) -> str:
    """
    Executes a single LLM completion using an OpenAI-compatible client.
    Handles rate limit backoff, daily quota fast-fail, and provider compatibility.
    """
    client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: Dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": 0.1,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(4):
        try:
            _pace(cfg)
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except openai.RateLimitError as e:
            if _is_daily_quota(e) or attempt == 3:
                raise QuotaExhausted(f"Daily API quota exhausted: {e}") from e
            time.sleep(2 ** (attempt + 1))
        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            if attempt == 3:
                raise StageError(f"LLM provider unreachable after retries: {e}") from e
            time.sleep(2 ** (attempt + 1))
        except openai.BadRequestError:
            # Handle providers that reject response_format parameter
            if json_mode and "response_format" in kwargs:
                kwargs.pop("response_format")
                continue
            raise

    raise StageError("LLM generation failed after maximum retry attempts.")

def _extract_json(text: str) -> Any:
    """Strips Markdown fences and parses JSON payload."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.S)
    target = match.group(1) if match else cleaned
    return json.loads(target)

def generate_json(prompt: str, cfg: LLMConfig, system: str = "") -> Any:
    """
    Generates structured JSON output with automatic extraction and single-retry repair.
    """
    raw = generate(prompt, cfg, system=system, json_mode=True)
    try:
        return _extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        stricter = prompt + "\n\nCRITICAL: Return ONLY valid, parseable JSON. Do not include markdown fences, comments, or preamble."
        raw = generate(stricter, cfg, system=system, json_mode=False)
        try:
            return _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            raise StageError(f"Model failed to produce valid JSON: {raw[:200]}") from e
