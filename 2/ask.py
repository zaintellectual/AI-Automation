import os

import chromadb
from groq import Groq

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
db = chromadb.PersistentClient(path=os.path.join(SCRIPT_DIR, "db"))
collection = db.get_collection("company_docs")
client = Groq()

SYSTEM_PROMPT = (
    "You answer employee questions using ONLY the provided document excerpts. "
    "If the answer is not in the excerpts, say: 'I could not find this in the company documents.' "
    "Be short and clear. At the end, list the sources you used."
)


def answer(question):
    # 1. Retrieve the most relevant chunks
    results = collection.query(query_texts=[question], n_results=3)
    chunks = results["documents"][0]
    metas = results["metadatas"][0]

    # 2. Build the context from those chunks
    context = "\n\n".join(
        f"[Source: {m['source']}, chunk {m['chunk']}]\n{c}" for c, m in zip(chunks, metas)
    )

    # 3. Ask the model, giving it only these chunks
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Document excerpts:\n{context}\n\nQuestion: {question}"},
        ],
    )
    return response.choices[0].message.content


while True:
    question = input("\nYou: ")
    if question.lower() == "quit":
        break
    print("AI:", answer(question))