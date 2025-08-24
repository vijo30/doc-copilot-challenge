# backend/components/chat_logic.py

from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# Language-specific prompts for QA
ANSWER_PROMPTS = {
    "en": ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. Answer the user's questions based on the provided context."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Context: {context}\n\nQuestion: {question}"),
        ]
    ),
    "es": ChatPromptTemplate.from_messages(
        [
            ("system", "Eres un asistente útil. Responde a las preguntas del usuario basándote en el contexto proporcionado."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Contexto: {context}\n\nPregunta: {question}"),
        ]
    )
}

STANDALONE_QUESTION_PROMPTS = {
    "en": ChatPromptTemplate.from_messages(
        [
            ("system", "Given the following conversation and a follow-up question, rephrase the follow-up question to be a standalone question."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Follow-Up Question: {question}"),
            ("human", "Standalone Question:")
        ]
    ),
    "es": ChatPromptTemplate.from_messages(
        [
            ("system", "Dada la siguiente conversación y una pregunta de seguimiento, reformula la pregunta de seguimiento para que sea una pregunta independiente."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Pregunta de seguimiento: {question}"),
            ("human", "Pregunta independiente:")
        ]
    )
}

def create_qa_chain(vector_store, language="en"):
    """
    Creates a full conversational QA chain using LCEL.
    """
    llm = ChatOpenAI(temperature=0)
    retriever = vector_store.as_retriever()

    answer_prompt = ANSWER_PROMPTS.get(language, ANSWER_PROMPTS["en"])
    standalone_question_prompt = STANDALONE_QUESTION_PROMPTS.get(language, STANDALONE_QUESTION_PROMPTS["en"])

    standalone_question_chain = (
        standalone_question_prompt
        | llm
        | StrOutputParser()
    )
    
    qa_chain = (
        RunnablePassthrough.assign(
            standalone_question=standalone_question_chain,
            chat_history=lambda x: x["chat_history"],
            question=lambda x: x["question"]
        )
        | RunnablePassthrough.assign(
            context=lambda x: retriever.invoke(x["standalone_question"]),
        )
        | RunnablePassthrough.assign(
            context=lambda x: "\n\n".join([doc.page_content for doc in x["context"]]),
        )
        | RunnableLambda(
            lambda x: {
                "context": x["context"],
                "question": x["question"],
                "chat_history": x["chat_history"]
            }
        )
        | answer_prompt
        | llm
        | StrOutputParser()
        | RunnableLambda(lambda x: {"answer": x})
    )
    
    return qa_chain