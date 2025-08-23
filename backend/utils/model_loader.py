# backend/utils/model_loader.py

from langchain_huggingface.embeddings import HuggingFaceEmbeddings

class EmbeddingsSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                encode_kwargs={'normalize_embeddings': False}
            )
        return cls._instance

def get_embeddings_model():
    return EmbeddingsSingleton()