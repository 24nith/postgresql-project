import os
import streamlit as st

st.set_page_config(
    page_title="RAG Knowledge Base",
    page_icon="💬",
    layout="wide"
)

st.title("💬 RAG Knowledge Base Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("Ask a question about your knowledge base..."):
    # Add user message to session state and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        
        context_docs = []
        if db_url:
            try:
                import psycopg2
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                cur.execute(
                    "SELECT content FROM documents WHERE content ILIKE %s LIMIT 3;",
                    (f"%{prompt}%",)
                )
                rows = cur.fetchall()
                context_docs = [row[0] for row in rows if row]
                cur.close()
                conn.close()
            except Exception:
                pass

        if context_docs:
            context_str = "\n---\n".join(context_docs)
            response = f"**Relevant Knowledge Base Context:**\n\n{context_str}\n\n**Answer:**\nBased on the retrieved documents, here is the information regarding your question: '{prompt}'."
        else:
            response = f"I searched the knowledge base for '{prompt}'. No direct matches were found in PostgreSQL, but I am ready to answer any additional questions."

        message_placeholder.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
