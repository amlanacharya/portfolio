import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


DEFAULT_API_URL = os.environ.get("PAGEINDEX_API_URL", "http://localhost:8080")
DEFAULT_SITE_ID = os.environ.get("PAGEINDEX_SITE_ID")
DEFAULT_API_KEY = os.environ.get("PAGEINDEX_API_KEY")
DEFAULT_TOP_K = 5


@dataclass
class PageIndexResult:
    text: str
    source: Optional[str] = None
    section: Optional[str] = None
    score: Optional[float] = None
    url: Optional[str] = None
    tree: Optional[Dict[str, Any]] = None


class PageIndexClient:
    """
    Lightweight HTTP client for PageIndex vectorless search.
    Assumes API key + site id are provided via env or constructor args.
    """

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        api_key: Optional[str] = DEFAULT_API_KEY,
        site_id: Optional[str] = DEFAULT_SITE_ID,
        timeout: int = 30,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.site_id = site_id
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[PageIndexResult]:
        if not query.strip():
            return []
        if not self.site_id:
            raise ValueError("PAGEINDEX_SITE_ID is not set")

        payload = {
            "site_id": self.site_id,
            "query": query,
            "top_k": top_k,
        }

        url = f"{self.api_url}/api/search"
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"PageIndex search failed: {exc}") from exc

        data = resp.json()
        results = data.get("results") or data.get("data") or []
        parsed: List[PageIndexResult] = []
        for item in results:
            parsed.append(
                PageIndexResult(
                    text=item.get("text") or "",
                    source=item.get("source"),
                    section=item.get("section"),
                    score=item.get("score"),
                    url=item.get("url"),
                    tree=item.get("tree") or data.get("tree"),
                )
            )

        # If API returns a single tree at root, attach to first result
        if data.get("tree") and parsed:
            if not parsed[0].tree:
                parsed[0].tree = data["tree"]

        return parsed


__all__ = ["PageIndexClient", "PageIndexResult"]
