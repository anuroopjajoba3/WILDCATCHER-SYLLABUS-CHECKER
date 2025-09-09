from backend_switch import build_chroma_retriever

def search_docs(query, models):
    retriever = build_chroma_retriever(models.embeddings)
    results = retriever.get_relevant_documents(query)
    return results
