# backend_switch.py
from __future__ import annotations

# Load .env early so both tests and the app see keys/flags
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import os
from dataclasses import dataclass
from typing import Optional, Literal

# Hard-disable Chroma telemetry at process level
os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")

# --- LangChain providers (import softly and fail with clear messages) ---
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
except Exception:
    ChatOpenAI = None
    OpenAIEmbeddings = None

try:
    from langchain_ollama import ChatOllama
except Exception:
    ChatOllama = None

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    HuggingFaceEmbeddings = None

# --- Vector store (Chroma) ---
# Use the modern package; avoids LangChain deprecation warnings
try:
    from langchain_chroma import Chroma
except Exception:
    Chroma = None  # will raise later with a clear error

# Chroma client bits for telemetry/persistence control
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except Exception:
    chromadb = None
    ChromaSettings = None


# ------------ Container for chosen models ------------
@dataclass
class ModelChoices:
    llm: object
    embeddings: object
    name: str  # "openai" | "oss"


# ------------ OpenAI backend ------------
def build_openai(
    chat_model: Optional[str] = None,
    embed_model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
) -> ModelChoices:
    """
    Build OpenAI backend (LLM + embeddings).
    Honors env:
      OPENAI_API_KEY, CHAT_MODEL, EMBED_MODEL, OPENAI_BASE_URL (for compatible servers).
    """
    if ChatOpenAI is None or OpenAIEmbeddings is None:
        raise RuntimeError(
            "OpenAI backend requested but 'langchain-openai' is not installed.\n"
            "Fix: pip install langchain-openai"
        )

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    chat_model = chat_model or os.getenv("CHAT_MODEL", "gpt-4o-mini")
    embed_model = embed_model or os.getenv("EMBED_MODEL", "text-embedding-3-small")
    base_url = os.getenv("OPENAI_BASE_URL")  # leave unset for official OpenAI

    llm = ChatOpenAI(
        model=chat_model,
        temperature=temperature,
        openai_api_key=api_key,
        base_url=base_url,
    )
    embeddings = OpenAIEmbeddings(
        model=embed_model,
        openai_api_key=api_key,
        base_url=base_url,
    )
    return ModelChoices(llm=llm, embeddings=embeddings, name="openai")


# ------------ OSS backend (Ollama + HF embeddings) ------------
def build_oss(
    ollama_model: Optional[str] = None,
    hf_model: Optional[str] = None,
    temperature: float = 0.2,
) -> ModelChoices:
    """
    Build OSS backend:
      - LLM via Ollama (ChatOllama)
      - Embeddings via HuggingFace (HuggingFaceEmbeddings)
    Env overrides:
      OLLAMA_BASE_URL (default http://localhost:11434)
      OLLAMA_CHAT_MODEL (default llama3.1:8b)
      HF_EMBED_MODEL (default sentence-transformers/all-MiniLM-L6-v2)
    """
    if ChatOllama is None:
        raise RuntimeError(
            "OSS backend requested but 'langchain-ollama' is not installed.\n"
            "Fix: pip install langchain-ollama"
        )
    if HuggingFaceEmbeddings is None:
        raise RuntimeError(
            "OSS backend requested but 'langchain-huggingface' (and sentence-transformers) "
            "is not installed.\nFix: pip install langchain-huggingface sentence-transformers"
        )

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = ollama_model or os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
    hf_model = hf_model or os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    llm = ChatOllama(model=ollama_model, base_url=base_url, temperature=temperature)
    embeddings = HuggingFaceEmbeddings(model_name=hf_model)
    return ModelChoices(llm=llm, embeddings=embeddings, name="oss")


# ------------ Switcher ------------
def get_backend(backend: Optional[Literal["openai", "oss"]] = None, **kwargs) -> ModelChoices:
    """
    Choose backend by precedence:
      1) explicit 'backend' argument,
      2) env LLM_BACKEND,
      3) default 'openai'.
    """
    choice = (backend or os.getenv("LLM_BACKEND", "openai")).lower()

    if choice == "openai":
        return build_openai(**kwargs)
    if choice in ("oss", "local", "ollama"):
        return build_oss(**kwargs)

    raise ValueError(f"Unknown backend: {choice!r}. Use 'openai' or 'oss'.")


# ------------ Chroma retriever helper (telemetry OFF) ------------
def build_chroma_retriever(
    embeddings,
    persist_directory: str = "./db",
    collection_name: str = "docs",
    k: int = 5,
):
    """
    Build a Chroma retriever with the given embeddings.

    - Disables Chroma's anonymized telemetry.
    - Persists to `persist_directory`.
    - Respects `collection_name`.
    """
    if Chroma is None or chromadb is None or ChromaSettings is None:
        raise RuntimeError(
            "Chroma integration not available. Install:\n"
            "  pip install chromadb langchain-chroma langchain-community"
        )

    # Preferred path: pass client_settings directly (chromadb >= ~0.5.x)
    try:
        client_settings = ChromaSettings(
            anonymized_telemetry=False,
            persist_directory=persist_directory,
            is_persistent=True,
        )
        db = Chroma(
            embedding_function=embeddings,
            collection_name=collection_name,
            persist_directory=persist_directory,
            client_settings=client_settings,
        )
    except TypeError:
        # Fallback for older chromadb versions: construct a PersistentClient explicitly
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        db = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )

    return db.as_retriever(search_kwargs={"k": k})
