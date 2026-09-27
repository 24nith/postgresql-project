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

# Database Connection Helper
def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None
    try:
        conn = psycopg2.connect(database_url)
        register_vector(conn)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

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
db_status = "Connected" if os.environ.get("DATABASE_URL") else "Not Configured"
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
        st.metric(label="Vector Extension", value="pgvector Enabled" if db_status == "Connected" else "Unknown")
    with col3:
        st.metric(label="RAG Engine", value=ai_status)
        
    st.markdown("### Welcome to your PostgreSQL & Vector Console")
    st.write("""
    This application allows you to manage your PostgreSQL database with `pgvector` extensions, 
    explore tables, run custom SQL queries, and execute Retrieval-Augmented Generation (RAG) 
    vector searches using OpenAI embeddings.
    """)
    
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
        st.warning("Please configure your `DATABASE_URL` environment variable to connect to your PostgreSQL database.")

elif st.session_state.active_tab == "explorer":
    st.title("Database Explorer")
    st.caption("Browse tables and inspect schema")
    
    conn = get_connection()
    if not conn:
        st.error("Database connection not available.")
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
        else:
            client = get_openai_client()
            conn = get_connection()
            
            if not client:
                st.error("OpenAI API key is missing or invalid.")
            elif not conn:
                st.error("Database connection not available.")
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
                            WHERE data_type = 'USER-DEFINED' AND table_schema = 'public';
                        """)
                        vector_columns = cur.fetchall()
                        
                        if not vector_columns:
                            st.info("No vector columns found in the database. Ensure you have a table with a vector column to perform RAG searches.")
                        else:
                            st.write("Found vector columns:", vector_columns)
                            # Perform sample vector similarity search on the first found vector table/column
                            t_name, c_name = vector_columns[0][0], vector_columns[0][1]
                            
                            # Example similarity query using cosine distance (<=>)
                            sql = f"SELECT * FROM {t_name} ORDER BY {c_name} <=> %s::vector LIMIT 5;"
                            cur.execute(sql, (str(query_embedding),))
                            results = cur.fetchall()
                            colnames = [desc[0] for desc in cur.description]
                            
                            if results:
                                st.subheader("Top Matching Contexts")
                                import pandas as pd
                                df_res = pd.DataFrame(results, columns=colnames)
                                st.dataframe(df_res, use_container_width=True)
                            else:
                                st.warning("No matching vectors found.")
                        
                        cur.close()
                        conn.close()
                except Exception as e:
                    st.error(f"Error during RAG execution: {e}")

elif st.session_state.active_tab == "sql":
    st.title("SQL Query Console")
    st.caption("Execute arbitrary SQL queries against your PostgreSQL database")
    
    default_query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
    sql_query = st.text_area("SQL Query", value=default_query, height=150)
    
    if st.button("Execute Query"):
        conn = get_connection()
        if not conn:
            st.error("Database connection not available.")
        else:
            try:
                cur = conn.cursor()
                cur.execute(sql_query)
                
                if cur.description:
                    rows = cur.fetchall()
                    colnames = [desc[0] for desc in cur.description]
                    import pandas as pd
                    df = pd.DataFrame(rows, columns=colnames)
                    st.dataframe(df, use_container_width=True)
                else:
                    conn.commit()
                    st.success("Query executed successfully (no results returned).")
                
                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"Error executing SQL: {e}")
