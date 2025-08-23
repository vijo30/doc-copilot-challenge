# Doc Copilot Challenge

This project is a conversational AI copilot that allows users to upload up to 5 PDF files and ask questions about their content. The system leverages a structured orchestration of a Retrieval-Augmented Generation (RAG) pipeline to provide contextual and accurate answers.

---

## Architecture

The system is built on a **Retrieval-Augmented Generation (RAG)** architecture, designed to provide accurate answers by referencing user-provided documents.

- **Frontend (Streamlit):** A user-friendly interface for uploading documents and interacting with the conversational copilot.
- **Backend (FastAPI):** An API to handle conversational logic and interact with the database.
- **Worker (Celery):** An asynchronous worker that handles the intensive task of document processing.
- **Database (PostgreSQL):** A persistent database that stores chat history and a record of uploaded files for each session.
- **Message Broker (Redis):** Manages the communication queue between the backend and the Celery worker.
- **Vector Store (ChromaDB):** Stores the vector embeddings of document chunks for efficient semantic search.
- **LLM:** Generates conversational responses based on the retrieved context.

The entire application is containerized with Docker, ensuring a reproducible and portable environment.

---

## How to Run the Project

This project uses `docker` and `docker-compose` to manage all its services.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/vijo30/doc-copilot-challenge.git
    cd doc-copilot-challenge
    ```

2.  Build and run the Docker containers:
    ```bash
    docker-compose up --build
    ```

3.  Access the application:
    Open your web browser and navigate to `http://localhost:8501`.

---

## Technical Choices and Justification

- **Orchestration Framework:** **LangChain** was chosen for its comprehensive set of tools for building RAG applications, including document loaders, text splitters, and ready-made chains.
- **LLM:** We use an OpenAI LLM (e.g., GPT-3.5-turbo) for its superior performance and ease of integration via API.
- **Vector Store:** **ChromaDB** was selected for its simplicity and ease of use in a containerized environment, making it perfect for rapid prototyping.
- **Database:** **PostgreSQL** was chosen for its robustness and reliability in handling persistent data like chat sessions and file metadata.
- **Asynchronous Tasks:** **Celery** with **Redis** as a message broker was implemented to offload the time-consuming PDF processing tasks from the main API thread, preventing the user interface from freezing.
- **Frontend:** **Streamlit** was used to build the user interface quickly and efficiently, allowing us to focus more on the core AI logic.
- **Containerization:** **Docker** and **docker-compose** ensure that the application is easy to set up and run, guaranteeing a consistent environment for anyone who wants to test it.

---

## Conversational Flow Explained

The conversational flow follows a structured RAG pipeline:

1.  **Document Upload:** The user uploads PDF files via the Streamlit interface.
2.  **Processing:** The system loads the PDFs, splits the content into manageable chunks, and creates vector embeddings for each chunk.
3.  **Indexing:** The generated embeddings are stored in ChromaDB, creating an index for fast retrieval.
4.  **User Query:** The user enters a question in the chat interface.
5.  **Retrieval:** The system converts the user's question into a vector and uses it to perform a similarity search in the ChromaDB index. It retrieves the most relevant document chunks.
6.  **Generation:** The retrieved chunks are passed to the LLM as context, along with the user's original question. The LLM generates a coherent and contextual response.
7.  **Response:** The final answer is displayed to the user in the chat.

---

## Limitations & Future Roadmap

### Current Limitations
- **Single-format Support:** The system currently only handles PDF files.
- **Advanced Features:** The optional features (summarization, comparison, classification) have not yet been implemented.
- **Basic UI:** The user interface is functional but lacks advanced features and a polished design.
- **Cost:** Reliance on a paid LLM API (OpenAI) can be a cost factor for extensive usage.

### Future Roadmap
- **Multi-format Support:** Add compatibility for `.docx`, `.txt`, and other document types.
- **Advanced Features:** Implement optional functionalities like automatic document summarization and cross-document comparison.
- **Scalability:** Migrate to a managed vector store solution (e.g., Pinecone, Weaviate) and deploy the application on a cloud platform (e.g., AWS, GCP) to handle larger loads.
- **UI/UX Improvement:** Enhance the user interface with better design, loading indicators, and error handling.
- **Open-source LLM:** Explore using an open-source LLM (e.g., Llama 3) to reduce costs and increase flexibility.