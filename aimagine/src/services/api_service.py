from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from pathlib import Path
import uvicorn
import os
import re
import numpy as np
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

from .data_ingestion import DataIngestionService
from .embedding_service import EmbeddingService
from .faiss_service import FAISSService

app = FastAPI(
    title="Airline Knowledge Base API",
    description="Search and retrieve information from airline knowledge base",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class SearchQuery(BaseModel):
    text: str = Field(..., description="The search query text")
    num_results: int = Field(default=3, ge=1, le=10, description="Number of results to return")
    min_score: float = Field(default=0.3, ge=0, le=1, description="Minimum similarity score threshold")

class SearchResponse(BaseModel):
    text: str
    score: float
    metadata: dict
    context: Optional[str] = None

class SearchResult(BaseModel):
    text: str
    score: float
    metadata: dict
    context: Optional[str] = None

class KnowledgeBaseService:
    def __init__(self):
        # Initialize Neo4j connection
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME')
        self.password = os.getenv('NEO4J_PASSWORD')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        
        # Initialize SBERT model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def simple_sentence_tokenize(self, text: str) -> List[str]:
        """Simple sentence tokenization using regex."""
        # Split on period followed by space or newline
        sentences = re.split(r'\.(?:\s+|\n+)', text)
        # Clean and filter empty sentences
        return [s.strip() + '.' for s in sentences if s.strip()]

    def chunk_text(self, text: str, max_sentences: int = 3, overlap: int = 1) -> List[Dict]:
        # Split text into sections based on '#' headers
        sections = text.split('#')[1:]  # Skip the first empty split
        chunks = []
        
        for section in sections:
            # Split into subsections
            subsections = re.split(r'\n(?=\d+\.(?:\d+\.)*\s)', section)
            
            for subsection in subsections:
                if not subsection.strip():
                    continue
                    
                # Get the section title/context
                lines = subsection.strip().split('\n')
                context = lines[0].strip()
                
                # Get the content
                content = '\n'.join(lines[1:]).strip()
                if not content:
                    continue
                
                # Tokenize into sentences
                sentences = self.simple_sentence_tokenize(content)
                
                # Create overlapping chunks
                for i in range(0, len(sentences), max_sentences - overlap):
                    chunk_sentences = sentences[i:i + max_sentences]
                    if chunk_sentences:
                        chunks.append({
                            'context': context,
                            'text': ' '.join(chunk_sentences)
                        })
        
        return chunks
    def generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for each chunk."""
        for chunk in chunks:
            # Combine context and text for better semantic understanding
            combined_text = f"{chunk['context']}: {chunk['text']}"
            embedding = self.model.encode(combined_text)
            
            # Convert to list, handling both numpy arrays and lists
            if isinstance(embedding, np.ndarray):
                chunk['embedding'] = embedding.tolist()
            else:
                chunk['embedding'] = list(embedding)
                
        return chunks

    def get_total_chunks(self) -> int:
        """Get total number of chunks stored in Neo4j."""
        with self.driver.session() as session:
            result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
            return result.single()['count']

    def get_chunk_by_id(self, chunk_id: int) -> Optional[Dict]:
        """Retrieve a specific chunk from Neo4j."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c:Chunk {id: $chunk_id}) RETURN c",
                chunk_id=chunk_id
            )
            record = result.single()
            if record:
                return dict(record['c'])
            return None
    def store_chunks(self, chunks: List[Dict]):
        """Store chunks in Neo4j."""
        def create_chunk(tx, chunk, chunk_id):
            query = """
            CREATE (c:Chunk {
                id: $chunk_id,
                context: $context,
                text: $text,
                embedding: $embedding
            })
            """
            tx.run(query, 
                   chunk_id=chunk_id,
                   context=chunk['context'],
                   text=chunk['text'],
                   embedding=chunk['embedding'])

        with self.driver.session() as session:
            # First, clear existing chunks
            session.run("MATCH (c:Chunk) DELETE c")
            
            # Store new chunks
            for i, chunk in enumerate(chunks):
                session.execute_write(create_chunk, chunk, i)

    def process_knowledge_base(self, file_path: str) -> int:
        """Process knowledge base file and return number of chunks created."""
        try:
            # Verify database connection first
            if not self.verify_database_connection():
                raise Exception("Could not connect to database. Please check your connection settings.")

            # Read and process the knowledge base file
            with open(file_path, 'r') as file:
                content = file.read()

            # Process the content
            chunks = self.chunk_text(content)
            if not chunks:
                raise ValueError("No chunks were generated from the knowledge base")

            # Generate embeddings
            chunks_with_embeddings = self.generate_embeddings(chunks)
            
            # Store in Neo4j
            self.store_chunks(chunks_with_embeddings)
            
            # Verify storage
            total_chunks = self.get_total_chunks()
            if total_chunks != len(chunks_with_embeddings):
                raise ValueError(f"Storage verification failed. Expected {len(chunks_with_embeddings)} chunks, found {total_chunks}")
            
            return total_chunks

        except Exception as e:
            raise e

    def search(self, query_text: str, num_results: int = 3, min_score: float = 0.3) -> List[SearchResult]:
        """Search for relevant chunks using semantic similarity."""
        # Generate embedding for the query
        query_embedding = self.model.encode(query_text)
        
        # Search in Neo4j using cosine similarity
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Chunk)
                WITH c, gds.similarity.cosine(c.embedding, $query_embedding) AS score
                WHERE score >= $min_score
                RETURN c.text as text, c.context as context, score
                ORDER BY score DESC
                LIMIT $num_results
            """, query_embedding=query_embedding.tolist(), min_score=min_score, num_results=num_results)
            
            return [
                SearchResult(
                    text=record["text"],
                    score=float(record["score"]),
                    metadata={},  # You can add metadata if needed
                    context=record["context"]
                )
                for record in result
            ]

    def verify_database_connection(self) -> bool:
        """Verify Neo4j database connection is working."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                return result.single()[0] == 1
        except Exception:
            return False

# Initialize knowledge base service
kb_service = KnowledgeBaseService()

@app.post("/api/search", 
    response_model=List[SearchResponse],
    tags=["Search"],
    summary="Search knowledge base",
    response_description="List of relevant text chunks with similarity scores")
async def search(query: SearchQuery):
    """
    Search the knowledge base for relevant information.
    
    - Uses semantic search with FAISS
    - Returns ranked results with similarity scores
    - Filters results below minimum score threshold
    """
    try:
        results = kb_service.search(
            query.text, 
            num_results=query.num_results,
            min_score=query.min_score
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/process-knowledge-base",
    tags=["Knowledge Base"],
    summary="Process a knowledge base file",
    response_description="Number of chunks created")
async def process_knowledge_base(file_path: str = Query(..., description="Path to the knowledge base file")):
    """
    Process a knowledge base file and store its contents in the database.
    
    - Chunks the content into manageable pieces
    - Generates embeddings for each chunk
    - Stores chunks and embeddings in Neo4j
    """
    try:
        total_chunks = kb_service.process_knowledge_base(file_path)
        return {"message": f"Successfully processed knowledge base", "total_chunks": total_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_server():
    """Start the API server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_server() 