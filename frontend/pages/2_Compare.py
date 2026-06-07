import os
import streamlit as st
import requests

st.set_page_config(page_title="Compare Documents", page_icon="⚖️", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "enterprise-secret-key-123")
headers = {"X-API-Key": API_KEY}

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

st.title("⚖️ Document Comparative Analyzer")
st.markdown("### Auditing policies, draft revisions, and financial schedules side-by-side.")

# Load completed documents
try:
    res = requests.get(f"{BACKEND_URL}/api/v1/documents", headers=headers)
    if res.status_code == 200:
        docs = [d for d in res.json() if d["status"] == "completed"]
    else:
        docs = []
except Exception as e:
    st.error(f"Could not connect to backend: {str(e)}")
    docs = []

if len(docs) < 2:
    st.info("Please index at least 2 completed documents in the corporate library to perform comparison.")
else:
    # Selection
    selected_docs = st.multiselect(
        "Select 2 or more documents to compare",
        options=docs,
        format_func=lambda d: f"{d['filename']} (Dept: {d['department']}, Author: {d['author']})"
    )

    # Prompt
    prompt = st.text_area(
        "Focus Area / Custom Instructions",
        value="Provide a detailed comparison table. List key parameters, contrast policies, and note any conflicting terms or updates between files.",
        help="Customize the comparative perspective (e.g. check travel allowance limits, compare security definitions)"
    )

    if st.button("Generate Comparison Report"):
        if len(selected_docs) < 2:
            st.warning("You must select at least 2 documents.")
        else:
            with st.spinner("Analyzing text chunks, identifying overlaps, and formatting comparison table..."):
                payload = {
                    "document_ids": [d["id"] for d in selected_docs],
                    "comparison_prompt": prompt
                }
                
                try:
                    res = requests.post(f"{BACKEND_URL}/api/v1/compare", json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        st.success("Comparison Report Compiled Successfully!")
                        st.markdown("---")
                        st.markdown(data["comparison"])
                    else:
                        st.error(f"Comparison failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"Failed to communicate with comparison engine: {str(e)}")
stream_data = ""
