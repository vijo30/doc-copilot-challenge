from asyncio.log import logger
import os
from celery import Celery
from backend.services.document_service import DocumentService
from backend.services.database_service import DatabaseService
from backend.services.redis_cache_service import RedisCacheService
from backend.chroma_client_singleton import ChromaClientSingleton
from backend.utils.model_loader import get_embeddings_model
from backend.database import SessionLocal
from backend.utils.env_loader import load_env
import logging

load_env()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)

@celery_app.task(bind=True)
def process_documents_task(self, session_id: str, file_data: list):
    try:
        db_service = DatabaseService(session_factory=SessionLocal)
        cache_service = RedisCacheService(os.getenv("REDIS_HOST", "redis"), 6379, 0)
        
        doc_service = DocumentService(
            db_service=db_service,
            cache_service=cache_service,
            chroma_client=ChromaClientSingleton(),
            embeddings=get_embeddings_model()
        )
        
        doc_service.process_documents(session_id, file_data)
        
        return {"status": "complete", "session_id": session_id}

    except Exception as e:
        self.update_state(state="FAILURE", meta={"exc_type": type(e).__name__, "exc_message": str(e)})
        logger.error(f"Celery task failed for session {session_id}: {e}")
        raise