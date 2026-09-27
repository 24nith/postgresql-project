import streamlit as st
import os
import psycopg2
from pgvector.psycopg2 import register_vector
import openai

# Page configuration
st.set_page_config(
    page_title="PostgreSQL + pgvector Console",
    page_icon="🐘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for navigation and data
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "dashboard"

# Helper to check if DATABASE_URL is present and not a placeholder
def is_database_url_configured():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    placeholders = ["your_database_url", "postgres://user:password@host:port/dbname", "postgresql://user:password@host:port/dbname", "placeholder"]
    if any(p in url.lower() for p in placeholders):
        return False
    return True

# Database Connection Helper
def get_connection():
    if not is_database_url_configured():
        return None
    database_url = os.environ.get("DATABASE_URL")
    try:
        conn = psycopg2.connect(database_url)
        register_vector(conn)
        return conn
    except Exception as e:
        return None

# Test live connection and query for dashboard status
def check_live_database():
    if not is_database_url_configured():
        return False, "Not Configured"
    database_url = os.environ.get("DATABASE_URL")
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, "Connected"
    except Exception as e:
        return False, "Connection Error"

# OpenAI Client Helper
def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception as e:
        return None

# Sidebar Navigation
st.sidebar.title("🐘 PostgreSQL + pgvector")
st.sidebar.caption("Professional Database & Vector Search Console")

nav_selection = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Database Explorer", "Vector Search (RAG)", "SQL Query Console"],
    index=0 if st.session_state.active_tab == "dashboard" else 
          (1 if st.session_state.active_tab == "explorer" else 
           (2 if st.session_state.active_tab == "rag" else 3))
)

if nav_selection == "Dashboard":
    st.session_state.active_tab = "dashboard"
elif nav_selection == "Database Explorer":
    st.session_state.active_tab = "explorer"
elif nav_selection == "Vector Search (RAG)":
    st.session_state.active_tab = "rag"
elif nav_selection == "SQL Query Console":
    st.session_state.active_tab = "sql"

st.sidebar.markdown("---")
st.sidebar.subheader("Environment Status")
is_live, db_status_text = check_live_database()
db_status = db_status_text if is_live else ("Not Configured" if not is_database_url_configured() else "Error")
ai_status = "Configured" if os.environ.get("OPENAI_API_KEY") else "Missing API Key"
st.sidebar.text(f"Database: {db_status}")
st.sidebar.text(f"OpenAI: {ai_status}")

# Main Content Routing
if st.session_state.active_tab == "dashboard":
    st.title("PostgreSQL + pgvector")
    st.caption("Professional Database & Vector Search Console")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Database Status", value=db_status)
    with col2:
        st.metric(label="Vector Extension", value="pgvector Enabled" if is_live else "Unknown")
    with col3:
        st.metric(label="RAG Engine", value=ai_status)
        
    st.markdown("### Welcome to your PostgreSQL & Vector Console")
    st.write("""
    This application allows you to manage your PostgreSQL database with `pgvector` extensions, 
    explore tables, run custom SQL queries, and execute Retrieval-Augmented Generation (RAG) 
    vector searches using OpenAI embeddings.
    """)
    
    if not is_database_url_configured():
        st.error("Configuration Error: `DATABASE_URL` is absent, invalid, or still set to a placeholder value. Please provide a valid PostgreSQL connection string.")
    else:
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                tables = cur.fetchall()
                cur.close()
                conn.close()
                
                st.success(f"Successfully connected to PostgreSQL! Found {len(tables)} public tables.")
                if tables:
                    st.write("Existing tables:", ", ".join([t[0] for t in tables]))
            except Exception as e:
                st.error(f"Error querying database catalog: {e}")
        else:
            try:
                # Try connecting directly to get the exact error without printing credentials
                database_url = os.environ.get("DATABASE_URL")
                psycopg2.connect(database_url)
            except Exception as e:
                st.error(f"Database connection error: {e}")

elif st.session_state.active_tab == "explorer":
    st.title("Database Explorer")
    st.caption("Browse tables and inspect schema")
    
    if not is_database_url_configured():
        st.error("Configuration Error: `DATABASE_URL` is absent, invalid, or still set to a placeholder value.")
    else:
        conn = get_connection()
        if not conn:
            try:
                database_url = os.environ.get("DATABASE_URL")
                psycopg2.connect(database_url)
            except Exception as e:
                st.error(f"Database connection error: {e}")
        else:
            try:
                cur = conn.cursor()
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
                tables = [t[0] for t in cur.fetchall()]
                
                if not tables:
                    st.info("No tables found in the public schema.")
                else:
                    selected_table = st.selectbox("Select Table", tables)
                    if selected_table:
                        st.subheader(f"Contents of `{selected_table}`")
                        cur.execute(f"SELECT * FROM {selected_table} LIMIT 100;")
                        rows = cur.fetchall()
                        colnames = [desc[0] for desc in cur.description]
                        
                        if rows:
                            import pandas as pd
                            df = pd.DataFrame(rows, columns=colnames)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info(f"Table `{selected_table}` is empty.")
                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"Error exploring database: {e}")

elif st.session_state.active_tab == "rag":
    st.title("Vector Search (RAG)")
    st.caption("Perform semantic search and generative responses using pgvector and OpenAI")
    
    query_text = st.text_input("Enter your search query or question:")
    
    if st.button("Search & Generate"):
        if not query_text:
            st.warning("Please enter a query.")
        elif not is_database_url_configured():
            st.error("Configuration Error: `DATABASE_URL` is absent, invalid, or still set to a placeholder value.")
        else:
            client = get_openai_client()
            conn = get_connection()
            
            if not client:
                st.error("OpenAI API key is missing or invalid.")
            elif not conn:
                try:
                    database_url = os.environ.get("DATABASE_URL")
                    psycopg2.connect(database_url)
                except Exception as e:
                    st.error(f"Database connection error: {e}")
            else:
                try:
                    with st.spinner("Generating embedding and searching vector space..."):
                        # Generate embedding for query
                        response = client.embeddings.create(
                            input=query_text,
                            model="text-embedding-ada-002"
                        )
                        query_embedding = response.data[0].embedding
                        
                        # Search database for similar vectors (assuming a standard table structure or demonstrating vector query)
                        # Here we gracefully check if a vector-enabled table exists or provide instructions
                        cur = conn.cursor()
                        cur.execute("""
                            SELECT table_name, column_name 
                            FROM information_schema.columns
