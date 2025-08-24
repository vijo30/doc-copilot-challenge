# frontend/app.py

import streamlit as st
import requests
import uuid
import time
import os
from typing import List, Dict, Any

from frontend.text_strings import STRINGS

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

        if "language" not in st.session_state:
            st.session_state.language = "en"
        
        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False

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
            st.error(STRINGS[st.session_state.language]["backend_error"])
            st.error(f"Details: {e}")

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
            st.success(STRINGS[st.session_state.language]["delete_success"])
            self.create_new_chat()
        except requests.exceptions.RequestException as e:
            st.error(STRINGS[st.session_state.language]["delete_error"])
            st.error(f"Details: {e}")
            
class FileUploaderComponent:
    """Handles file uploading and background processing."""
    def __init__(self, backend_url):
        self.backend_url = backend_url
        self.display_uploader_and_button()

    def display_uploader_and_button(self):
        """Shows the file uploader and handles the processing logic."""
        strings = STRINGS[st.session_state.language]
        uploaded_files = st.sidebar.file_uploader(
            strings["upload_label"],
            type="pdf",
            accept_multiple_files=True,
            help="You can upload multiple PDF files at once.",
            disabled=st.session_state.is_processing # Disabled while processing
        )

        if uploaded_files and st.button(strings["upload_button"], disabled=st.session_state.is_processing):
            self.process_files(uploaded_files)
            
        if st.session_state.uploaded_filenames:
            st.sidebar.markdown("---")
            st.sidebar.subheader(strings["uploaded_files_header"])
            for filename in st.session_state.uploaded_filenames:
                st.sidebar.write(f"• {filename}")

    def process_files(self, uploaded_files):
        """Sends files to the backend for processing and polls for task status."""
        strings = STRINGS[st.session_state.language]
        if not uploaded_files:
            st.error(strings["no_files_error"])
            return
        
        st.session_state.is_processing = True
        
        files_data = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_files]
        st.session_state.uploaded_filenames = [file.name for file in uploaded_files]
        
        with st.spinner(strings["processing_spinner"]):
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
                st.info(strings["processing_spinner"])
                
                self.poll_task_status(task_id)

            except requests.exceptions.RequestException as e:
                st.error(strings["processing_error"])
                st.error(f"Details: {e}")
                st.session_state.is_processing = False
    
    def poll_task_status(self, task_id):
        """Polls the backend for the status of the processing task."""
        strings = STRINGS[st.session_state.language]
        with st.spinner(strings["processing_spinner"]):
            while True:
                task_response = requests.get(f"{self.backend_url}/task-status/{task_id}")
                task_data = task_response.json()
                state = task_data.get("state")
                
                if state == "SUCCESS":
                    st.session_state.is_processed = True
                    st.success(strings["processing_success"])
                    st.session_state.is_processing = False
                    st.rerun()
                elif state == "FAILURE":
                    st.error(strings["processing_error"])
                    st.session_state.is_processing = False
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
        strings = STRINGS[st.session_state.language]
        disabled_input = not st.session_state.is_processed or st.session_state.is_processing
        if prompt := st.chat_input(strings["chat_placeholder"], disabled=disabled_input):
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                with st.spinner(strings["ai_thinking"]):
                    try:
                        response = requests.post(
                            f"{self.backend_url}/ask-question/",
                            json={
                                "question": prompt,
                                "session_id": st.session_state.session_id,
                                "language": st.session_state.language
                            },
                            timeout=300
                        )
                        response.raise_for_status()
                        
                        updated_messages = response.json().get("messages", [])
                        st.session_state.messages = updated_messages
                        
                        last_ai_message = updated_messages[-1]["content"]
                        placeholder.markdown(last_ai_message)

                    except requests.exceptions.RequestException as e:
                        st.error(strings["backend_error"])
                        st.error(f"Details: {e}")

class DocumentActionsComponent:
    """Handles buttons and logic for document-specific actions."""
    def __init__(self, backend_url):
        self.backend_url = backend_url
        self.display_actions()

    def display_actions(self):
        strings = STRINGS[st.session_state.language]
        st.sidebar.markdown("---")
        st.sidebar.subheader(strings["document_actions_header"])
        
        if not st.session_state.uploaded_filenames:
            st.sidebar.info(strings["no_files_error"])
            return

        action = st.sidebar.selectbox(
            strings["select_action_label"],
            options=["", "Summarize", "Compare", "Classify"],
            format_func=lambda x: strings.get(f"{x.lower()}_button".replace(" ", "_"), x),
            disabled=st.session_state.is_processing
        )

        if action == "Summarize":
            self.summarize_action()
        elif action == "Compare":
            self.compare_action()
        elif action == "Classify":
            self.classify_action()

    def summarize_action(self):
        strings = STRINGS[st.session_state.language]
        if st.sidebar.button(strings["summarize_button"], disabled=st.session_state.is_processing):
            try:
                with st.spinner(strings["ai_thinking"]):
                    response = requests.post(
                        f"{self.backend_url}/summarize/",
                        json={
                            "session_id": st.session_state.session_id,
                            "filenames": st.session_state.uploaded_filenames,
                            "language": st.session_state.language
                        },
                        timeout=300
                    )
                    response.raise_for_status()
                    
                    summary = response.json().get("summary")
                    st.session_state.messages.append({"role": "assistant", "content": summary})
                    st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(strings["action_error"])
                st.error(f"Details: {e}")

    def compare_action(self):
        strings = STRINGS[st.session_state.language]
        selected_files = st.sidebar.multiselect(
            strings["compare_select_label"],
            options=st.session_state.uploaded_filenames,
            disabled=st.session_state.is_processing
        )
        if st.sidebar.button(strings["compare_button"], disabled=st.session_state.is_processing):
            if len(selected_files) < 2:
                st.sidebar.warning(strings["compare_warning"])
                return
            
            try:
                with st.spinner(strings["ai_thinking"]):
                    response = requests.post(
                        f"{self.backend_url}/compare/",
                        json={
                            "session_id": st.session_state.session_id,
                            "filenames": selected_files,
                            "language": st.session_state.language
                        },
                        timeout=300
                    )
                    response.raise_for_status()

                    comparison = response.json().get("comparison")
                    st.session_state.messages.append({"role": "assistant", "content": comparison})
                    st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(strings["action_error"])
                st.error(f"Details: {e}")

    def classify_action(self):
        strings = STRINGS[st.session_state.language]
        if st.sidebar.button(strings["classify_button"], disabled=st.session_state.is_processing):
            try:
                with st.spinner(strings["ai_thinking"]):
                    response = requests.post(
                        f"{self.backend_url}/classify/",
                        json={
                            "session_id": st.session_state.session_id,
                            "language": st.session_state.language
                        },
                        timeout=300
                    )
                    response.raise_for_status()

                    topics = response.json().get("topics")
                    st.session_state.messages.append({"role": "assistant", "content": topics})
                    st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(strings["action_error"])
                st.error(f"Details: {e}")

def main():
    """The main entry point for the Streamlit application."""
    app_manager = AppSessionManager()
    strings = STRINGS[st.session_state.language]
    
    st.title(strings["title"])
    
    with st.sidebar:
        st.subheader(strings["manage_chat_header"])
        

        language_options = {
            "en": "English",
            "es": "Español"
        }
        selected_language = st.selectbox(
            "Select Language",
            options=list(language_options.keys()),
            format_func=lambda x: language_options[x],
            disabled=st.session_state.is_processing
        )

        if selected_language != st.session_state.language:
            st.session_state.language = selected_language
            st.rerun()

        strings = STRINGS[st.session_state.language]

        if st.button(strings["new_chat_button"], disabled=st.session_state.is_processing):
            app_manager.create_new_chat()
        
        FileUploaderComponent(app_manager.backend_url)
        
        if st.session_state.messages:
            if st.button(strings["delete_chat_button"], disabled=st.session_state.is_processing):
                app_manager.delete_chat()

    if not st.session_state.messages and not st.session_state.uploaded_filenames:
        st.info(strings["welcome_message"])
    
    ChatInterface(app_manager.backend_url)
    DocumentActionsComponent(app_manager.backend_url)

if __name__ == "__main__":
    main()