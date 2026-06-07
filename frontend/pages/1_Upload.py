import os
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Upload Documents", page_icon="📤", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "enterprise-secret-key-123")
headers = {"X-API-Key": API_KEY}

# Premium Custom CSS (duplicated for consistent layout across pages)
st.markdown("""
<style>
    .stApp { background-color: #080B10; color: #E2E8F0; }
    h1, h2, h3 { color: #00F0FF; font-family: 'Outfit', sans-serif; }
    .stButton>button {
        background-color: #5E00FF; color: white; border-radius: 4px; border: none;
    }
    .stButton>button:hover { background-color: #00F0FF; color: black; }
</style>
""", unsafe_allow_html=True)

st.title("📤 Corporate Document Repository")
st.markdown("### Upload & Index Enterprise Policies, Slide Decks, and Spreadsheets")

# Document Uploader Section
uploaded_files = st.file_uploader(
    "Choose policy, presentation, spreadsheet, or doc files...",
    type=["pdf", "docx", "pptx", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Index Files in Knowledge Base"):
        for uploaded_file in uploaded_files:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    res = requests.post(f"{BACKEND_URL}/api/v1/documents/upload", files=files, headers=headers)
                    if res.status_code == 200:
                        st.success(f"Indexed successfully: {uploaded_file.name}. Ingestion starting in background.")
                    else:
                        st.error(f"Failed to upload {uploaded_file.name}: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Error connecting to server: {str(e)}")
        st.cache_data.clear()

st.markdown("---")
st.subheader("📚 Managed Corporate Library")

# List documents and show actions
def load_documents():
    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/documents", headers=headers)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Could not load library: {str(e)}")
    return []

docs = load_documents()

if not docs:
    st.info("No documents have been indexed yet.")
else:
    df = pd.DataFrame(docs)
    # Reorder for display
    df_display = df[[
        "id", "filename", "doc_type", "department", "author", "status", "created_at"
    ]].copy()
    
    # Render table nicely
    st.dataframe(df_display, use_container_width=True)

    # Row-by-row Delete tool
    st.markdown("#### Danger Zone")
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_del = st.selectbox(
            "Select Document to delete permanent",
            options=docs,
            format_func=lambda d: f"{d['filename']} (Type: {d['doc_type']}, Dept: {d['department']})"
        )
    with col2:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        if st.button("Delete Selected Document"):
            if selected_del:
                with st.spinner("Deleting..."):
                    try:
                        res = requests.delete(
                            f"{BACKEND_URL}/api/v1/documents/{selected_del['id']}",
                            headers=headers
                        )
                        if res.status_code == 200:
                            st.success(f"Deleted {selected_del['filename']}")
                            st.rerun()
                        else:
                            st.error(res.json().get("detail", "Failed to delete"))
                    except Exception as e:
                        st.error(f"Error deleting: {str(e)}")
