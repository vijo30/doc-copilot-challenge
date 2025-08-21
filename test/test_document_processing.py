import pytest
from unittest.mock import patch
import os


class MockUploadedFile:
    def __init__(self, name="test_document.pdf", content=b"This is a test document content."):
        self.name = name
        self.content = content
    def getbuffer(self):
        return self.content

def test_process_pdfs_loads_and_splits_documents():
    """
    Test that the process_pdfs function correctly loads and splits documents.
    """
    from frontend.app import process_pdfs

    with patch('frontend.app.PyPDFLoader') as mock_pdf_loader, \
         patch('frontend.app.RecursiveCharacterTextSplitter') as mock_text_splitter, \
         patch('builtins.open'):
        
        mock_pdf_loader.return_value.load.return_value = ["mocked document content"]
        mock_text_splitter.return_value.split_documents.return_value = ["chunk1", "chunk2"]
    
        uploaded_files = [MockUploadedFile()]
    
        chunks = process_pdfs(uploaded_files)
    
        assert len(chunks) == 2
        assert chunks[0] == "chunk1"
        assert chunks[1] == "chunk2"
        mock_pdf_loader.assert_called_once()
        mock_text_splitter.assert_called_once()