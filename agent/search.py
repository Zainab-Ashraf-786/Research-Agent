import os
from typing import List, Optional
from urllib.parse import urlparse
from agent.config import SearchConfig
from agent.schemas import Source
from agent.cache import DiskCache

def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def search_sources(
    queries: List[str],
    search_cfg: SearchConfig,
    max_sources: int = 8,
    use_cache: bool = True
) -> List[Source]:
    """
    Stage 2: Executes web searches across generated queries and aggregates unique sources.
    Uses Tavily API with include_raw_content=True for rich page excerpts.
    Consumes 0 LLM calls.
    """
    from tavily import TavilyClient
    
    cache = DiskCache(enabled=use_cache)
    seen_urls = set()
    seen_domains = set()
    sources: List[Source] = []
    client = TavilyClient(api_key=search_cfg.api_key)

    for query in queries:
        query_str = query.strip()
        if not query_str:
            continue

        cache_key = f"tavily_search_{query_str}"
        cached_results = cache.get(cache_key)

        if cached_results is not None:
            results = cached_results
        else:
            try:
                resp = client.search(
                    query=query_str,
                    search_depth="advanced",
                    max_results=5,
                    include_raw_content=True
                )
                results = resp.get("results", [])
                cache.set(cache_key, results)
            except Exception as e:
                # Log or handle failure cleanly without crashing
                results = []

        for item in results:
            url = item.get("url", "").strip()
            if not url or url in seen_urls:
                continue

            domain = _extract_domain(url)
            # Soft domain deduplication: allow max 2 URLs per domain
            domain_count = sum(1 for s in sources if s.domain == domain)
            if domain_count >= 2:
                continue

            raw_text = item.get("raw_content") or item.get("content") or ""
            if len(raw_text.strip()) < 100:
                continue

            seen_urls.add(url)
            seen_domains.add(domain)

            source = Source(
                id=len(sources) + 1,
                title=item.get("title", "Untitled Source").strip(),
                url=url,
                domain=domain,
                published_date=item.get("published_date"),
                text=raw_text.strip()
            )
            sources.append(source)

            if len(sources) >= max_sources:
                return sources

    return sources
