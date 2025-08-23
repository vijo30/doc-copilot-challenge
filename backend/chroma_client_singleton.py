import os
from chromadb import HttpClient

class ChromaClientSingleton:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ChromaClientSingleton, cls).__new__(cls)
            host = os.getenv("CHROMA_HOST", "chromadb")
            port = int(os.getenv("CHROMA_PORT", "8000"))
            cls._instance.client = HttpClient(host=host, port=port)
            print("ChromaDB client instance created.")
        return cls._instance