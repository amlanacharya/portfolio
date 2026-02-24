from typing import List, Dict, Tuple
import numpy as np
import faiss
import pickle
from pathlib import Path

class FAISSService:
    def __init__(self, dimension: int = 384, index_type: str = "l2"):
        """Initialize FAISS index service
        
        Args:
            dimension: Dimension of embeddings (384 for MiniLM-L6-v2)
            index_type: Type of index ('l2' or 'cosine')
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index = self._create_index()
        self.chunk_store: List[Dict] = []  # Store chunks with their metadata
        
    def _create_index(self) -> faiss.Index:
        """Create a new FAISS index"""
        if self.index_type == "cosine":
            # For cosine similarity
            return faiss.IndexFlatIP(self.dimension)  # Inner Product
        else:
            # For L2 distance (default)
            return faiss.IndexFlatL2(self.dimension)

    def add_chunks(self, chunks: List[Dict]) -> None:
        """Add chunks and their embeddings to the index"""
        # Extract embeddings from chunks
        embeddings = [chunk['embedding'] for chunk in chunks]
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Store the starting index for this batch
        start_idx = len(self.chunk_store)
        
        # Add embeddings to FAISS index
        self.index.add(embeddings_array)
        
        # Store chunks with their index positions
        for i, chunk in enumerate(chunks):
            chunk_data = {
                'text': chunk['text'],
                'metadata': chunk.get('metadata', {}),
                'index': start_idx + i
            }
            self.chunk_store.append(chunk_data)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict]:
        """Search for most similar chunks
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            List of dictionaries containing matched chunks and their scores
        """
        # Ensure query embedding is in correct shape
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # Perform search
        distances, indices = self.index.search(query_embedding, k)
        
        # Prepare results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx != -1:  # Valid index
                chunk_data = self.chunk_store[idx]
                results.append({
                    'text': chunk_data['text'],
                    'metadata': chunk_data['metadata'],
                    'score': float(1 / (1 + dist)) if self.index_type == "l2" else float(dist),
                    'rank': i + 1
                })
        
        return results

    def save_index(self, directory: Path) -> None:
        """Save FAISS index and chunk store to disk"""
        directory.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(directory / "index.faiss"))
        
        # Save chunk store
        with open(directory / "chunk_store.pkl", "wb") as f:
            pickle.dump(self.chunk_store, f)

    def load_index(self, directory: Path) -> None:
        """Load FAISS index and chunk store from disk"""
        # Load FAISS index
        self.index = faiss.read_index(str(directory / "index.faiss"))
        
        # Load chunk store
        with open(directory / "chunk_store.pkl", "rb") as f:
            self.chunk_store = pickle.load(f) 