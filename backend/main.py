from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
import logging
from langchain_community.vectorstores import Chroma

from backend.tasks import process_documents_task
from backend.services.database_service import DatabaseService, get_database_service
from backend.services.redis_cache_service import RedisCacheService, get_redis_cache_service
from backend.services.document_service import DocumentService, get_document_service
from backend.services.chat_service import ChatService, get_chat_service
from backend.services.document_actions_service import DocumentActionsService, get_document_actions_service
from backend.models.schemas import QuestionRequest, DeleteChatroomRequest, SummarizeRequest, CompareRequest, ClassifyRequest

from backend.database import Base, engine
from backend.utils.env_loader import load_env

MAX_FILES_PER_CHAT = 5

load_env()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    try:
        logging.info("Attempting to create database tables...")
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully!")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}", exc_info=True)

# --- API Endpoints ---

@app.post("/process-pdfs/")
async def process_pdfs_endpoint(
    files: list[UploadFile] = File(...),
    session_id: str = Form(...),
    cache_service: RedisCacheService = Depends(get_redis_cache_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    if len(files) > MAX_FILES_PER_CHAT:
        raise HTTPException(
            status_code=400,
            detail=f"You can only upload {MAX_FILES_PER_CHAT}."
        )
    try:
        cache_service.delete_keys(f"vector_store_ready:{session_id}")
        file_data = [{"filename": file.filename, "content": file.file.read()} for file in files] 
        session_exists = db_service.get_session(session_id)
        if not session_exists:
            db_service.create_session(session_id, [file['filename'] for file in file_data])
        else:
            db_service.update_uploaded_files(session_id, [file['filename'] for file in file_data])

        task = process_documents_task.delay(session_id, file_data)
        return {"message": "Processing started.", "task_id": task.id}
    except Exception as e:
        logger.error("Error starting PDF processing task:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error starting PDF processing.")
      
@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    task = process_documents_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'status': task.info.get('status', 'Processing...'), 'result': task.info.get('result')}
        if 'complete' in response['status']:
            response['result'] = task.info
    else:
        response = {'state': task.state, 'status': str(task.info)}
    return response

@app.post("/ask-question/")
async def ask_question_endpoint(
    request: QuestionRequest, 
    db_service: DatabaseService = Depends(get_database_service),
    chat_service: ChatService = Depends(get_chat_service),
    doc_service: DocumentService = Depends(get_document_service)
):
    try:
        vector_store = doc_service.get_vector_store(request.session_id)
        if not vector_store:
            raise HTTPException(status_code=404, detail="Vector store not found. Documents must be processed first.")
        
        answer = chat_service.get_answer(vector_store, request.question, request.session_id, request.language)
        db_service.add_message(request.session_id, "user", request.question)
        db_service.add_message(request.session_id, "assistant", answer)
        updated_chat_history = db_service.get_chat_history(request.session_id)
        return {"messages": updated_chat_history}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error asking question:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error asking question.")
        

@app.post("/summarize/")
async def summarize_endpoint(
    request: SummarizeRequest,
    actions_service: DocumentActionsService = Depends(get_document_actions_service),
    doc_service: DocumentService = Depends(get_document_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    try:
        vector_store = doc_service.get_vector_store(request.session_id)
        if not vector_store:
            raise HTTPException(status_code=404, detail="Vector store not found. Documents must be processed first.")
            
        summary = actions_service.summarize_documents(vector_store, request.filenames, request.language)
        
        db_service.add_message(request.session_id, "assistant", summary)
        
        return {"summary": summary}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error summarizing content: {e}")
        raise HTTPException(status_code=500, detail="Error generating summary.")

@app.post("/compare/")
async def compare_endpoint(
    request: CompareRequest,
    actions_service: DocumentActionsService = Depends(get_document_actions_service),
    doc_service: DocumentService = Depends(get_document_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    try:
        vector_store = doc_service.get_vector_store(request.session_id)
        if not vector_store:
            raise HTTPException(status_code=404, detail="Vector store not found. Documents must be processed first.")
            
        comparison = actions_service.compare_documents(vector_store, request.filenames, request.language)
        
        db_service.add_message(request.session_id, "assistant", comparison)
        
        return {"comparison": comparison}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error comparing documents: {e}")
        raise HTTPException(status_code=500, detail="Error generating comparison.")

@app.post("/classify/")
async def classify_topics_endpoint(
    request: ClassifyRequest,
    actions_service: DocumentActionsService = Depends(get_document_actions_service),
    doc_service: DocumentService = Depends(get_document_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    try:
        vector_store = doc_service.get_vector_store(request.session_id)
        if not vector_store:
            raise HTTPException(status_code=404, detail="Vector store not found. Documents must be processed first.")
            
        topics = actions_service.classify_topics(vector_store, request.language)
        
        db_service.add_message(request.session_id, "assistant", topics)
        
        return {"topics": topics}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error classifying topics: {e}")
        raise HTTPException(status_code=500, detail="Error classifying topics.")
      
@app.get("/chat-history/{session_id}")
async def get_chat_history_endpoint(session_id: str, db_service: DatabaseService = Depends(get_database_service)):
    try:
        chat_history = db_service.get_chat_history(session_id)
        return {"messages": chat_history}
    except Exception as e:
        logger.error("Error getting chat history:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting chat history.")

@app.get("/get-all-chatrooms/")
async def get_all_chatrooms_endpoint(db_service: DatabaseService = Depends(get_database_service)):
    try:
        chatrooms = db_service.get_all_chatrooms()
        return {"chatrooms": chatrooms}
    except Exception as e:
        logger.error("Error getting all chatrooms:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting all chatrooms.")

@app.post("/delete-chatroom/")
async def delete_chatroom_endpoint(
    request: DeleteChatroomRequest, 
    db_service: DatabaseService = Depends(get_database_service),
    doc_service: DocumentService = Depends(get_document_service),
    cache_service: RedisCacheService = Depends(get_redis_cache_service)
):
    try:
        doc_service.delete_vector_store(request.session_id)
        db_service.delete_session(request.session_id)
        cache_service.delete_keys(f"vector_store_ready:{request.session_id}")
        return {"message": f"Chatroom {request.session_id} successfully deleted."}
    except Exception as e:
        logger.error("Error deleting chatroom:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting chatroom.")

@app.get("/chat-files/{session_id}")
def get_chat_files(session_id: str, db_service: DatabaseService = Depends(get_database_service)):
    chat_session = db_service.get_session(session_id)
    if not chat_session:
        return {"files": []}
    return {"files": chat_session.uploaded_files}