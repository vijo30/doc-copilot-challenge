from backend.components.document_processor import get_pdf_text, create_text_chunks, vectorize_and_store
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List
from PyPDF2 import PdfReader
from fastapi import UploadFile
from langchain_community.vectorstores import FAISS
import pickle
from redis import Redis
from sqlalchemy.orm import Session
from backend.models.schemas import ChatSession
from io import BytesIO


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
      
    def process_documents(self, file_data: list, session_id: str) -> str:
        """
        Processes a list of file data (dictionaries), creates a vector store,
        and saves it to the database.
        """
        raw_text = ""
        for file in file_data:
            reader = PdfReader(BytesIO(file["content"]))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    raw_text += text
        
        texts = self.text_splitter.split_text(raw_text)
        vector_store = FAISS.from_texts(texts, self.embeddings)
        serialized_vector_store = pickle.dumps(vector_store)

        with self.db_session_maker() as db_session:
            db_entry = db_session.query(ChatSession).filter_by(id=session_id).first()
            if not db_entry:
                db_entry = ChatSession(id=session_id)
                db_session.add(db_entry)
            db_entry.faiss_index = serialized_vector_store
            db_session.commit()

        return raw_text