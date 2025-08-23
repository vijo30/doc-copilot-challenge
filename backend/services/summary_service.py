from components.chat_summarizer import summarize_conversation

class SummaryService:
    """Service to summarize chat conversations."""
    
    def summarize(self, chat_history: list):
        """
        Summarizes the chat history using the core summarization component.
        """
        return summarize_conversation(chat_history)