from typing import List, Dict
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from embedding import client, model


def search_docs(
    query: str,
    top_k: int = 3,
    collection_name: str = "supply_chain_docs"
) -> List[Dict]:
    
    query_embedding = model.encode(query)
    
    results = client.query_points(
        collection_name=collection_name,
        query=query_embedding.tolist(),
        limit=top_k
    )
    
    return [
        {
            "text": point.payload["text"],
            "source": point.payload["source"],
            "section": point.payload["section"],
            "score": point.score
        }
        for point in results.points
    ]



__all__ = ["search_docs", "client", "model"]