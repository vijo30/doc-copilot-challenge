# backend/components/document_actions.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

SUMMARIZE_PROMPTS = {
    "en": ChatPromptTemplate.from_template("Provide a concise and objective summary of the following text:\n\n{text}"),
    "es": ChatPromptTemplate.from_template("Proporciona un resumen conciso y objetivo del siguiente texto:\n\n{text}")
}

COMPARE_PROMPTS = {
    "en": ChatPromptTemplate.from_template("""
    You are an expert assistant in document comparison. Compare the following files: {filenames}.
    Identify the similarities, differences, and unique points of each. Respond in a structured format.

    File Content:
    {content_summary}
    """),
    "es": ChatPromptTemplate.from_template("""
    Eres un asistente experto en comparación de documentos. Compara los siguientes archivos: {filenames}.
    Identifica las similitudes, diferencias y puntos únicos de cada uno. Responde en un formato estructurado.

    Contenido de los archivos:
    {content_summary}
    """)
}

CLASSIFICATION_PROMPTS = {
    "en": ChatPromptTemplate.from_template("Analyze the following text and identify the 3 main topics. Respond with a list of the topics.\n\n{text}"),
    "es": ChatPromptTemplate.from_template("Analiza el siguiente texto e identifica los 3 temas principales. Responde con una lista de los temas.\n\n{text}")
}

def get_summarize_chain(language="en"):
    """Returns the LangChain chain for document summarization."""
    summary_prompt = SUMMARIZE_PROMPTS.get(language, SUMMARIZE_PROMPTS["en"])
    llm = ChatOpenAI(temperature=0)
    return summary_prompt | llm | StrOutputParser()

def get_comparison_chain(language="en"):
    """Returns the LangChain chain for document comparison."""
    comparison_prompt = COMPARE_PROMPTS.get(language, COMPARE_PROMPTS["en"])
    llm = ChatOpenAI(temperature=0)
    return comparison_prompt | llm | StrOutputParser()

def get_classification_chain(language="en"):
    """Returns the LangChain chain for topic classification."""
    classification_prompt = CLASSIFICATION_PROMPTS.get(language, CLASSIFICATION_PROMPTS["en"])
    llm = ChatOpenAI(temperature=0)
    return classification_prompt | llm | StrOutputParser()