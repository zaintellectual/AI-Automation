# Company Docs Chatbot (RAG)

An AI chatbot that answers employee questions using only a company's own documents,
such as handbooks, policies and manuals, and shows exactly where each answer came from.

## What it does
- Upload company documents (.txt or .pdf) through a web page
- Splits them into chunks and stores them in a vector database (ChromaDB)
- Finds the most relevant sections by meaning, not just keywords
- Answers using only those sections, and shows the sources so answers can be verified
- Says "I could not find this in the company documents" instead of making things up

## How it works (RAG)
1. **Ingest:** documents are split into chunks and converted into embeddings
2. **Retrieve:** the question is matched to the most similar chunks
3. **Generate:** the AI model answers using only those chunks

## Setup
1. Install requirements: `pip install -r requirements.txt`
2. Get a free API key from https://console.groq.com
3. Set it as an environment variable: `setx GROQ_API_KEY "your-key"`
4. Run: `streamlit run app.py`
5. Upload documents in the sidebar and click **Rebuild database**

## Files
- `app.py`: web app (upload, rebuild, chat with sources)
- `ingest.py`: builds the database from the `docs/` folder (command line)
- `ask.py`: chat in the terminal
- `search.py`: test the meaning search without the AI

## Built with
Python, Streamlit, ChromaDB, Groq API (gpt-oss-120b), Retrieval-Augmented Generation