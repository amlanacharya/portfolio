from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from typing import List, Dict
import uuid
from  chunking import load_and_chunk_docs

def build_vector_store(
    chunks: List[Dict[str, str]], 
    collection_name: str = "supply_chain_docs",
    model_name: str = "all-MiniLM-L6-v2"
) -> tuple[QdrantClient, SentenceTransformer]:
  
    model = SentenceTransformer(model_name)
    if model:
        print("log_msg1:loaded embedding model")
    #else: and error msg
            
    embedding_dim = model.get_sentence_embedding_dimension()
    if embedding_dim and model:
        print(f"log_msg2:Embedding of {model_name}: {embedding_dim}")

    client = QdrantClient(":memory:")
    if client:
        print("log_msg3:Qdrant client created")
    
    created_col=client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embedding_dim,
            distance=Distance.COSINE
        )
    )
    if created_col:
        print(f"log_msg4:Qdrant collection {collection_name} created")
    
    texts = [chunk["text"] for chunk in chunks]
    if chunks:
        print(f"Embedding {len(chunks)} chunks")
    embeddings = model.encode(texts, show_progress_bar=True)

    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding.tolist(),
            payload={
                "text": chunk["text"],
                "source": chunk["source"],
                "section": chunk["section"]
            }
        )
        points.append(point)

    print(f"log_msg5:Storing {len(points)} vectors in Qdrant")
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    return client, model

## shifted to retrieval
# def search_docs(
#     query: str,
#     client: QdrantClient,
#     model: SentenceTransformer,
#     collection_name: str = "supply_chain_docs",
#     top_k: int = 3
# ) -> List[Dict]:
#     query_embedding = model.encode(query)
#     results = client.query_points(
#         collection_name=collection_name,
#         query=query_embedding.tolist(),
#         limit=top_k
#     )
    
#     return [
#         {
#             "text": point.payload["text"],
#             "source":point.payload["source"],
#             "section": point.payload["section"],
#             "score": point.score
#         }
#         for point in results.points
#     ]

_client = None
_model = None


def get_vector_store() -> tuple[QdrantClient, SentenceTransformer]:
    """Lazy singleton — builds vector store on first call only."""
    global _client, _model
    if _client is None:
        docs_folder = r"2026\networkx-mua\docs_folder"
        chunks = load_and_chunk_docs(docs_folder)
        _client, _model = build_vector_store(chunks)
    return _client, _model

# if __name__ == "__main__":
   
    
#     docs_folder = r"2026\networkx-mua\docs_folder"
#     chunks = load_and_chunk_docs(docs_folder)
#     client, model = build_vector_store(chunks)
    
#     # Test query
#     query = "What happens when a port is congested?"
    
#     print(f"Query: {query}")
#     print("=" * 60)
    
#     results = search_docs(query, client, model)
    
#     for i, result in enumerate(results, 1):
#         print(f"\n[{i}] Score: {result['score']:.4f}")
#         print(f"    Source: {result['source']}")
#         print(f"    Section: {result['section']}")
#         print(f"    Text:\n    {result['text'][:200]}...")
