from backend.components.document_processor import get_pdf_text, create_text_chunks, vectorize_and_store
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from PyPDF2 import PdfReader
from sqlalchemy.orm import Session
from backend.models.schemas import ChatSession
from io import BytesIO
from langchain_community.vectorstores import Chroma
from backend.chroma_client_singleton import ChromaClientSingleton


class DocumentService:
    """Service to handle the core document processing logic."""
    
    def __init__(self, embeddings: HuggingFaceEmbeddings, db_session_maker: Session):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embeddings = embeddings
        self.db_session_maker = db_session_maker

    def process_pdfs_to_text(self, uploaded_files):
        """
        Processes a list of uploaded files and returns a single string of all text.
        """
        return get_pdf_text(uploaded_files)
        
    def create_chunks_from_text(self, text):
        """
        Creates document chunks from a string of text.
        """
        text_chunks = create_text_chunks(text)
        return [Document(page_content=t) for t in text_chunks]

    def vectorize_chunks(self, chunks):
        """
        Creates a vector store from document chunks using the pre-initialized embeddings model.
        """
        return vectorize_and_store(chunks, self.embeddings)
      

    def process_documents(self, file_data: list, session_id: str, filenames: list) -> str:
        # Get the shared ChromaDB client
        chroma_client_singleton = ChromaClientSingleton()
        
        # 1. DELETE any pre-existing collection for this session
        try:
            # Check if the collection exists before attempting to delete it
            chroma_client_singleton.client.get_collection(name=session_id)
            chroma_client_singleton.client.delete_collection(name=session_id)
            print(f"ChromaDB collection for session {session_id} deleted successfully.")
        except Exception:
            # Collection may not exist, which is fine for a new chat
            print(f"No existing ChromaDB collection found for session {session_id}. Proceeding.")
        
        all_documents = []
        
        for file in file_data:
            raw_text = ""
            # 2. Extract and chunk text from the new files
            reader = PdfReader(BytesIO(file["content"]))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    raw_text += text
            
            texts = self.text_splitter.split_text(raw_text)
            
            # 3. Create Document objects with metadata for each chunk
            file_name = file["filename"]
            documents = [Document(page_content=t, metadata={"filename": file_name}) for t in texts]
            all_documents.extend(documents)
            
        # 4. Create and persist the NEW collection with the new documents
        if not all_documents:
            print("No text found in the uploaded documents. Aborting vector store creation.")
            return "No text found in the uploaded documents."
            
        chroma_client_singleton = ChromaClientSingleton()
        
        vector_store = Chroma.from_documents(
            all_documents, 
            self.embeddings,
            client=chroma_client_singleton.client,
            collection_name=session_id
        )
    
        
        with self.db_session_maker() as db_session:
            db_entry = db_session.query(ChatSession).filter_by(id=session_id).first()
            if not db_entry:
                db_entry = ChatSession(id=session_id)
                db_session.add(db_entry)
            
            db_entry.uploaded_files = filenames
            db_session.commit()

        return raw_text