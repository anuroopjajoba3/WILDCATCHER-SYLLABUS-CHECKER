from backend_switch import get_backend, build_chroma_retriever

def main():
    models = get_backend()  # Uses backend from .env
    
    print(f"Using backend: {models.name}")
    
    # Example documents to embed
    texts = [
        "Paris is the capital of France.",
        "The moon is Earth's only natural satellite.",
        "Shakespeare wrote many famous plays.",
        "Python is a popular programming language."
    ]

    # Create Chroma vector store
    from langchain_core.documents import Document
    docs = [Document(page_content=t) for t in texts]

    retriever = build_chroma_retriever(models.embeddings, persist_directory="./db_test", collection_name="test_docs")
    retriever.add_documents(docs)

    # Query it
    query = "Who wrote plays?"
    results = retriever.invoke(query)

    print(f"\nQuery: {query}")
    print("Top result(s):")
    for doc in results:
        print("-", doc.page_content)

if __name__ == "__main__":
    main()
