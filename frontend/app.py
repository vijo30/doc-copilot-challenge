import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OllamaEmbeddings

def process_pdfs(uploaded_files):
    """
    Processes uploaded PDF files by loading, splitting, and embedding their content.

    Args:
        uploaded_files: A list of uploaded Streamlit file objects.

    Returns:
        The processed document chunks.
    """
    all_chunks = []
    
    for uploaded_file in uploaded_files:
        temp_file_path = f"./data/{uploaded_file.name}"
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        loader = PyPDFLoader(temp_file_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        all_chunks.extend(chunks)

    return all_chunks

def main():
    """
    Main function to run the Streamlit app.
    """
    st.set_page_config(
        page_title="Doc Copilot",
        page_icon="📄",
        layout="centered"
    )

    st.title("📄 Doc Copilot")
    st.markdown("Upload up to 5 PDF files and ask questions about their content.")

    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type="pdf",
        accept_multiple_files=True
    )

    if uploaded_files:
        if len(uploaded_files) > 5:
            st.warning("You can only upload up to 5 files. Please remove some.")
        else:
            with st.spinner("Processing files..."):
                processed_chunks = process_pdfs(uploaded_files)
                st.success(f"Processing complete! Found {len(processed_chunks)} chunks.")
            
            
if __name__ == "__main__":
  main()