from backend.components.chat_logic import create_qa_chain
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from backend.services.database_service import DatabaseService, get_database_service
from langchain_community.vectorstores import Chroma
from fastapi import Depends

class ChatService:
    """Service to handle core conversational logic."""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    def get_answer(self, vector_store: Chroma, question: str, session_id: str, language: str):
        """
        Invokes the QA chain to get an answer to a question.
        The vector_store is now a direct parameter.
        """
        qa_chain = create_qa_chain(vector_store, language=language)

        db_history = self.db_service.get_chat_history(session_id)
        formatted_history = self._format_chat_history(db_history)
        
        response = qa_chain.invoke({'question': question, 'chat_history': formatted_history})
        return response['answer']

    def _format_chat_history(self, history: list):
        """Formats the chat history for the QA chain."""
        formatted = []
        for msg in history:
            if msg['role'] == 'user':
                formatted.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                formatted.append(AIMessage(content=msg['content']))
            elif msg['role'] == 'system':
                formatted.append(SystemMessage(content=msg['content']))
        return formatted

# --- Dependency Injection for the Service ---
def get_chat_service(
    db_service: DatabaseService = Depends(get_database_service),
) -> ChatService:
    """
    Dependency that provides a ChatService instance.
    It no longer needs DocumentService to be a dependency itself.
    """
    return ChatService(db_service)