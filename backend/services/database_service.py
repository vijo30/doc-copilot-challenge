from typing import List, Dict, Any, Generator
from backend.models.schemas import ChatSession, ChatMessage
from typing import Optional
from sqlalchemy.orm import sessionmaker, Session as DBSession
from fastapi import Depends

class DatabaseService:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        
    def create_session(self, session_id: str, filenames: List[str]):
        """Creates a new chat session in the database."""
        db = self.session_factory()
        try:
            db_session = ChatSession(id=session_id, name=", ".join(filenames), uploaded_files=filenames)
            db.add(db_session)
            db.commit()
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieves a ChatSession object from the database by its ID."""
        db = self.session_factory()
        try:
            chat_session = db.query(ChatSession).filter_by(id=session_id).first()
            return chat_session
        finally:
            db.close()
    
    def update_uploaded_files(self, session_id: str, filenames: List[str]):
        """Updates the list of uploaded files for an existing session."""
        db = self.session_factory()
        try:
            chat_session = db.query(ChatSession).filter_by(id=session_id).first()
            if chat_session:
                chat_session.uploaded_files = filenames
                db.commit()
        finally:
            db.close()

    def add_message(self, session_id: str, role: str, content: str):
        db = self.session_factory()
        try:
            db_message = ChatMessage(session_id=session_id, role=role, content=content)
            db.add(db_message)
            db.commit()
        finally:
            db.close()

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        db = self.session_factory()
        try:
            messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
            return [{"role": m.role, "content": m.content} for m in messages]
        finally:
            db.close()

    def get_all_chatrooms(self) -> List[Dict[str, Any]]:
        db = self.session_factory()
        try:
            sessions = db.query(ChatSession).all()
            return [{"session_id": s.id, "name": s.name} for s in sessions]
        finally:
            db.close()

    def delete_session(self, session_id: str):
        db = self.session_factory()
        try:
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
            db.query(ChatSession).filter(ChatSession.id == session_id).delete()
            db.commit()
        finally:
            db.close()

# --- Dependency Injection for FastAPI ---
def get_database_service() -> Generator[DatabaseService, None, None]:
    """
    Dependency that provides a DatabaseService instance.
    The session factory is imported here and yielded.
    """
    from backend.database import SessionLocal
    db_session = SessionLocal()
    try:
        yield DatabaseService(SessionLocal)
    finally:
        db_session.close()