"""
RAG Pipeline - ChromaDB with lazy init and custom lightweight embeddings.
No onnxruntime needed — embeddings are pre-computed using numpy hashing.
"""
import os
import logging
import hashlib
import numpy as np

CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "syllabus_compliance"
GROUND_TRUTH_DIR = os.path.join(os.path.dirname(__file__), "ground_truth_syllabus")


def _get_client():
    """Lazy init — only loads ChromaDB when actually needed."""
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection():
    """Get or create collection. No default embedding function."""
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def embed(texts: list) -> list:
    """Hash-based embedding — no ML model, no onnxruntime."""
    result = []
    for text in texts:
        vec = np.zeros(256, dtype=np.float32)
        text_lower = text.lower()
        for i in range(len(text_lower) - 2):
            ngram = text_lower[i:i+3]
            h = int(hashlib.md5(ngram.encode()).hexdigest(), 16) % 256
            vec[h] += 1
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        result.append(vec.tolist())
    return result


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    """Split text into chunks with a guaranteed minimum advance to prevent infinite loops."""
    chunks, start = [], 0
    text = text.strip()
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            bp = max(chunk.rfind('\n'), chunk.rfind('.'))
            if bp > chunk_size // 2:
                chunk = chunk[:bp+1]
        if chunk.strip():
            chunks.append(chunk.strip())
        # Always advance by at least 50 chars to prevent infinite loop
        advance = max(len(chunk) - overlap, 50)
        start += advance
    return chunks


def ingest_ground_truth_syllabi(force_reingest=False):
    from document_processing import extract_text_from_pdf, extract_text_from_docx
    collection = get_collection()
    if collection.count() > 0 and not force_reingest:
        logging.info(f"Already have {collection.count()} chunks. Skipping.")
        return collection.count()
    if force_reingest:
        _get_client().delete_collection(COLLECTION_NAME)
        collection = get_collection()
    files = [f for f in os.listdir(GROUND_TRUTH_DIR)
             if (f.endswith('.pdf') or f.endswith('.docx')) and not f.startswith('~')]
    total = 0
    for i, filename in enumerate(files):
        path = os.path.join(GROUND_TRUTH_DIR, filename)
        try:
            text = extract_text_from_pdf(path) if filename.endswith('.pdf') else extract_text_from_docx(path)
            if not text or len(text.strip()) < 100:
                print(f"[{i+1}/{len(files)}] SKIP {filename}")
                continue
            chunks = chunk_text(text)
            for k in range(0, len(chunks), 10):
                batch = chunks[k:k+10]
                collection.add(
                    documents=batch,
                    embeddings=embed(batch),
                    ids=[f"{filename}__c{k+j}" for j in range(len(batch))],
                    metadatas=[{"filename": filename, "chunk_index": k+j} for j in range(len(batch))]
                )
            total += len(chunks)
            print(f"[{i+1}/{len(files)}] ✅ {filename}: {len(chunks)} chunks")
        except Exception as e:
            print(f"[{i+1}/{len(files)}] ❌ {filename}: {e}")
    return total


def search_similar_sections(query: str, n_results: int = 5):
    collection = get_collection()
    if collection.count() == 0:
        return []
    try:
        results = collection.query(
            query_embeddings=embed([query]),
            n_results=min(n_results, collection.count())
        )
        return [
            {"text": doc, "filename": meta.get("filename"), "distance": round(dist, 4)}
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    except Exception as e:
        logging.error(f"ChromaDB search error: {e}")
        return []


def get_rag_context(query: str, n_results: int = 3) -> str:
    chunks = search_similar_sections(query, n_results)
    if not chunks:
        return ""
    return "\n\n---\n\n".join(
        f"[Example {i+1} from '{c['filename']}']\n{c['text']}"
        for i, c in enumerate(chunks)
    )


def get_collection_stats():
    collection = get_collection()
    return {
        "total_chunks": collection.count(),
        "collection_name": COLLECTION_NAME,
        "db_path": CHROMA_DB_PATH,
        "ready": collection.count() > 0
    }