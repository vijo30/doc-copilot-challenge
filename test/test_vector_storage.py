import pytest
from unittest.mock import MagicMock, patch

@patch('frontend.app.HuggingFaceEmbeddings')
@patch('frontend.app.Chroma')
def test_vectorize_and_store_documents(mock_chroma, mock_huggingface_embeddings):
    """
    Test that the vectorize_and_store function correctly processes and stores document chunks.
    """
    from frontend.app import vectorize_and_store
    from langchain.docstore.document import Document
    
    mock_embeddings_instance = MagicMock()
    mock_huggingface_embeddings.return_value = mock_embeddings_instance
    
    mock_chroma.from_documents.return_value = MagicMock()
  
    chunks = [
        Document(page_content="Test chunk 1", metadata={"source": "doc1.pdf"}),
        Document(page_content="Test chunk 2", metadata={"source": "doc2.pdf"})
    ]

    vectorize_and_store(chunks)

    mock_chroma.from_documents.assert_called_once() 
    mock_huggingface_embeddings.assert_called_once()