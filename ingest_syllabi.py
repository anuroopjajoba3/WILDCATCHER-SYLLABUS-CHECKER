"""
Ingest ground truth syllabi into ChromaDB with pre-computed embeddings.
"""
import os, logging
logging.basicConfig(level=logging.WARNING)
from rag_pipeline import get_collection, chunk_text, embed, GROUND_TRUTH_DIR
from document_processing import extract_text_from_pdf, extract_text_from_docx

TARGET_FILES = [
    "COMP_405 - Jin_Fall - Fall 2023.pdf",
    "COMP_415 - Harvey_Fall - Fall 2025.pdf",
    "COMP_424 - Sabin_Fall - Fall 2025.docx",
    "COMP_430 - Eglowstein_Fall - Fall 2025.docx",
    "COMP_525 - Jin_Fall - Fall 2025.pdf",
    "COMP_625 - Jonas_Fall - Fall 2025.pdf",
    "COMP_690 - Jin_Fall - Fall 2025.pdf",
    "COMP_720.820 - Finan_Fall - Fall 2025.pdf",
    "COMP_755.855 - Jonas_Fall - Fall 2025.pdf",
    "COMP_801 - Sabin_Fall - Fall 2025.docx",
    "COMP_880 - Greene_Fall - Fall 2025.pdf",
    "COMP_891 - Jin_Fall - Fall 2025.pdf",
    "Math 418 Syllabus Fall 2025.pdf",
    "PSYC 511 Syllabus Fall 2025.pdf",
    "PHYS 401 (M1) Syllabus (Fall 2025).pdf",
]

if __name__ == "__main__":
    collection = get_collection()
    if collection.count() > 0:
        print(f"Already have {collection.count()} chunks. Done.")
        exit()

    total = 0
    for i, filename in enumerate(TARGET_FILES):
        file_path = os.path.join(GROUND_TRUTH_DIR, filename)
        if not os.path.exists(file_path):
            print(f"[{i+1}] SKIP (not found): {filename}")
            continue
        try:
            text = extract_text_from_pdf(file_path) if filename.endswith('.pdf') else extract_text_from_docx(file_path)
            if not text or len(text.strip()) < 100:
                print(f"[{i+1}] SKIP (no text): {filename}")
                continue
            chunks = chunk_text(text)
            for k in range(0, len(chunks), 5):
                batch = chunks[k:k+5]
                collection.add(
                    documents=batch,
                    embeddings=embed(batch),
                    ids=[f"{filename}__c{k+j}" for j in range(len(batch))],
                    metadatas=[{"filename": filename, "chunk_index": k+j} for j in range(len(batch))]
                )
            total += len(chunks)
            print(f"[{i+1}/{len(TARGET_FILES)}] ✅ {filename}: {len(chunks)} chunks")
        except Exception as e:
            print(f"[{i+1}] ❌ {filename}: {e}")

    print(f"\n✅ Done! Total chunks: {collection.count()}")
