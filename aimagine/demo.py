from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables at the start of the script
load_dotenv()

print("Environment variables loaded:")
print(f"GROQ_API_KEY exists: {'GROQ_API_KEY' in os.environ}")
print(f"GROQ_MODEL_NAME: {os.getenv('GROQ_MODEL_NAME')}")

from src.services.data_ingestion import DataIngestionService
from src.services.embedding_service import EmbeddingService
from src.services.faiss_service import FAISSService
from src.services.llm_service import LLMService

def setup_knowledge_base(file_path: Path, index_path: Path):
    """Set up and index the knowledge base"""
    # Initialize services
    ingestion_service = DataIngestionService()
    embedding_service = EmbeddingService()
    faiss_service = FAISSService()
    
    # Process document
    print("Processing document...")
    document = ingestion_service.process_file(file_path)
    
    # Generate embeddings
    print("Generating embeddings...")
    chunks_with_embeddings = embedding_service.generate_embeddings(document['chunks'])
    
    # Add to FAISS index
    print("Adding to FAISS index...")
    faiss_service.add_chunks(chunks_with_embeddings)
    
    # Save index for later use
    print("Saving index...")
    faiss_service.save_index(index_path)
    return faiss_service

def search_and_respond(query: str, 
                      faiss_service: FAISSService, 
                      embedding_service: EmbeddingService,
                      llm_service: LLMService):
    """Search knowledge base and generate LLM response"""
    # Generate query embedding
    query_embedding = embedding_service.generate_query_embedding(query)
    
    # Search for similar chunks
    results = faiss_service.search(query_embedding, k=3)
    
    # Generate LLM response using retrieved context
    llm_response = llm_service.generate_response(query, results)
    
    # Generate follow-up questions
    followup_questions = llm_service.generate_followup_questions(query, llm_response)
    
    return results, llm_response, followup_questions

# Example usage
if __name__ == "__main__":
    # Use the existing knowledge_base.md file
    file_path = Path("knowledge_base.md")
    index_path = Path("index")
    
    print(f"Processing file: {file_path}")
    
    # Initial setup
    faiss_service = setup_knowledge_base(file_path, index_path)
    embedding_service = EmbeddingService()
    llm_service = LLMService()
    
    # Test queries
    test_queries = [
        "What is the baggage policy for economy class?",
        "Can I bring my pet on the flight?",
        "What's your cancellation policy?"
    ]
    
    # Run tests
    for query in test_queries:
        print("\n" + "="*50)
        print(f"\nTesting Query: {query}")
        print("="*50)
        
        results, llm_response, followup_questions = search_and_respond(
            query, faiss_service, embedding_service, llm_service
        )
        
        # Print raw search results
        print("\nRelevant Chunks Found:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.4f}")
            print(f"Text: {result['text'][:200]}...")
        
        # Print LLM response
        print("\nLLM Response:")
        print(llm_response)
        
        # Print follow-up questions
        print("\nSuggested Follow-up Questions:")
        for i, question in enumerate(followup_questions, 1):
            print(f"{i}. {question}")
        
        print("\n" + "="*50)