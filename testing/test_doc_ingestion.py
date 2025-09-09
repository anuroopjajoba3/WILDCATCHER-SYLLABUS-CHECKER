import os
from backend_switch import get_backend, build_chroma_retriever
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_documents_from_file(file_path: str) -> list[Document]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return [Document(page_content=content)]

def main():
    models = get_backend()
    print(f"Using backend: {models.name}")

    # Step 1: Load document
    docs = load_documents_from_file("sample.txt")

    # Step 2: Split text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    print(f"Loaded {len(chunks)} chunks.")

    # Step 3: Build retriever and add chunks
    retriever = build_chroma_retriever(models.embeddings, persist_directory="./db_docs", collection_name="doc_chunks")
    retriever.add_documents(chunks)

    # Step 4: Ask a question
    query = "Who won the Nobel Prize in 1921?"
    results = retriever.invoke(query)

    print("\nQuery:", query)
    print("Top result(s):")
    for doc in results:
        print("-", doc.page_content)

if __name__ == "__main__":
    main()
