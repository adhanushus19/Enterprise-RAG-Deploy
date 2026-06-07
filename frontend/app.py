import os
import streamlit as st
import requests
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Enterprise AI Knowledge Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL & API Key configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "enterprise-secret-key-123")
headers = {"X-API-Key": API_KEY}

# Premium Custom CSS
st.markdown("""
<style>
    /* Dark Theme Core Styles */
    .stApp {
        background-color: #080B10;
        color: #E2E8F0;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0F131A;
        border-right: 1px solid #1E293B;
    }
    
    /* Headers styling */
    h1, h2, h3 {
        color: #00F0FF;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Neon glow cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(0, 240, 255, 0.15);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    }
    
    /* Chat bubbles styling */
    .stChatMessage {
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Custom citation tag */
    .citation-tag {
        display: inline-block;
        background: rgba(0, 240, 255, 0.1);
        color: #00F0FF;
        border: 1px solid rgba(0, 240, 255, 0.3);
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.8em;
        margin-right: 5px;
        cursor: pointer;
    }
    .citation-tag:hover {
        background: rgba(0, 240, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.title("🤖 Enterprise AI Knowledge Assistant")
st.markdown("##### *Production-Grade RAG Multi-Agent Assistant*")

# Fetch unique filters from existing documents
@st.cache_data(ttl=10)
def get_filter_options():
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/documents", headers=headers)
        if response.status_code == 200:
            docs = response.json()
            df = pd.DataFrame(docs)
            if not df.empty:
                departments = sorted(list(df["department"].dropna().unique()))
                doc_types = sorted(list(df["doc_type"].dropna().unique()))
                all_tags = []
                for tags_list in df["tags"].dropna():
                    all_tags.extend(tags_list)
                unique_tags = sorted(list(set(all_tags)))
                return departments, doc_types, unique_tags
    except Exception as e:
        st.sidebar.warning(f"Could not connect to database to load filters: {str(e)}")
    return [], [], []

departments, doc_types, tags = get_filter_options()

# Sidebar configuration
st.sidebar.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=80)
st.sidebar.markdown("### **Search Scope Filters**")

selected_department = st.sidebar.selectbox("Filter Department", ["All"] + departments)
selected_doc_type = st.sidebar.selectbox("Filter File Format", ["All"] + doc_types)
selected_tags = st.sidebar.multiselect("Filter Keywords/Tags", tags)

# Map filters
active_filters = {}
if selected_department != "All":
    active_filters["department"] = selected_department
if selected_doc_type != "All":
    active_filters["doc_type"] = selected_doc_type
if selected_tags:
    active_filters["tags"] = selected_tags

# Chat History Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Conversational History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "citations" in message and message["citations"]:
            with st.expander("References"):
                for cit in message["citations"]:
                    st.markdown(
                        f"**[{cit['id']}] {cit['filename']}** (Page/Row {cit['page_number']})  \n"
                        f"*Snippet:* \"{cit['snippet']}\"  \n"
                        f"*Department:* {cit['department']} | *Author:* {cit['author']}"
                    )

# Input Query
if prompt := st.chat_input("Ask a question about the enterprise policies, logistics data, or financial sheets..."):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Perform backend request
    with st.chat_message("assistant"):
        with st.spinner("Multi-agent swarm searching and verifying facts..."):
            # Prepare request body
            payload = {
                "query": prompt,
                "filters": active_filters if active_filters else None,
                "chat_history": [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[-5:-1]  # Include last few messages for memory context
                ] if len(st.session_state.messages) > 1 else None
            }
            
            try:
                response = requests.post(f"{BACKEND_URL}/api/v1/query", json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    citations = data["citations"]
                    
                    st.markdown(answer)
                    
                    if citations:
                        with st.expander("References"):
                            for cit in citations:
                                st.markdown(
                                    f"**[{cit['id']}] {cit['filename']}** (Page/Row {cit['page_number']})  \n"
                                    f"*Snippet:* \"{cit['snippet']}\"  \n"
                                    f"*Department:* {cit['department']} | *Author:* {cit['author']}"
                                )
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "citations": citations
                    })
                else:
                    err = response.json().get("detail", "Unknown error")
                    st.error(f"Error: {err}")
            except Exception as e:
                st.error(f"Failed to reach backend API: {str(e)}")
