import pytest
from unittest.mock import patch, MagicMock

@patch('frontend.components.chat_logic.ChatOpenAI')
@patch('frontend.components.chat_logic.RetrievalQA')
def test_create_qa_chain_initializes_correctly(mock_retrieval_qa, mock_chat_openai):
    """
    Tests that the create_qa_chain function initializes the RetrievalQA chain correctly.
    """
    from frontend.components.chat_logic import create_qa_chain
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_vector_store = MagicMock()
    mock_retriever = MagicMock()
    mock_vector_store.as_retriever.return_value = mock_retriever
    
    qa_chain = create_qa_chain(mock_vector_store)

    mock_chat_openai.assert_called_once_with(temperature=0)
    mock_vector_store.as_retriever.assert_called_once()
    mock_retrieval_qa.from_chain_type.assert_called_once_with(
        llm=mock_llm,
        chain_type="stuff",
        retriever=mock_retriever
    )
    assert qa_chain is not None