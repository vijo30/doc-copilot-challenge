import pytest
from unittest.mock import patch, mock_open, MagicMock

@patch('frontend.components.document_processor.PyPDFLoader')
@patch('frontend.components.document_processor.RecursiveCharacterTextSplitter')
def test_process_pdfs_loads_and_splits_documents(mock_text_splitter, mock_pdf_loader):
    """
    Tests that the process_pdfs function correctly loads and splits documents.
    """
    from frontend.components.document_processor import process_pdfs

    mock_pdf_loader.return_value.load.return_value = ["mocked document content"]
    mock_text_splitter.return_value.split_documents.return_value = ["chunk1", "chunk2"]

    mock_uploaded_file = MagicMock()
    mock_uploaded_file.name = "test.pdf"
    mock_uploaded_file.getbuffer.return_value = b"file content"
    
    with patch("builtins.open", mock_open()):
        chunks = process_pdfs([mock_uploaded_file])

    assert len(chunks) == 2
    assert chunks[0] == "chunk1"
    assert chunks[1] == "chunk2"
    mock_pdf_loader.assert_called_once()
    mock_text_splitter.assert_called_once()


@patch('frontend.components.document_processor.Chroma')
@patch('frontend.components.document_processor.HuggingFaceEmbeddings')
def test_vectorize_and_store_documents(mock_embeddings, mock_chroma):
    """
    Tests that the vectorize_and_store function correctly processes and stores document chunks.
    """
    from frontend.components.document_processor import vectorize_and_store
    
    mock_embeddings_instance = MagicMock()
    mock_embeddings.return_value = mock_embeddings_instance
    mock_chroma.from_documents.return_value = MagicMock()
    
    chunks = [MagicMock()]
    
    vectorize_and_store(chunks)
    
    mock_embeddings.assert_called_once()
    mock_chroma.from_documents.assert_called_once()