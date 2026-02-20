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

class RAGService:
    """RAG service for document retrieval and question answering via Gemini"""

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

        # ── Gemini ────────────────────────────────────────────────────────────
        self.gemini_model = None
        if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != 'your-gemini-api-key-here':
            try:
                import google.generativeai as genai
                genai.configure(api_key=Config.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
                print("[INFO] Gemini model initialised (gemini-1.5-flash)")
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
            'document_id':    doc_id,
            'chunks_processed': len(chunks),
            'status':         'success'
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
        Generate an answer using Gemini given the context chunks.
        Falls back to a summary of the raw chunks if Gemini is unavailable.
        """
        context = "\n\n".join(context_chunks)

        # Danger keyword check for alert_flag
        danger_keywords = ['emergency', 'urgent', 'severe', 'immediately', 'danger', 'critical', 'call 911', '999', 'ambulance']
        alert_flag = any(kw in context.lower() for kw in danger_keywords)

        # ── Gemini path ───────────────────────────────────────────────────────
        if self.gemini_model:
            prompt = f"""You are a compassionate medical assistant helping a patient understand their hospital discharge instructions.
Answer the patient's question based ONLY on the context extracted from their discharge documents below.
If the information is not available in the context, say: "I cannot find that in your discharge documents – please contact your doctor directly."
Do not invent or guess any medical information.

--- DISCHARGE DOCUMENT CONTEXT ---
{context}
--- END OF CONTEXT ---

Patient's question: {question}

Provide a clear, concise, helpful answer:"""

            try:
                response = self.gemini_model.generate_content(prompt)
                answer = response.text.strip()
                return {'answer': answer, 'alert_flag': alert_flag, 'source': 'gemini'}
            except Exception as e:
                print(f"[ERROR] Gemini generation failed: {e}")
                # fall through to fallback

        # ── Fallback path ─────────────────────────────────────────────────────
        snippet   = context[:600]
        fallback  = (
            f"Based on your discharge documents, here is the most relevant information:\n\n"
            f"{snippet}{'...' if len(context) > 600 else ''}\n\n"
            "Please consult your doctor if you need personalised medical advice."
        )
        return {'answer': fallback, 'alert_flag': alert_flag, 'source': 'fallback'}

    # ── Direct Gemini chat (no RAG context, for general questions) ─────────────
    def answer_general_question(self, question: str) -> dict:
        """Use Gemini for general recovery questions when no discharge docs are available."""
        if not self.gemini_model:
            return {
                'answer': (
                    "I don't have your discharge documents on file yet. "
                    "Please ask your doctor to upload them, or contact your healthcare provider for personalised guidance."
                ),
                'alert_flag': False,
                'source': 'no_docs'
            }

        prompt = f"""You are a supportive medical recovery assistant. The patient has asked a general recovery question.
Provide helpful, responsible general guidance. Always remind the patient to follow their doctor's specific instructions.
Do not provide specific diagnoses or prescribe medication.

Question: {question}"""

        try:
            response  = self.gemini_model.generate_content(prompt)
            answer    = response.text.strip()
            alert_flag = any(kw in answer.lower() for kw in ['emergency','severe','call 911','call 999','ambulance'])
            return {'answer': answer, 'alert_flag': alert_flag, 'source': 'gemini_general'}
        except Exception as e:
            return {
                'answer': f"I encountered an issue. Please contact your doctor directly. ({e})",
                'alert_flag': False,
                'source': 'error'
            }
