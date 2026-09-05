import json
import os
from io import BytesIO
from typing import TypedDict

import numpy as np
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from pypdf import PdfReader
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "gemma3")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


class RagState(TypedDict, total=False):
    question: str
    context: str
    sources: list[str]
    answer: str


class DocumentStore:
    def __init__(self) -> None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured")
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        self.embeddings = OllamaEmbeddings(
            model=EMBED_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=900,
            chunk_overlap=150,
        )
        self._create_tables()

    def _create_tables(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    embedding JSONB NOT NULL
                )
            """))

    @staticmethod
    def extract_pdf(data: bytes, filename: str) -> list[Document]:
        reader = PdfReader(BytesIO(data))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            content = page.extract_text() or ""
            if content.strip():
                pages.append(Document(
                    page_content=content,
                    metadata={"source": filename, "page": page_number},
                ))
        if not pages:
            raise ValueError("No selectable text was found in this PDF")
        return pages

    def ingest_pdf(self, data: bytes, filename: str) -> int:
        pages = self.extract_pdf(data, filename)
        chunks = self.splitter.split_documents(pages)
        vectors = self.embeddings.embed_documents([chunk.page_content for chunk in chunks])

        with self.engine.begin() as connection:
            document_id = connection.execute(
                text("INSERT INTO rag_documents (filename) VALUES (:filename) RETURNING id"),
                {"filename": filename},
            ).scalar_one()
            for chunk, vector in zip(chunks, vectors):
                connection.execute(
                    text("""
                        INSERT INTO rag_chunks (document_id, filename, content, embedding)
                        VALUES (:document_id, :filename, :content, CAST(:embedding AS JSONB))
                    """),
                    {
                        "document_id": document_id,
                        "filename": filename,
                        "content": chunk.page_content,
                        "embedding": json.dumps(vector),
                    },
                )
        return len(chunks)

    def search(self, question: str, limit: int = 4) -> tuple[str, list[str]]:
        query_vector = np.array(self.embeddings.embed_query(question), dtype=float)
        with self.engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT filename, content, embedding FROM rag_chunks"
            )).mappings().all()

        scored = []
        for row in rows:
            vector = np.array(row["embedding"], dtype=float)
            denominator = np.linalg.norm(query_vector) * np.linalg.norm(vector)
            score = float(np.dot(query_vector, vector) / denominator) if denominator else 0.0
            scored.append((score, row["filename"], row["content"]))

        scored.sort(reverse=True, key=lambda item: item[0])
        selected = scored[:limit]
        context = "\n\n---\n\n".join(item[2] for item in selected)
        sources = sorted({item[1] for item in selected})
        return context, sources

    def document_names(self) -> list[str]:
        with self.engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT filename FROM rag_documents ORDER BY created_at DESC"
            )).scalars()
            return list(dict.fromkeys(rows))

    def stored_chunks(self, filename: str | None = None) -> list[dict[str, str | int]]:
        query = """
            SELECT id, filename, content
            FROM rag_chunks
        """
        parameters = {}
        if filename:
            query += " WHERE filename = :filename"
            parameters["filename"] = filename
        query += " ORDER BY id"

        with self.engine.connect() as connection:
            rows = connection.execute(text(query), parameters).mappings()
            return [dict(row) for row in rows]


def build_rag_graph(store: DocumentStore):
    chat = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    def retrieve(state: RagState) -> RagState:
        context, sources = store.search(state["question"])
        return {"context": context, "sources": sources}

    def generate(state: RagState) -> RagState:
        prompt = f"""You are a precise document question-answering assistant.
Answer the question using only the supplied context. If the context does not contain
an answer, say that you could not find the answer in the uploaded documents.
Do not invent facts. Keep the answer clear and concise.

Context:
{state.get('context', '')}

Question:
{state['question']}
"""
        response = chat.invoke(prompt)
        return {"answer": response.content}

    graph = StateGraph(RagState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()
