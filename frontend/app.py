import streamlit as st

def main():
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
            st.success(f"{len(uploaded_files)} file(s) uploaded successfully!")
            st.write("Processing files...")
            
            
if __name__ == "__main__":
  main()