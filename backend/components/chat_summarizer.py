from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

def summarize_conversation(chat_history: list) -> str:
    """
    Summarizes the chat history to create a concise memory.
    """
    llm = ChatOpenAI(temperature=0.0)
    
    formatted_history = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_history
    )
    
    prompt_template = """
    Please create a concise summary of the following chat conversation to use as context for a retrieval agent.

    Chat History:
    {chat_history}

    Concise Summary:
    """
    
    summary_chain = PromptTemplate.from_template(prompt_template) | llm
    
    summary_response = summary_chain.invoke({"chat_history": formatted_history})
    return summary_response.content