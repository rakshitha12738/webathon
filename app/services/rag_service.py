"""
RAG (Retrieval-Augmented Generation) service using Qdrant and Google Gemini
"""
import os
import PyPDF2
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from app.utils.config import Config
from app.services.firebase_service import FirebaseService

# Danger keywords that always trigger alert_flag regardless of context
DANGER_KEYWORDS = [
    'emergency', 'urgent', 'severe', 'immediately', 'danger',
    'critical', 'call 911', '999', 'ambulance', 'chest pain',
    'difficulty breathing', "can't breathe", 'unconscious', 'collapse',
    'heart attack', 'stroke', 'haemorrhage', 'hemorrhage'
]

def _is_danger(*texts) -> bool:
    """Return True if any danger keyword appears in any of the provided text strings."""
    combined = ' '.join(str(t).lower() for t in texts)
    return any(kw in combined for kw in DANGER_KEYWORDS)


class RAGService:
    """RAG service for document retrieval and question answering via Gemini 2.0 Flash"""

    def __init__(self):
        self.firebase = FirebaseService()

        # ── Qdrant ────────────────────────────────────────────────────────────
        try:
            client = QdrantClient(
                host=Config.QDRANT_HOST,
                port=Config.QDRANT_PORT,
                timeout=3
            )
            client.get_collections()          # probe connection
            self.qdrant_client = client
            print(f"[INFO] Connected to Qdrant at {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
        except Exception:
            print("[WARNING] Qdrant not reachable – using in-memory vector store.")
            self.qdrant_client = QdrantClient(location=":memory:")

        # ── Sentence Transformer embeddings ──────────────────────────────────
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)

        # ── Gemini 2.0 Flash ──────────────────────────────────────────────────
        self.gemini_model = None
        if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != 'your-gemini-api-key-here':
            try:
                import google.generativeai as genai
                genai.configure(api_key=Config.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                print("[INFO] Gemini model initialised (gemini-2.0-flash)")
            except Exception as e:
                print(f"[WARNING] Could not initialise Gemini: {e}")
        else:
            print("[INFO] GEMINI_API_KEY not set – RAG will use fallback mode.")

        self._ensure_collection_exists()

    # ── Collection setup ───────────────────────────────────────────────────────
    def _ensure_collection_exists(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            existing = [c.name for c in self.qdrant_client.get_collections().collections]
            if Config.QDRANT_COLLECTION_NAME not in existing:
                self.qdrant_client.create_collection(
                    collection_name=Config.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"[WARNING] Could not initialise Qdrant collection: {e}")

    # ── PDF utilities ──────────────────────────────────────────────────────────
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract plain text from a PDF file."""
        text = ""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            raise ValueError(f"Error reading PDF: {e}")
        return text.strip()

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """Split text into overlapping word-count chunks."""
        words = text.split()
        chunks, current, cur_len = [], [], 0
        for word in words:
            wl = len(word) + 1
            if cur_len + wl > chunk_size and current:
                chunks.append(' '.join(current))
                overlap_words = current[-overlap:] if len(current) > overlap else current
                current = overlap_words + [word]
                cur_len = sum(len(w) + 1 for w in current)
            else:
                current.append(word)
                cur_len += wl
        if current:
            chunks.append(' '.join(current))
        return chunks

    # ── Upload ─────────────────────────────────────────────────────────────────
    def upload_discharge_document(self, patient_id: str, file_path: str, file_url: str) -> dict:
        """Process a PDF, embed and store chunks in Qdrant, save metadata."""
        text   = self.extract_text_from_pdf(file_path)
        chunks = self.chunk_text(text)

        for idx, chunk in enumerate(chunks):
            embedding = self.embedding_model.encode(chunk).tolist()
            point_id  = abs(hash(f"{patient_id}_{idx}_{chunk[:50]}")) % (10 ** 15)
            self.qdrant_client.upsert(
                collection_name=Config.QDRANT_COLLECTION_NAME,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        'patient_id':  patient_id,
                        'chunk_index': idx,
                        'text':        chunk,
                        'file_url':    file_url
                    }
                )]
            )

        doc_id = self.firebase.create_discharge_document({
            'patient_id':     patient_id,
            'file_url':       file_url,
            'extracted_text': text,
            'chunk_count':    len(chunks)
        })

        return {
            'document_id':      doc_id,
            'chunks_processed': len(chunks),
            'status':           'success'
        }

    # ── Retrieval ──────────────────────────────────────────────────────────────
    def retrieve_relevant_chunks(self, patient_id: str, query: str, top_k: int = 5) -> list:
        """Embed the query and retrieve the top-k matching chunks for this patient."""
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.qdrant_client.search(
            collection_name=Config.QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter={
                "must": [{"key": "patient_id", "match": {"value": patient_id}}]
            },
            limit=top_k
        )
        return [r.payload.get('text', '') for r in results if r.payload]

    # ── Generation ─────────────────────────────────────────────────────────────
    def generate_answer(self, question: str, context_chunks: list) -> dict:
        """
        Generate a RAG answer using Gemini 2.0 Flash given the context chunks.
        alert_flag is True if danger keywords appear in the question OR context.
        Falls back to raw context snippet if Gemini is unavailable.
        """
        context    = "\n\n".join(context_chunks)
        # Check BOTH question and context for danger signals
        alert_flag = _is_danger(question, context)

        # ── Gemini path ───────────────────────────────────────────────────────
        if self.gemini_model:
            prompt = f"""You are a compassionate medical assistant helping a patient understand their hospital discharge instructions.
Answer the patient's question based ONLY on the context extracted from their discharge documents below.
If the information is not available in the context, say: "I cannot find that in your discharge documents – please contact your doctor directly."
Do not invent or guess any medical information.
If the question contains signs of a medical emergency, start your answer with a clear emergency warning.

--- DISCHARGE DOCUMENT CONTEXT ---
{context}
--- END OF CONTEXT ---

Patient's question: {question}

Provide a clear, concise, helpful answer:"""

            try:
                response = self.gemini_model.generate_content(prompt)
                answer   = response.text.strip()
                return {'answer': answer, 'alert_flag': alert_flag, 'source': 'gemini'}
            except Exception as e:
                print(f"[ERROR] Gemini generation failed: {e}")
                # fall through to fallback

        # ── Fallback path ─────────────────────────────────────────────────────
        snippet  = context[:600]
        fallback = (
            f"Based on your discharge documents:\n\n"
            f"{snippet}{'...' if len(context) > 600 else ''}\n\n"
            "Please consult your doctor if you need personalised medical advice."
        )
        return {'answer': fallback, 'alert_flag': alert_flag, 'source': 'fallback'}

    # ── General Q&A (no discharge docs available) ─────────────────────────────
    def answer_general_question(self, question: str) -> dict:
        """
        Use Gemini 2.0 Flash for general recovery questions when no discharge docs are
        available for this patient. alert_flag always checked against the question.
        """
        # Always evaluate danger in the question itself
        alert_flag = _is_danger(question)

        if not self.gemini_model:
            return {
                'answer': (
                    "I don't have your discharge documents on file yet. "
                    "Please ask your doctor to upload them, or contact your healthcare provider "
                    "for personalised guidance."
                ),
                'alert_flag': alert_flag,
                'source': 'no_docs'
            }

        # Emergency override — if danger detected, always surface it
        emergency_prefix = ""
        if alert_flag:
            emergency_prefix = (
                "🚨 **EMERGENCY WARNING**: Your question contains signs of a potential medical emergency. "
                "Please call emergency services (911 / 999) or go to your nearest A&E immediately "
                "if you are experiencing a life-threatening situation.\n\n"
            )

        prompt = f"""You are a supportive medical recovery assistant.
The patient has asked a general recovery question (no discharge documents are on file).
Provide helpful, responsible guidance based on standard post-surgical recovery best practices.
Always advise the patient to follow their doctor's specific instructions.
Do not diagnose or prescribe medication.
If the question suggests a medical emergency, state clearly that they must seek immediate care.

Question: {question}"""

        try:
            response   = self.gemini_model.generate_content(prompt)
            answer     = emergency_prefix + response.text.strip()
            # Re-check alert_flag against Gemini's answer too
            alert_flag = alert_flag or _is_danger(response.text)
            return {'answer': answer, 'alert_flag': alert_flag, 'source': 'gemini_general'}
        except Exception as e:
            return {
                'answer': (
                    f"{emergency_prefix}I encountered an issue connecting to the AI. "
                    "Please contact your doctor directly."
                ),
                'alert_flag': alert_flag,
                'source': 'error'
            }
