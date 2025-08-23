# backend/tasks.py

import os
from celery import Celery
from backend.services.document_service import DocumentService
from backend.utils.model_loader import get_embeddings_model
from backend.models.schemas import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Configure Celery
celery_app = Celery('tasks', broker=f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0",
                    backend=f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0")

# Set up database session for the worker
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


embeddings = get_embeddings_model()

# Initialize document service for the worker
document_service = DocumentService(embeddings, SessionLocal)

@celery_app.task
def process_documents_task(session_id: str, file_data: list):
    """
    Celery task to process documents in the background.
    """
    try:
        logging.info(f"Worker starting document processing for session: {session_id}")
        document_service.process_documents(file_data, session_id)
        logging.info(f"Worker finished document processing for session: {session_id}")
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        logging.error(f"Error in task for session {session_id}: {e}", exc_info=True)
        return {"status": "error", "session_id": session_id, "error": str(e)}