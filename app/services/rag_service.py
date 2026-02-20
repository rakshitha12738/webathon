"""
rag_service.py – Retrieval-Augmented Generation (RAG) pipeline.

Flow:
  1. Upload:  PDF → extract text → chunk → embed → store in Qdrant
  2. Ask:     question → embed → retrieve top-k chunks → generate answer

Vector store: Qdrant  (local or cloud)
Embeddings  : sentence-transformers/all-MiniLM-L6-v2  (384-dim)
LLM         : google/flan-t5-base  (local HuggingFace inference)

The LLM is intentionally constrained to answer **only from retrieved context**
so it cannot hallucinate information that was not in the discharge document.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from io import BytesIO
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded heavy dependencies
_embedding_model = None
_llm_pipeline = None
_qdrant_client = None


# ─────────────────────────────────────────────────────────────────────────────
# Initialisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_qdrant(host: str, port: int):
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(host=host, port=port)
    return _qdrant_client


def _get_embedding_model(model_name: str):
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def _get_llm(model_name: str, max_new_tokens: int = 256):
    global _llm_pipeline
    if _llm_pipeline is None:
        from transformers import pipeline as hf_pipeline
        _llm_pipeline = hf_pipeline(
            "text2text-generation",
            model=model_name,
            max_new_tokens=max_new_tokens,
        )
    return _llm_pipeline


def ensure_collection(host: str, port: int, collection: str, vector_size: int) -> None:
    """
    Create the Qdrant collection if it does not already exist.
    Safe to call on every application start.
    """
    from qdrant_client.models import Distance, VectorParams

    client = _get_qdrant(host, port)
    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Qdrant collection '%s' created.", collection)


# ─────────────────────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF given as raw bytes."""
    import pypdf

    reader = pypdf.PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


# ─────────────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Split *text* into overlapping word-level chunks.

    Parameters
    ----------
    text       : full document text
    chunk_size : approximate number of words per chunk
    overlap    : number of words shared between consecutive chunks
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Upload pipeline
# ─────────────────────────────────────────────────────────────────────────────

def process_and_store_document(
    file_bytes: bytes,
    patient_id: str,
    document_id: str,
    config: Any,
) -> dict[str, Any]:
    """
    Full upload pipeline:
      1. Extract text from PDF
      2. Chunk the text
      3. Embed each chunk
      4. Upsert vectors into Qdrant with patient / document metadata

    Returns a dict with ``extracted_text`` and ``chunks_stored`` count.
    """
    from qdrant_client.models import PointStruct

    extracted_text = extract_text_from_pdf(file_bytes)
    if not extracted_text.strip():
        raise ValueError("No text could be extracted from the uploaded PDF.")

    chunks = _chunk_text(
        extracted_text,
        chunk_size=config.RAG_CHUNK_SIZE,
        overlap=config.RAG_CHUNK_OVERLAP,
    )
    model = _get_embedding_model(config.EMBEDDING_MODEL)
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    client = _get_qdrant(config.QDRANT_HOST, config.QDRANT_PORT)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i],
            payload={
                "patient_id": patient_id,
                "document_id": document_id,
                "chunk_index": i,
                "text": chunks[i],
            },
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=config.QDRANT_COLLECTION, points=points)

    return {"extracted_text": extracted_text, "chunks_stored": len(chunks)}


# ─────────────────────────────────────────────────────────────────────────────
# Ask pipeline
# ─────────────────────────────────────────────────────────────────────────────

# Danger keywords that, if found in retrieved context, trigger an alert flag
_DANGER_PATTERNS = re.compile(
    r"\b(emergency|seek immediate|call 911|call 999|severe bleeding|"
    r"chest pain|difficulty breathing|stroke|suicidal|crisis)\b",
    re.IGNORECASE,
)


def retrieve_and_answer(
    question: str,
    patient_id: str,
    config: Any,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    RAG ask pipeline:
      1. Embed the question
      2. Retrieve top-k most similar chunks from Qdrant (filtered by patient)
      3. Concatenate chunks as context
      4. Prompt the LLM **strictly** using that context
      5. Check for danger keywords in context

    Returns a dict with ``answer``, ``alert``, and ``sources`` keys.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    model = _get_embedding_model(config.EMBEDDING_MODEL)
    question_vec = model.encode([question], show_progress_bar=False)[0].tolist()

    client = _get_qdrant(config.QDRANT_HOST, config.QDRANT_PORT)
    results = client.search(
        collection_name=config.QDRANT_COLLECTION,
        query_vector=question_vec,
        limit=top_k,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="patient_id", match=MatchValue(value=patient_id)
                )
            ]
        ),
        with_payload=True,
    )

    if not results:
        return {
            "answer": (
                "I could not find relevant information in your discharge documents. "
                "Please consult your healthcare provider."
            ),
            "alert": False,
            "sources": [],
        }

    context_chunks = [hit.payload.get("text", "") for hit in results]
    context = "\n\n".join(context_chunks)

    # Danger-keyword check on retrieved context
    alert = bool(_DANGER_PATTERNS.search(context))

    # Grounded prompt – LLM is explicitly told to use only the provided context
    prompt = (
        "You are a medical assistant. Answer the question using ONLY the "
        "information provided below. If the answer is not in the context, "
        "say 'I don't have enough information to answer this question safely.'\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    llm = _get_llm(config.LLM_MODEL, max_new_tokens=config.LLM_MAX_NEW_TOKENS)
    raw = llm(prompt)
    answer = raw[0]["generated_text"].strip() if raw else ""

    return {
        "answer": answer,
        "alert": alert,
        "sources": [
            {"chunk_index": hit.payload.get("chunk_index"), "score": hit.score}
            for hit in results
        ],
    }
