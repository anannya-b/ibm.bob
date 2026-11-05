"""
rag_pipeline.py – RAG (Retrieval-Augmented Generation) Pipeline
================================================================
Handles document loading, chunking, embedding via sentence-transformers,
and vector storage/retrieval using ChromaDB.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"
CHROMA_PERSIST_DIR = Path(__file__).parent / "chroma_db"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Module-level cached vector store (avoid re-loading on every request)
_vector_store: Optional[Chroma] = None


def _load_documents() -> list:
    """
    Load all .txt files from the knowledge_base directory.

    Returns:
        list: A list of LangChain Document objects.
    """
    documents = []
    txt_files = list(KNOWLEDGE_BASE_DIR.glob("*.txt"))

    if not txt_files:
        logger.warning("No .txt files found in %s", KNOWLEDGE_BASE_DIR)
        return documents

    for txt_file in txt_files:
        try:
            loader = TextLoader(str(txt_file), encoding="utf-8")
            docs = loader.load()
            # Tag each document with its source filename for reference
            for doc in docs:
                doc.metadata["source_file"] = txt_file.name
            documents.extend(docs)
            logger.info("Loaded: %s (%d characters)", txt_file.name, sum(len(d.page_content) for d in docs))
        except Exception as exc:
            logger.error("Failed to load %s: %s", txt_file.name, exc)

    logger.info("Total documents loaded: %d", len(documents))
    return documents


def _build_vector_store(embeddings: HuggingFaceEmbeddings) -> Chroma:
    """
    Build the ChromaDB vector store from scratch by loading and chunking all
    knowledge base documents, then embedding and persisting them.

    Args:
        embeddings: HuggingFaceEmbeddings instance.

    Returns:
        Chroma: A persistent ChromaDB vector store.
    """
    logger.info("Building vector store from knowledge base documents…")
    documents = _load_documents()

    if not documents:
        raise RuntimeError("No documents found in knowledge base. Cannot build vector store.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info("Created %d chunks from %d documents", len(chunks), len(documents))

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
    )
    logger.info("Vector store built and persisted to %s", CHROMA_PERSIST_DIR)
    return vector_store


def _get_embeddings() -> HuggingFaceEmbeddings:
    """
    Instantiate the HuggingFace sentence-transformer embeddings model.

    Returns:
        HuggingFaceEmbeddings: Embeddings instance using all-MiniLM-L6-v2.
    """
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vector_store() -> Chroma:
    """
    Get the global vector store instance, building it if it does not yet exist.
    On first call: builds the index from knowledge base files.
    On subsequent calls: loads the persisted index from disk.

    Returns:
        Chroma: The ChromaDB vector store.
    """
    global _vector_store

    if _vector_store is not None:
        return _vector_store

    embeddings = _get_embeddings()

    # Check if a persisted store already exists
    chroma_files = list(CHROMA_PERSIST_DIR.glob("**/*")) if CHROMA_PERSIST_DIR.exists() else []
    has_persisted = any(f.is_file() for f in chroma_files)

    if has_persisted:
        logger.info("Loading existing vector store from %s", CHROMA_PERSIST_DIR)
        _vector_store = Chroma(
            persist_directory=str(CHROMA_PERSIST_DIR),
            embedding_function=embeddings,
        )
        # Validate the store has documents
        count = _vector_store._collection.count()
        logger.info("Loaded vector store with %d chunks", count)
        if count == 0:
            logger.warning("Persisted store is empty — rebuilding from knowledge base")
            _vector_store = _build_vector_store(embeddings)
    else:
        logger.info("No persisted store found — building from scratch")
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _vector_store = _build_vector_store(embeddings)

    return _vector_store


def retrieve_context(query: str, k: int = 4) -> str:
    """
    Retrieve the most relevant context chunks from the knowledge base for a
    given query using semantic similarity search.

    Args:
        query: The user's question or search string.
        k:     Number of top-k chunks to retrieve (default: 4).

    Returns:
        str: Concatenated context string from the top-k relevant chunks,
             separated by double newlines.
    """
    try:
        store = get_vector_store()
        results = store.similarity_search(query, k=k)

        if not results:
            logger.warning("No results found for query: %s", query[:80])
            return ""

        context_parts = []
        for doc in results:
            source = doc.metadata.get("source_file", "unknown")
            context_parts.append(f"[Source: {source}]\n{doc.page_content.strip()}")

        context = "\n\n".join(context_parts)
        logger.info(
            "Retrieved %d chunks for query '%s…' (total %d chars)",
            len(results),
            query[:40],
            len(context),
        )
        return context

    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        return ""


def rebuild_index() -> bool:
    """
    Force-rebuild the vector store index from the knowledge base files.
    Useful after adding new documents to the knowledge base directory.

    Returns:
        bool: True if rebuild succeeded, False otherwise.
    """
    global _vector_store
    try:
        import shutil
        if CHROMA_PERSIST_DIR.exists():
            shutil.rmtree(CHROMA_PERSIST_DIR)
            logger.info("Removed existing index at %s", CHROMA_PERSIST_DIR)
        _vector_store = None
        get_vector_store()
        return True
    except Exception as exc:
        logger.error("Index rebuild failed: %s", exc)
        return False
