import streamlit as st

from rag_agent import CHAT_MODEL, EMBED_MODEL, DocumentStore, build_rag_graph


st.set_page_config(page_title="Local PDF RAG", page_icon="R", layout="wide")


@st.cache_resource
def get_rag_components(cache_version: int = 2):
    store = DocumentStore()
    return store, build_rag_graph(store)


st.title("Local PDF RAG Agent")
st.caption(f"PostgreSQL storage | Ollama chat: {CHAT_MODEL} | Embeddings: {EMBED_MODEL}")

try:
    store, rag_graph = get_rag_components()
except Exception as error:
    st.error(f"Could not initialize the application: {error}")
    st.stop()


with st.sidebar:
    st.header("Documents")
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded_file and st.button("Store PDF", type="primary", use_container_width=True):
        try:
            with st.spinner("Extracting, embedding, and storing PDF chunks..."):
                chunk_count = store.ingest_pdf(uploaded_file.getvalue(), uploaded_file.name)
            st.success(f"Stored {chunk_count} chunks from {uploaded_file.name}")
        except Exception as error:
            st.error(f"PDF storage failed: {error}")

    st.subheader("Stored documents")
    names = store.document_names()
    if names:
        for name in names:
            st.write(f"- {name}")
    else:
        st.caption("No PDFs stored yet")

    st.subheader("Stored PDF text")
    stored_chunks = store.stored_chunks()
    if stored_chunks:
        st.caption(f"{len(stored_chunks)} chunks stored in PostgreSQL")
        for chunk in stored_chunks:
            with st.expander(f"Chunk {chunk['id']} - {chunk['filename']}"):
                st.write(chunk["content"])
    else:
        st.caption("No PDF chunks stored yet")


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            st.caption("Sources: " + ", ".join(message["sources"]))


question = st.chat_input("Ask a question about your uploaded PDFs")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching your documents..."):
                result = rag_graph.invoke({"question": question})
            st.markdown(result["answer"])
            if result.get("sources"):
                st.caption("Sources: " + ", ".join(result["sources"]))
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get("sources", []),
            })
        except Exception as error:
            st.error(f"RAG request failed: {error}")
