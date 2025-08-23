from langchain_community.vectorstores import Chroma
from backend.components.chat_logic import create_qa_chain
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from backend.services.database_service import DatabaseService
from typing import List, Dict, Any

class ChatService:
    """Service to handle core conversational logic."""
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service

    def get_answer(self, vector_store, question: str, chat_history: List[Dict[str, Any]]):
        """
        Invokes the QA chain to get an answer to a question.
        """
        if not vector_store:
            raise ValueError("Vector store not set. Documents must be processed first.")

        qa_chain = create_qa_chain(vector_store)

        formatted_history = self._format_chat_history(chat_history)

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