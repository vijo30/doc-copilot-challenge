from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

def get_answer_prompt():
    """Returns the prompt template for generating the final answer."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. Answer the user's questions based on the provided context."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Context: {context}\n\nQuestion: {question}"),
        ]
    )

def get_standalone_question_prompt():
    """Returns the prompt for rephrasing a follow-up question."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", "Given the following conversation and a follow-up question, rephrase the follow-up question to be a standalone question."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Follow-Up Question: {question}"),
            ("human", "Standalone Question:")
        ]
    )

def create_qa_chain(vector_store):
    """
    Creates a full conversational QA chain using LCEL.
    """
    llm = ChatOpenAI(temperature=0)
    retriever = vector_store.as_retriever()

    standalone_question_chain = (
        get_standalone_question_prompt()
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
        | RunnableLambda(
            lambda x: {
                "context": "\n\n".join([doc.page_content for doc in x["context"]]),
                "question": x["question"],
                "chat_history": x["chat_history"]
            }
        )
        | get_answer_prompt()
        | llm
        | RunnableLambda(lambda x: {"answer": x.content})
    )
    
    return qa_chain