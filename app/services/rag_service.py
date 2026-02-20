"""
RAG (Retrieval-Augmented Generation) service using Qdrant and OpenAI
"""
import os
import PyPDF2
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from app.utils.config import Config
from app.services.firebase_service import FirebaseService

class RAGService:
    """RAG service for document retrieval and question answering"""
    
    def __init__(self):
        self.firebase = FirebaseService()
        # Try connecting to Qdrant server; fall back to in-memory mode if unavailable
        try:
            client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT, timeout=3)
            client.get_collections()  # probe connection
            self.qdrant_client = client
            print(f"[INFO] Connected to Qdrant at {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
        except Exception:
            print("[WARNING] Qdrant server not reachable. Using in-memory vector store.")
            self.qdrant_client = QdrantClient(location=":memory:")
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
        
        # Initialize collection if it doesn't exist
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if Config.QDRANT_COLLECTION_NAME not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=Config.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 produces 384-dimensional vectors
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Warning: Could not initialize Qdrant collection: {e}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
        
        return text.strip()
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """
        Split text into chunks for embedding
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Start new chunk with overlap
                overlap_words = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def upload_discharge_document(self, patient_id: str, file_path: str, file_url: str) -> dict:
        """
        Process and upload discharge document
        
        Args:
            patient_id: Patient user ID
            file_path: Local path to PDF file
            file_url: URL of uploaded file in Firebase Storage
            
        Returns:
            Dictionary with document ID and status
        """
        # Extract text from PDF
        extracted_text = self.extract_text_from_pdf(file_path)
        
        # Chunk the text
        chunks = self.chunk_text(extracted_text)
        
        # Generate embeddings and store in Qdrant
        point_ids = []
        for idx, chunk in enumerate(chunks):
            embedding = self.embedding_model.encode(chunk).tolist()
            
            point_id = hash(f"{patient_id}_{idx}_{chunk[:50]}")
            point_ids.append(point_id)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    'patient_id': patient_id,
                    'chunk_index': idx,
                    'text': chunk,
                    'file_url': file_url
                }
            )
            
            self.qdrant_client.upsert(
                collection_name=Config.QDRANT_COLLECTION_NAME,
                points=[point]
            )
        
        # Save document metadata to Firestore
        doc_data = {
            'patient_id': patient_id,
            'file_url': file_url,
            'extracted_text': extracted_text,
            'chunk_count': len(chunks)
        }
        
        doc_id = self.firebase.create_discharge_document(doc_data)
        
        return {
            'document_id': doc_id,
            'chunks_processed': len(chunks),
            'status': 'success'
        }
    
    def retrieve_relevant_chunks(self, patient_id: str, query: str, top_k: int = 5) -> list:
        """
        Retrieve relevant chunks from Qdrant based on query
        
        Args:
            patient_id: Patient user ID
            query: User query/question
            top_k: Number of top chunks to retrieve
            
        Returns:
            List of relevant text chunks
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Search in Qdrant
        search_results = self.qdrant_client.search(
            collection_name=Config.QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter={
                "must": [
                    {
                        "key": "patient_id",
                        "match": {"value": patient_id}
                    }
                ]
            },
            limit=top_k
        )
        
        chunks = []
        for result in search_results:
            if result.payload:
                chunks.append(result.payload.get('text', ''))
        
        return chunks
    
    def generate_answer(self, question: str, context_chunks: list) -> dict:
        """
        Generate answer using OpenAI based on retrieved context
        
        Args:
            question: User question
            context_chunks: Retrieved context chunks
            
        Returns:
            Dictionary with answer and alert flag
        """
        if not self.openai_client:
            # Fallback: return simple response if OpenAI is not configured
            combined_context = "\n\n".join(context_chunks[:3])
            return {
                'answer': f"Based on your discharge documents: {combined_context[:500]}...",
                'alert_flag': False,
                'source': 'fallback'
            }
        
        # Combine context chunks
        context = "\n\n".join(context_chunks)
        
        # Check for danger indicators in context
        danger_keywords = ['emergency', 'urgent', 'severe', 'immediately', 'danger', 'critical', 'call 911']
        alert_flag = any(keyword.lower() in context.lower() for keyword in danger_keywords)
        
        # Construct prompt
        prompt = f"""You are a medical assistant helping a patient understand their discharge instructions. 
Answer the patient's question based ONLY on the provided context from their discharge documents.
Do NOT make up information or use knowledge outside the provided context.
If the information is not in the context, say "I cannot find that information in your discharge documents. Please consult your doctor."

Context from discharge documents:
{context}

Patient's question: {question}

Provide a clear, helpful answer based only on the context above:"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful medical assistant. Only answer based on the provided context. Do not hallucinate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                'answer': answer,
                'alert_flag': alert_flag,
                'source': 'openai'
            }
        except Exception as e:
            # Fallback response
            return {
                'answer': f"I encountered an error processing your question. Please consult your doctor directly. Error: {str(e)}",
                'alert_flag': alert_flag,
                'source': 'error_fallback'
            }

