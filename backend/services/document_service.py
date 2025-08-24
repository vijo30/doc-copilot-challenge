from http.client import HTTPException
import logging
from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from backend.components.document_processor import get_pdf_text, create_text_chunks, vectorize_and_store
from backend.chroma_client_singleton import ChromaClientSingleton
from backend.services.database_service import DatabaseService, get_database_service
from backend.services.redis_cache_service import RedisCacheService, get_redis_cache_service
from backend.utils.model_loader import get_embeddings_model
from fastapi import Depends

logger = logging.getLogger(__name__)

class DocumentService:
    """Service to handle the core document processing and persistence logic."""
    
    def __init__(
        self,
        db_service: DatabaseService,
        cache_service: RedisCacheService,
        chroma_client: ChromaClientSingleton,
        embeddings,
    ):
        self.db_service = db_service
        self.cache_service = cache_service
        self.chroma_client = chroma_client
        self.embeddings = embeddings

    def process_documents(self, session_id: str, file_data: List[Dict[str, Any]]):
        """
        Processes uploaded documents and stores them in a vector store.
        """
        try:
            try:
                self.chroma_client.client.get_collection(name=session_id)
                self.chroma_client.client.delete_collection(name=session_id)
                logger.info(f"Existing ChromaDB collection for session {session_id} deleted.")
            except Exception:
                logger.info(f"No existing ChromaDB collection found for session {session_id}. Proceeding.")

            all_documents = []
            filenames = [file['filename'] for file in file_data]
            
            for file in file_data:
                raw_text = get_pdf_text([file])
                
                if not raw_text:
                    logger.warning(f"No text found in file {file['filename']}. Skipping.")
                    continue

                texts = create_text_chunks(raw_text)
                documents = [Document(page_content=t, metadata={"filename": file["filename"]}) for t in texts]
                all_documents.extend(documents)
            
            if not all_documents:
                raise ValueError("No text found in the uploaded documents.")

            vectorize_and_store(all_documents, self.embeddings, self.chroma_client.client, session_id)
            
            self.db_service.update_uploaded_files(session_id, filenames)
            
            self.cache_service.set_flag(f"vector_store_ready:{session_id}")
            
            logger.info(f"Successfully processed {len(all_documents)} document chunks for session {session_id}.")
            return {"status": "complete", "session_id": session_id}
        
        except Exception as e:
            logger.error(f"Error processing documents for session {session_id}: {e}", exc_info=True)
            raise
    
    def get_filenames(self, session_id: str) -> List[str]:
        """Retrieves filenames associated with a chat session."""
        chat_session = self.db_service.get_session(session_id)
        return chat_session.uploaded_files if chat_session else []

    def get_vector_store(self, session_id: str) -> Optional[Chroma]:
        """Returns the Chroma vector store instance for a session."""
        if not self.cache_service.get_flag(f"vector_store_ready:{session_id}"):
            return None
        return Chroma(
            client=self.chroma_client.client,
            embedding_function=self.embeddings,
            collection_name=session_id
        )
        
    def delete_vector_store(self, session_id: str):
        """
        Deletes the ChromaDB collection associated with the session ID.
        """
        try:
            self.chroma_client.client.delete_collection(name=session_id)
            logger.info(f"Successfully deleted ChromaDB collection for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collection for session {session_id}: {e}")
            pass


# --- Dependency Injection for FastAPI ---
def get_document_service(
    db_service: DatabaseService = Depends(get_database_service),
    cache_service: RedisCacheService = Depends(get_redis_cache_service),
) -> DocumentService:
    """
    Dependency that provides a DocumentService instance with all its dependencies.
    """
    return DocumentService(
        db_service=db_service,
        cache_service=cache_service,
        chroma_client=ChromaClientSingleton(),
        embeddings=get_embeddings_model()
    )

def get_vector_store_dependency(
    session_id: str,
    doc_service: DocumentService = Depends(get_document_service),
) -> Chroma:
    """
    This is the new dependency that directly retrieves the vector store.
    It takes 'session_id' as a parameter, which is provided by the endpoint.
    """
    vector_store = doc_service.get_vector_store(session_id)
    if not vector_store:
        raise HTTPException(status_code=404, detail="Vector store not found. Documents must be processed first.")
    return vector_store