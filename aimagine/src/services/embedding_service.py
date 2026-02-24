from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service with a default lightweight model"""
        self.model = SentenceTransformer(model_name)

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.model.encode(text, normalize_embeddings=True)

    def generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for multiple chunks"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        return chunks

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a search query"""
        return self.generate_embedding(query)