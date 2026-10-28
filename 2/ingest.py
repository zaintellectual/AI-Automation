import os

import chromadb
from pypdf import PdfReader

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_FOLDER = os.path.join(SCRIPT_DIR, "docs")
DB_FOLDER = os.path.join(SCRIPT_DIR, "db")

MAX_CHUNK_CHARS = 600  # roughly 1-2 paragraphs per chunk


def read_document(path):
    """Read text from a .txt or .pdf file."""
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_into_chunks(text):
    """Split text into chunks of whole paragraphs, each up to MAX_CHUNK_CHARS."""
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


# Connect to the database (saved in the "db" folder)
db = chromadb.PersistentClient(path=DB_FOLDER)

# Start fresh each time, so edited documents don't leave old chunks behind
try:
    db.delete_collection("company_docs")
except Exception:
    pass
collection = db.get_or_create_collection("company_docs")

total = 0
for filename in os.listdir(DOCS_FOLDER):
    path = os.path.join(DOCS_FOLDER, filename)
    chunks = split_into_chunks(read_document(path))
    if not chunks:
        print(f"Skipped {filename} (no text)")
        continue
    collection.add(
        documents=chunks,
        ids=[f"{filename}-{i}" for i in range(len(chunks))],
        metadatas=[{"source": filename, "chunk": i} for i in range(len(chunks))],
    )
    print(f"{filename}: {len(chunks)} chunks")
    total += len(chunks)

print(f"Done. {total} chunks stored in the database.")