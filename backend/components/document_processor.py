import io
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from typing import List

def get_pdf_text(pdf_files):
    """
    Extracts text from a list of PDF file objects.
    """
    text = ""
    for pdf_file in pdf_files:
        pdf_reader = PdfReader(io.BytesIO(pdf_file.file.read()))
        for page in pdf_reader.pages:
            text += page.extract_text()
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

def vectorize_and_store(chunks, embeddings):
    """
    Vectorizes document chunks and stores them in a ChromaDB collection.
    """
    vector_store = Chroma.from_documents(chunks, embeddings)
    return vector_store