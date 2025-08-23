import os
import redis
import pickle
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
from backend.utils.model_loader import get_embeddings_model
from dotenv import load_dotenv
from backend.tasks import process_documents_task

from backend.services.document_service import DocumentService
from backend.services.chat_service import ChatService
from backend.services.database_service import DatabaseService
from backend.models.schemas import Base, ChatSession, ChatMessage
from backend.components.chat_logic import create_qa_chain
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class QuestionRequest(BaseModel):
    question: str
    session_id: str

class ChatHistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]

class DeleteChatroomRequest(BaseModel):
    session_id: str

class ChatroomListResponse(BaseModel):
    chatrooms: List[Dict[str, Any]]

embeddings = get_embeddings_model()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=os.getenv("REDIS_PORT", "6379"),
    db=0,
)


database_service = DatabaseService(SessionLocal)
chat_service = ChatService(database_service)


@app.post("/process-pdfs/")
async def process_pdfs_endpoint(session_id: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        file_data = [{"filename": file.filename, "content": file.file.read()} for file in files]
        
        task = process_documents_task.delay(session_id, file_data)
        return {"message": "Processing started.", "task_id": task.id}
    except Exception as e:
        logging.error("Error starting PDF processing task:", exc_info=True)
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

@app.post("/ask-question/", response_model=ChatHistoryResponse)
async def ask_question_endpoint(request: QuestionRequest):
    try:
        with SessionLocal() as db_session:
            chat_session_entry = db_session.query(ChatSession).filter_by(id=request.session_id).first()

            if not chat_session_entry or not chat_session_entry.faiss_index:
                raise HTTPException(status_code=404, detail="Session not found or has expired.")

        vector_store = pickle.loads(chat_session_entry.faiss_index)
        vector_store.embedding_function = embeddings

        db_history = database_service.get_chat_history(request.session_id)
        
        chat_history = [
            HumanMessage(content=msg['content']) if msg['role'] == "user" else AIMessage(content=msg['content'])
            for msg in db_history
        ]
        
        qa_chain = create_qa_chain(vector_store)
        result = qa_chain.invoke({"question": request.question, "chat_history": chat_history})
        answer = result["answer"]

        database_service.add_message(request.session_id, "user", request.question)
        database_service.add_message(request.session_id, "assistant", answer)

        updated_chat_history = database_service.get_chat_history(request.session_id)
        
        return {"messages": updated_chat_history}
    except Exception as e:
        logger.error("Error asking question:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error asking question.")
    
@app.get("/get-chat-history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history_endpoint(session_id: str):
    try:
        chat_history = database_service.get_chat_history(session_id)
        return {"messages": chat_history}
    except Exception as e:
        logger.error("Error getting chat history:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting chat history.")

@app.get("/get-all-chatrooms/", response_model=ChatroomListResponse)
async def get_all_chatrooms_endpoint():
    try:
        chatrooms = database_service.get_all_chatrooms()
        return {"chatrooms": chatrooms}
    except Exception as e:
        logger.error("Error getting all chatrooms:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting all chatrooms.")

@app.post("/delete-chatroom/")
async def delete_chatroom_endpoint(request: DeleteChatroomRequest):
    try:
        database_service.delete_session(request.session_id)
        redis_client.delete(f"{request.session_id}_text")
        redis_client.delete(f"{request.session_id}_vector_store")
        
        return {"message": f"Chatroom {request.session_id} successfully deleted."}
    except Exception as e:
        logger.error("Error deleting chatroom:", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting chatroom.")
      
@app.get("/chat-history/{session_id}")
def get_chat_history_endpoint(session_id: str):
    messages = database_service.get_chat_history(session_id)
    return {"messages": messages}