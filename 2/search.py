import os

import chromadb

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
db = chromadb.PersistentClient(path=os.path.join(SCRIPT_DIR, "db"))
collection = db.get_collection("company_docs")

while True:
    question = input("\nSearch: ")
    if question.lower() == "quit":
        break

    results = collection.query(query_texts=[question], n_results=2)

    for text, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        print(f"\n--- {meta['source']} (chunk {meta['chunk']}), distance {distance:.3f} ---")
        print(text[:300])