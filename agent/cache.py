import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"

class DiskCache:
    """Simple JSON-based disk cache for search results and fetched page contents."""
    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear(self) -> None:
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass
