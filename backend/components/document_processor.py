import io
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from typing import List
from langchain_core.documents import Document

def get_pdf_text(pdf_files: list) -> str:
    """
    Extracts text from a list of PDF file objects.
    """
    text = ""
    for pdf_file in pdf_files:
        pdf_reader = PdfReader(io.BytesIO(pdf_file["content"]))
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

def create_text_chunks(text: str) -> List[str]:
    """
    Splits a long string of text into smaller string chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_text(text)
    return chunks

def vectorize_and_store(
    chunks: List[Document], 
    embeddings, 
    chroma_client, 
    collection_name: str
) -> Chroma:
    """
    Vectorizes document chunks and stores them in a specific ChromaDB collection.
    """
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=chroma_client,
        collection_name=collection_name
    )
    return vector_store