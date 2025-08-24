import uuid
from sqlalchemy import Column, String, DateTime, Text, func, TypeDecorator, Integer
from sqlalchemy.dialects.postgresql import UUID
import json
from backend.database import Base
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class JSONEncodedList(TypeDecorator):
    """Stores a list as a JSON-encoded string."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    uploaded_files = Column(JSONEncodedList, default=[])
    created_at = Column(DateTime, default=func.now())

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    session_id = Column(String)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
class QuestionRequest(BaseModel):
    session_id: str
    question: str
    language: str

class SummarizeRequest(BaseModel):
    session_id: str
    filenames: Optional[List[str]] = None
    language: str

class CompareRequest(BaseModel):
    session_id: str
    filenames: List[str]
    language: str

class ClassifyRequest(BaseModel):
    session_id: str
    language: str

class DeleteChatroomRequest(BaseModel):
    session_id: str