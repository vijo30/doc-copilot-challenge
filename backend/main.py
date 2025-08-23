# backend/main.py

import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.tasks import process_documents_task
from backend.services.database_service import DatabaseService, get_database_service
from backend.components.chat_logic import create_qa_chain
from backend.utils.model_loader import get_embeddings_model

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
import redis
from backend.chroma_client_singleton import ChromaClientSingleton


from backend.database import Base, engine

MAX_FILES_PER_CHAT = 5

class QuestionRequest(BaseModel):
    question: str
    session_id: str

class ChatHistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]

class DeleteChatroomRequest(BaseModel):
    session_id: str

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embeddings = get_embeddings_model()
redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=os.getenv("REDIS_PORT", "6379"),
    db=0,
)

def get_vector_store(session_id: str):
    client_singleton = ChromaClientSingleton()
    
    return Chroma(
        client=client_singleton.client,
        embedding_function=embeddings,
        collection_name=session_id
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
):
    new_files_count = len(files)
    if new_files_count > MAX_FILES_PER_CHAT:
        raise HTTPException(
            status_code=400,
            detail=f"You can only upload {MAX_FILES_PER_CHAT}."
        )
    try:
        file_data = [{"filename": file.filename, "content": file.file.read()} for file in files]
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
    db_service: DatabaseService = Depends(get_database_service)
):
    try:
        vector_store = get_vector_store(request.session_id)
        
        db_history = db_service.get_chat_history(request.session_id)
        
        chat_history = [
            HumanMessage(content=msg['content']) if msg['role'] == "user" else AIMessage(content=msg['content'])
            for msg in db_history
        ]
        
        qa_chain = create_qa_chain(vector_store) 
        result = qa_chain.invoke({"question": request.question, "chat_history": chat_history})
        answer = result["answer"]

        db_service.add_message(request.session_id, "user", request.question)
        db_service.add_message(request.session_id, "assistant", answer)

        updated_chat_history = db_service.get_chat_history(request.session_id)
        return {"messages": updated_chat_history}
    except Exception as e:
        logger.error("Error asking question:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error asking question.")

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
    db_service: DatabaseService = Depends(get_database_service)
):
    try:
        client_singleton = ChromaClientSingleton()
        
        try:
            client_singleton.client.get_collection(name=request.session_id)
            client_singleton.client.delete_collection(name=request.session_id)
            logger.info(f"ChromaDB collection for session {request.session_id} deleted.")
        except Exception as e:
            logger.warning(f"ChromaDB collection for session {request.session_id} not found or could not be deleted: {e}")

        db_service.delete_session(request.session_id)
        
        redis_client.delete(f"{request.session_id}_text")
        redis_client.delete(f"{request.session_id}_vector_store")
        
        return {"message": f"Chatroom {request.session_id} successfully deleted."}
    except Exception as e:
        logger.error("Error deleting chatroom:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting chatroom.")

@app.get("/chat-files/{session_id}")
def get_chat_files(
    session_id: str, 
    db_service: DatabaseService = Depends(get_database_service)
):
    chat_session = db_service.get_session(session_id)
    if not chat_session:
        return {"files": []}
    
    return {"files": chat_session.uploaded_files}