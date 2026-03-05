import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


DEFAULT_API_URL = os.environ.get("PAGEINDEX_API_URL", "https://api.pageindex.ai")
DEFAULT_API_KEY = os.environ.get("PAGEINDEX_API_KEY")
DEFAULT_TOP_K = 5
MANIFEST_PATH = Path(__file__).parent / "docs_folder" / "pageindex_manifest.json"


def _load_doc_ids_from_manifest(path: Path = MANIFEST_PATH) -> List[str]:
    """Read all doc_id values from the PageIndex manifest file."""
    if not path.exists():
        return []
    with open(path) as f:
        manifest = json.load(f)
    return [entry["doc_id"] for entry in manifest.values() if entry.get("doc_id")]


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
    Lightweight HTTP client for PageIndex Chat API (vectorless search).
    Uses /chat/completions which supports doc_id as an array and works
    on any doc with status=completed (no retrieval_ready required).
    """

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        api_key: Optional[str] = DEFAULT_API_KEY,
        doc_ids: Optional[List[str]] = None,
        timeout: int = 60,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.doc_ids = doc_ids if doc_ids is not None else _load_doc_ids_from_manifest()
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api_key"] = self.api_key
        return headers

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[PageIndexResult]:
        if not query.strip():
            return []
        if not self.doc_ids:
            raise RuntimeError("No doc_ids configured — check pageindex_manifest.json")

        payload: Dict[str, Any] = {
            "messages": [{"role": "user", "content": query}],
            "doc_id": self.doc_ids,
            "stream": False,
            "enable_citations": True,
        }

        url = f"{self.api_url}/chat/completions"
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
        choices = data.get("choices", [])
        if not choices:
            return []

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            return []

        return [
            PageIndexResult(
                text=content,
                source="PageIndex Chat API",
            )
        ]


__all__ = ["PageIndexClient", "PageIndexResult"]
