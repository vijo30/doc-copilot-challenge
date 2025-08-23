# frontend/app.py

import streamlit as st
import requests
import uuid
import time
import os

class AppSessionManager:
    """Manages the Streamlit app's state and core functionality."""

    def __init__(self):
        st.set_page_config(page_title="PDF Chat", page_icon="📄")
        self.backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initializes or restores the session state based on URL parameters."""
        query_params = st.query_params
        session_id_from_url = query_params.get("chatroom")

        if "session_id" not in st.session_state:
            if session_id_from_url:
                st.session_state.session_id = session_id_from_url
            else:
                st.session_state.session_id = str(uuid.uuid4())
            
            st.session_state.is_processed = False
            st.session_state.messages = []
            st.session_state.uploaded_filenames = []
            st.query_params["chatroom"] = st.session_state.session_id

            self.fetch_initial_data()
        
    def fetch_initial_data(self):
        """Fetches existing chat history and files from the backend on startup."""
        try:
            history_response = requests.get(f"{self.backend_url}/chat-history/{st.session_state.session_id}", timeout=300)
            history_response.raise_for_status()
            data = history_response.json()
            st.session_state.messages = data.get("messages", [])
            if st.session_state.messages:
                st.session_state.is_processed = True
            
            files_response = requests.get(f"{self.backend_url}/chat-files/{st.session_state.session_id}")
            files_response.raise_for_status()
            files_data = files_response.json()
            st.session_state.uploaded_filenames = files_data.get("files", [])
            
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch chat history or files: {e}")

    def create_new_chat(self):
        """Resets the session state to start a new chat."""
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.is_processed = False
        st.session_state.messages = []
        st.session_state.uploaded_filenames = []
        st.query_params["chatroom"] = st.session_state.session_id
        st.rerun()

    def delete_chat(self):
        """Deletes the current chatroom from the backend and resets the UI."""
        try:
            response = requests.post(f"{self.backend_url}/delete-chatroom/", json={
                "session_id": st.session_state.session_id
            })
            response.raise_for_status()
            st.success("Chat deleted successfully!")
            self.create_new_chat()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to delete chat: {e}")
            
class FileUploaderComponent:
    """Handles file uploading and background processing."""
    def __init__(self, backend_url):
        self.backend_url = backend_url
        self.display_uploader_and_button()

    def display_uploader_and_button(self):
        """Shows the file uploader and handles the processing logic."""
        uploaded_files = st.sidebar.file_uploader(
            "Upload PDFs",
            type="pdf",
            accept_multiple_files=True,
            help="You can upload multiple PDF files at once."
        )

        if uploaded_files and st.button("Process PDFs"):
            self.process_files(uploaded_files)
            
        if st.session_state.uploaded_filenames:
            st.sidebar.markdown("---")
            st.sidebar.subheader("Uploaded Files")
            for filename in st.session_state.uploaded_filenames:
                st.sidebar.write(f"• {filename}")

    def process_files(self, uploaded_files):
        """Sends files to the backend for processing and polls for task status."""
        files_data = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_files]
        st.session_state.uploaded_filenames = [file.name for file in uploaded_files]
        
        with st.spinner("Starting processing..."):
            try:
                response = requests.post(
                    f"{self.backend_url}/process-pdfs/",
                    files=files_data,
                    data={"session_id": st.session_state.session_id},
                    timeout=300,
                )
                response.raise_for_status()
                task_id = response.json().get("task_id")
                st.session_state.is_processed = False
                st.info("Processing PDFs in the background. This may take a few moments.")
                
                self.poll_task_status(task_id)

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to start PDF processing: {e}")
                st.error("Make sure the backend and worker are running.")
    
    def poll_task_status(self, task_id):
        """Polls the backend for the status of the processing task."""
        with st.spinner("Processing..."):
            while True:
                task_response = requests.get(f"{self.backend_url}/task-status/{task_id}")
                task_data = task_response.json()
                state = task_data.get("state")
                
                if state == "SUCCESS":
                    st.session_state.is_processed = True
                    st.success("PDFs processed successfully! You can now ask questions.")
                    st.rerun()
                elif state == "FAILURE":
                    st.error("An error occurred during processing.")
                    break
                
                time.sleep(2)



class ChatInterface:
    """Handles the display of chat messages and user input."""
    def __init__(self, backend_url):
        self.backend_url = backend_url
        self.display_messages()
        self.handle_input()

    def display_messages(self):
        """Displays all messages in the current session state."""
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    def handle_input(self):
        """Handles the chat input, sending questions to the backend."""
        disabled_input = not st.session_state.is_processed
        if prompt := st.chat_input("Ask a question about your PDFs", disabled=disabled_input):
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)


            with st.chat_message("assistant"):
                placeholder = st.empty()
                with st.spinner("AI is thinking..."):
                    try:
                        response = requests.post(
                            f"{self.backend_url}/ask-question/",
                            json={"question": prompt, "session_id": st.session_state.session_id},
                            timeout=300
                        )
                        response.raise_for_status()
                        
                        updated_messages = response.json().get("messages", [])
                        st.session_state.messages = updated_messages
                        
                        last_ai_message = updated_messages[-1]["content"]

                        placeholder.markdown(last_ai_message)

                    except requests.exceptions.RequestException as e:
                        st.error(f"Failed to get AI response: {e}")
                        
def main():
    """The main entry point for the Streamlit application."""
    app_manager = AppSessionManager()
    
    st.title("📄💬 Chat with PDF")
    
    with st.sidebar:
        st.subheader("Manage Chat")
        if st.button("New Chat"):
            app_manager.create_new_chat()
        
        FileUploaderComponent(app_manager.backend_url)
        
        if st.session_state.messages:
            if st.button("Delete Chat"):
                app_manager.delete_chat()

    if not st.session_state.messages:
        st.info("Welcome! Upload and process a PDF to start a conversation.")
    
    ChatInterface(app_manager.backend_url)

if __name__ == "__main__":
    main()