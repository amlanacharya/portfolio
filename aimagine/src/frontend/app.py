import streamlit as st
from pathlib import Path
import sys
import os

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.data_ingestion import DataIngestionService
from src.services.embedding_service import EmbeddingService
from src.services.faiss_service import FAISSService
from src.services.llm_service import LLMService

def initialize_services():
    """Initialize all required services"""
    faiss_service = FAISSService()
    
    # Load existing index if available
    index_path = Path(__file__).parent.parent.parent / "index"
    if index_path.exists():
        faiss_service.load_index(index_path)
    
    return {
        'embedding': EmbeddingService(),
        'faiss': faiss_service,
        'ingestion': DataIngestionService(),
        'llm': LLMService()
    }

def setup_page():
    """Configure the Streamlit page"""
    st.set_page_config(
        page_title="Airline Knowledge Base Chat",
        page_icon="✈️",
        layout="wide"
    )
    st.title("✈️ Airline Assistant")

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'services' not in st.session_state:
        st.session_state.services = initialize_services()

def main():
    try:
        setup_page()
        initialize_session_state()

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("How can I help you?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Generate query embedding
                    query_embedding = st.session_state.services['embedding'].generate_query_embedding(prompt)
                    
                    # Search for relevant information
                    results = st.session_state.services['faiss'].search(query_embedding, k=3)
                    
                    # Generate LLM response using retrieved context
                    llm_response = st.session_state.services['llm'].generate_response(prompt, results)
                    
                    # Generate follow-up questions
                    followup_questions = st.session_state.services['llm'].generate_followup_questions(prompt, llm_response)
                    
                    # Format complete response
                    response = f"{llm_response}\n\n---\n\n**Suggested follow-up questions:**\n"
                    for i, question in enumerate(followup_questions, 1):
                        response += f"{i}. {question}\n"
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        if "GROQ_API_KEY" not in os.environ:
            st.error("GROQ_API_KEY not found. Please check your environment variables.")

if __name__ == "__main__":
    main() 