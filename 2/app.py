import os

import chromadb
import streamlit as st
from groq import Groq
from pypdf import PdfReader

# ---------- SETUP ----------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_FOLDER = os.path.join(SCRIPT_DIR, "docs")
DB_FOLDER = os.path.join(SCRIPT_DIR, "db")
os.makedirs(DOCS_FOLDER, exist_ok=True)

MODEL = "openai/gpt-oss-120b"
MAX_CHUNK_CHARS = 600
COLLECTION = "company_docs"

SYSTEM_PROMPT = (
    "You answer employee questions using ONLY the provided document excerpts. "
    "If the answer is not in the excerpts, say: 'I could not find this in the company documents.' "
    "Be short and clear."
)


@st.cache_resource
def get_clients():
    """Create the database and Groq clients once, and reuse them."""
    return chromadb.PersistentClient(path=DB_FOLDER), Groq()


db, llm = get_clients()


# ---------- INGESTION (split + store) ----------

def read_document(path):
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_into_chunks(text):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if current and len(current) + len(p) > MAX_CHUNK_CHARS:
            chunks.append(current)
            current = p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return chunks


def rebuild_database():
    """Delete the old database and store all documents again."""
    try:
        db.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = db.get_or_create_collection(COLLECTION)
    total = 0
    for filename in os.listdir(DOCS_FOLDER):
        chunks = split_into_chunks(read_document(os.path.join(DOCS_FOLDER, filename)))
        if not chunks:
            continue
        collection.add(
            documents=chunks,
            ids=[f"{filename}-{i}" for i in range(len(chunks))],
            metadatas=[{"source": filename, "chunk": i} for i in range(len(chunks))],
        )
        total += len(chunks)
    return total


# ---------- RETRIEVAL + ANSWER ----------

def answer(question):
    collection = db.get_or_create_collection(COLLECTION)
    if collection.count() == 0:
        return "No documents in the database yet. Upload files and click 'Rebuild database'.", []

    results = collection.query(query_texts=[question], n_results=3)
    chunks = results["documents"][0]
    metas = results["metadatas"][0]

    context = "\n\n".join(
        f"[Source: {m['source']}, chunk {m['chunk']}]\n{c}" for c, m in zip(chunks, metas)
    )
    response = llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Document excerpts:\n{context}\n\nQuestion: {question}"},
        ],
    )
    sources = [(m["source"], m["chunk"], c) for c, m in zip(chunks, metas)]
    return response.choices[0].message.content, sources


# ---------- WEB PAGE ----------

st.set_page_config(page_title="Company Docs Chatbot", page_icon="💬")
st.title("💬 Company Docs Chatbot")
st.caption("Ask questions about your company documents. Answers come only from your files.")

with st.sidebar:
    st.header("1. Upload documents")
    uploaded = st.file_uploader("Text or PDF files", type=["txt", "pdf"], accept_multiple_files=True)
    if uploaded:
        for file in uploaded:
            with open(os.path.join(DOCS_FOLDER, os.path.basename(file.name)), "wb") as f:
                f.write(file.getbuffer())
        st.success(f"Saved {len(uploaded)} file(s). Now click 'Rebuild database'.")

    st.header("2. Update the database")
    if st.button("🔄 Rebuild database"):
        with st.spinner("Reading and storing documents..."):
            total = rebuild_database()
        st.success(f"Stored {total} chunks.")

    st.subheader("Documents")
    for name in sorted(os.listdir(DOCS_FOLDER)):
        st.write("•", name)

if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if msg.get("sources"):
            with st.expander("📚 Sources"):
                for source, chunk, text in msg["sources"]:
                    st.markdown(f"**{source}** (chunk {chunk})")
                    st.caption(text[:300])

question = st.chat_input("Ask a question...")
if question:
    st.session_state.chat.append({"role": "user", "text": question})
    with st.spinner("Searching documents..."):
        reply, sources = answer(question)
    st.session_state.chat.append({"role": "assistant", "text": reply, "sources": sources})
    st.rerun()