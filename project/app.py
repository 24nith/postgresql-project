import os
import streamlit as st
import psycopg2
from urllib.parse import urlparse

st.set_page_config(page_title="AI Engineering App", page_icon="🤖", layout="wide")

st.title("🤖 AI Engineering Dashboard")

# Retrieve and sanitize DATABASE_URL
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Function to check database connectivity safely without exposing credentials
def check_db_connection(url):
    if not url or "placeholder" in url or "your_database_url" in url:
        return False, "DATABASE_URL is absent, a placeholder, or invalid. Please set a valid DATABASE_URL in your environment configuration."
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return False, "Invalid DATABASE_URL format."
        
        conn = psycopg2.connect(url, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, None
    except Exception as e:
        # Return a safe error message without leaking credentials
        return False, f"PostgreSQL connection failed: {type(e).__name__}"

st.sidebar.header("Configuration Status")

# Database Status Check
is_connected, error_msg = check_db_connection(db_url)

if is_connected:
    st.sidebar.success("PostgreSQL: Connected")
else:
    st.sidebar.error("PostgreSQL: Disconnected")
    if not db_url:
        st.error("Configuration Error: The `DATABASE_URL` environment variable is not set. Please set it in your environment configuration.")
    else:
        st.error(f"Configuration Error: {error_msg}")

st.header("Application Overview")
st.write("Welcome to the AI Engineering application dashboard. Use the sidebar to check system status.")

# Preserve existing RAG or other placeholder behaviors if applicable
st.subheader("RAG Pipeline Status")
if is_connected:
    st.info("RAG pipeline is ready and connected to the database backend.")
else:
    st.warning("RAG pipeline is running in degraded mode due to database connectivity issues.")
