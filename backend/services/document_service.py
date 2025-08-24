from asyncio.log import logger
from backend.components.document_processor import get_pdf_text, create_text_chunks, vectorize_and_store
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from sqlalchemy.orm import Session
from backend.models.schemas import ChatSession
from backend.chroma_client_singleton import ChromaClientSingleton

class DocumentService:
    """Service to handle the core document processing and persistence logic."""
    
    def __init__(self, embeddings: HuggingFaceEmbeddings, db_session_maker: Session):
        self.embeddings = embeddings
        self.db_session_maker = db_session_maker
        self.chroma_client_singleton = ChromaClientSingleton()

    def process_documents(self, file_data: list, session_id: str, filenames: list) -> str:
        """
        Processes uploaded documents, stores them in a vector store, and updates the database.
        
        Args:
            file_data: A list of dictionaries, each containing file content and metadata.
            session_id: The ID of the current chat session.
            filenames: A list of the names of the uploaded files.

        Returns:
            A string indicating the result of the process.
        """
        try:
          try:
              self.chroma_client_singleton.client.get_collection(name=session_id)
              self.chroma_client_singleton.client.delete_collection(name=session_id)
              print(f"ChromaDB collection for session {session_id} deleted successfully.")
          except Exception:
              print(f"No existing ChromaDB collection found for session {session_id}. Proceeding.")

          all_documents = []
          raw_text_combined = ""

          for file in file_data:
              raw_text = get_pdf_text([file])
              raw_text_combined += raw_text

              if not raw_text:
                  print(f"No text found in file {file['filename']}. Skipping.")
                  continue

              texts = create_text_chunks(raw_text)
              documents = [Document(page_content=t, metadata={"filename": file["filename"]}) for t in texts]
              all_documents.extend(documents)

          if not all_documents:
              print("No text found in the uploaded documents. Aborting vector store creation.")
              return "No text found in the uploaded documents."

          vectorize_and_store(all_documents, self.embeddings, self.chroma_client_singleton.client, session_id)
          
          with self.db_session_maker() as db_session:
              db_entry = db_session.query(ChatSession).filter_by(id=session_id).first()
              if not db_entry:
                  db_entry = ChatSession(id=session_id)
                  db_session.add(db_entry)
              
              db_entry.uploaded_files = filenames
              db_session.commit()
              
          self.redis_cache_service.set_flag(f"vector_store_ready:{session_id}")
              
          return f"Successfully processed {len(all_documents)} document chunks from {len(file_data)} files."
        except Exception as e:
            logger.error(f"Error processing documents for session {session_id}: {e}", exc_info=True)
            raise