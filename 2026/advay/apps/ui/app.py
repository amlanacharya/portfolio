"""Phase 1 Streamlit shell for the Advay platform."""

import streamlit as st


st.set_page_config(page_title="Advay Platform", page_icon="A", layout="wide")

st.title("Advay Platform")
st.caption("Phase 1 foundation shell")

st.write(
    """
    This UI is intentionally minimal in Phase 1.
    It exists only to prove application startup, package structure, and basic project wiring.
    """
)

st.subheader("Current scope")
st.markdown(
    """
    - FastAPI skeleton
    - Streamlit skeleton
    - Health and readiness endpoints
    - Config loader
    - Redis cache adapter
    - Postgres and Neo4j placeholder connectors
    """
)

st.subheader("Not implemented yet")
st.markdown(
    """
    - Pinecone retrieval
    - LangGraph workflows
    - Embeddings
    - Document parsing
    - KPI business logic
    - Advanced dashboard features
    """
)
