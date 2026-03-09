# PART 1: ROUTER MODEL COMPARISON

Model                          | Intent | Entity | Ent-ND | Combined | JSON% | Consist |    p50 |    p95
--------------------------------------------------------------------------------------------------------
ollama/llama3.1:8b             |  0.800 |  0.825 |  0.781 |    0.800 | 0.925 |   0.933 |   4.7s |   5.7s
ollama/mistral:7b              |  0.200 |  0.200 |  0.062 |    0.175 | 0.225 |   0.992 |   3.3s |   5.9s
ollama/phi3:3.8b               |  0.000 |  0.000 |  0.000 |    0.000 | 0.000 |   1.000 |   0.0s |   0.0s
ollama/gemma2:9b               |  0.000 |  0.000 |  0.000 |    0.000 | 0.000 |   1.000 |   0.0s |   0.0s
groq/llama-3.1-8b-instant      |  0.900 |  0.925 |  0.906 |    0.900 | 0.975 |   1.000 |   6.4s |   7.9s
groq/mixtral-8x7b-32768        |  0.000 |  0.000 |  0.000 |    0.000 | 0.000 |   1.000 |   0.0s |   0.0s
groq/gemma2-9b-it              |  0.000 |  0.000 |  0.000 |    0.000 | 0.000 |   1.000 |   0.0s |   0.0s

BEST ROUTER: groq/llama-3.1-8b-instant (combined=0.900)

PER-QUERY FAILURES (groq/llama-3.1-8b-instant):
  R07 [query] Got intent=document, node_id=unknown
  R27 [action] Got intent=document, node_id=unknown
  R38 [edge_ood] Got intent=query, node_id=unknown
  R39 [edge_ambiguous] Got intent=None, node_id=None


# PART 2: EMBEDDING MODEL COMPARISON

Skipped models: ollama/nomic-embed-text

Model                                    |  HR@3 |   MRR | AvgTop1 |    p50 |    p95
------------------------------------------------------------------------------------
sentence_transformers/all-MiniLM-L6-v2   | 1.000 | 1.000 |   0.653 | 0.006s | 0.011s
sentence_transformers/BAAI/bge-small-en-v1.5 | 1.000 | 1.000 |   0.796 | 0.013s | 0.015s
sentence_transformers/BAAI/bge-large-en-v1.5 | 1.000 | 1.000 |   0.749 | 0.048s | 0.055s
openrouter/openai/text-embedding-3-small | 1.000 | 0.958 |   0.632 | 0.703s | 1.028s
openrouter/openai/text-embedding-3-large | 1.000 | 0.958 |   0.626 | 0.747s | 0.889s

BEST EMBEDDING: sentence_transformers/all-MiniLM-L6-v2 (HR@3=1.000, MRR=1.000)
