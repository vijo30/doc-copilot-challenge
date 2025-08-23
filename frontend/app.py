import streamlit as st
import requests
import uuid
import time
import os


st.set_page_config(page_title="PDF Chat", page_icon="📄")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.title("📄 Chat with PDF")
st.markdown("Upload a PDF and ask questions about its content.")

if st.sidebar.button("New Chat"):
    new_session_id = str(uuid.uuid4())
    st.session_state.session_id = new_session_id
    st.session_state.is_processed = False
    st.session_state.current_chatroom = {"id": new_session_id, "messages": []}
    
    st.query_params["chatroom"] = new_session_id
    st.rerun()


query_params = st.query_params
session_id_from_url = query_params.get("chatroom")

if "session_id" not in st.session_state:
    if session_id_from_url:
        st.session_state.session_id = session_id_from_url
        st.session_state.is_processed = False
    else:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.is_processed = False
        st.query_params["chatroom"] = st.session_state.session_id  # Initialize the URL for the first time
    
    st.session_state.current_chatroom = {"id": st.session_state.session_id, "messages": []}
    
    try:
        response = requests.get(f"{BACKEND_URL}/chat-history/{st.session_state.session_id}", timeout=300)
        response.raise_for_status()
        data = response.json()
        st.session_state.current_chatroom["messages"] = data.get("messages", [])
        if st.session_state.current_chatroom["messages"]:
            st.session_state.is_processed = True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch chat history: {e}")


uploaded_files = st.sidebar.file_uploader(
    "Upload PDFs",
    type="pdf",
    accept_multiple_files=True,
    help="You can upload multiple PDF files at once."
)

if uploaded_files:
    if st.button("Process PDFs"):
        files_data = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_files]
        with st.spinner("Starting processing..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/process-pdfs/",
                    files=files_data,
                    data={"session_id": st.session_state.session_id},
                    timeout=300,
                )
                response.raise_for_status()
                data = response.json()
                task_id = data.get("task_id")
                st.session_state.is_processed = False
                st.info("Processing PDFs in the background. This may take a few moments.")

                with st.spinner("Processing..."):
                    while True:
                        task_response = requests.get(f"{BACKEND_URL}/task-status/{task_id}")
                        task_data = task_response.json()
                        if task_data.get("state") == "SUCCESS":
                            st.session_state.is_processed = True
                            st.success("PDFs processed successfully!")
                            st.rerun()
                            break
                        elif task_data.get("state") == "FAILURE":
                            st.error("An error occurred during processing.")
                            break
                        time.sleep(2)
                        
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to start PDF processing: {e}")
                st.error("Make sure the backend and worker are running.")
                

for message in st.session_state.current_chatroom["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.is_processed:
    st.info("Please process a document before asking questions.")


if prompt := st.chat_input("Ask a question about the PDF content", disabled=not st.session_state.is_processed):
    st.session_state.current_chatroom["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {
        "session_id": st.session_state.session_id,
        "question": prompt,
    }

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/ask-question/",
                    json=payload,
                    timeout=300
                )
                response.raise_for_status()
                data = response.json()
                messages = data.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if last_message["role"] == "assistant":
                        full_response = last_message["content"].strip()
                        message_placeholder.markdown(full_response)
                        st.session_state.current_chatroom["messages"] = messages
                    else:
                        st.error("Invalid response from backend.")
                else:
                    st.error("Invalid response from backend.")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to get a response from the backend: {e}")