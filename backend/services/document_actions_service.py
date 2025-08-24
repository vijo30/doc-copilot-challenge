# backend/services/document_actions_service.py

import logging
from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma
from backend.components.document_actions import get_summarize_chain, get_comparison_chain, get_classification_chain
from backend.services.database_service import DatabaseService, get_database_service
from fastapi import Depends, HTTPException
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class DocumentActionsService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def _retrieve_content(self, vector_store: Chroma, filenames: Optional[List[str]]) -> List[Document]:
        """
        Retrieves document content from the vector store based on filenames.
        If no filenames are provided, it retrieves all documents.
        """
        if not filenames:
            retriever = vector_store.as_retriever(search_kwargs={"k": 100})
            docs = retriever.invoke("all") 
        else:
            docs = []
            for filename in filenames:
                try:
                    retriever = vector_store.as_retriever(search_kwargs={"filter": {"filename": filename}})
                    file_docs = retriever.get_relevant_documents("")
                    docs.extend(file_docs)
                except Exception as e:
                    logger.warning(f"Could not retrieve documents for filename {filename}: {e}")
        
        if not docs:
            raise ValueError("No documents found for the given criteria.")
        
        return docs

    def summarize_documents(self, vector_store: Chroma, filenames: Optional[List[str]], language: str) -> str:
        """Generates a summary for the specified documents."""
        try:
            docs = self._retrieve_content(vector_store, filenames)
            combined_content = "\n\n".join([doc.page_content for doc in docs])
            summary_chain = get_summarize_chain(language=language)
            return summary_chain.invoke({"text": combined_content})
        except ValueError as e:
            logger.error(f"Error summarizing documents: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def compare_documents(self, vector_store: Chroma, filenames: List[str], language: str) -> str:
        """Compares multiple documents."""
        if len(filenames) < 2:
            raise HTTPException(status_code=400, detail="Comparison requires at least two files.")

        content_summary = ""
        for filename in filenames:
            try:
                docs = self._retrieve_content(vector_store, [filename])
                combined_content = "\n\n".join([doc.page_content for doc in docs])
                content_summary += f"\n\n--- Content of {filename} ---\n{combined_content}"
            except ValueError:
                raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        comparison_chain = get_comparison_chain(language=language)
        return comparison_chain.invoke({"filenames": ", ".join(filenames), "content_summary": content_summary})

    def classify_topics(self, vector_store: Chroma, language: str) -> str:
        """Classifies the main topics of all documents in the session."""
        try:
            docs = self._retrieve_content(vector_store, filenames=None)
            combined_content = "\n\n".join([doc.page_content for doc in docs])
            classification_chain = get_classification_chain(language=language)
            return classification_chain.invoke({"text": combined_content})
        except ValueError as e:
            logger.error(f"Error classifying topics: {e}")
            raise HTTPException(status_code=400, detail=str(e))

# --- Dependency Injection for FastAPI ---
def get_document_actions_service(
    db_service: DatabaseService = Depends(get_database_service),
) -> DocumentActionsService:
    return DocumentActionsService(db_service=db_service)