from asyncio.log import logger
import os

from dotenv import load_dotenv
from celery import Celery
from backend.services.document_service import DocumentService
from backend.utils.model_loader import get_embeddings_model
from backend.database import SessionLocal

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

celery_app = Celery('tasks', broker=f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0",
                    backend=f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0")

embeddings = get_embeddings_model()


document_service = DocumentService(embeddings, SessionLocal)

@celery_app.task(bind=True)
def process_documents_task(self, session_id: str, file_data: list):
    try:
        filenames = [file['filename'] for file in file_data]
        self.update_state(state="PROGRESS", meta={"status": "Processing documents...", "session_id": session_id})
        document_service.process_documents(file_data, session_id, filenames)
        
        return {"status": "complete", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error in task for session {session_id}: {e}")
        self.update_state(state="FAILURE", meta={"status": "error", "error": str(e)})
        raise