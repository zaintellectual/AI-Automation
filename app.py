import csv
import json
import os

import streamlit as st
from groq import Groq

# ---------- SETUP ----------

client = Groq()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_FOLDER = os.path.join(SCRIPT_DIR, "docs")
OUTPUT_FOLDER = os.path.join(SCRIPT_DIR, "output")
os.makedirs(DOCS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

MODEL = "openai/gpt-oss-120b"


# ---------- TOOLS ----------

def list_files() -> list:
    """List all files in the docs folder."""
    return os.listdir(DOCS_FOLDER)


def read_file(filename: str) -> str:
    """Read a file from the docs folder."""
    safe_name = os.path.basename(filename)
    path = os.path.join(DOCS_FOLDER, safe_name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_report(filename: str, rows: list) -> str:
    """Save a list of rows (dictionaries) as a CSV file in the output folder."""
    if not rows:
        return "Error: no rows to save."
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".csv"):
        safe_name += ".csv"
    path = os.path.join(OUTPUT_FOLDER, safe_name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return f"Saved {len(rows)} rows to output/{safe_name}"


tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the names of all available documents. Always call this first.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full text of one document by its file name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Exact file name, e.g. invoice_001.txt"}
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_report",
            "description": (
                "Save a table as a real CSV file on disk (opens in Excel). "
                "You MUST call this whenever the user asks to save, export or create a report. "
                "Each row is an object with the same keys."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Report file name, e.g. invoices_summary.csv"},
                    "rows": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "The table rows; every row must have the same keys",
                    },
                },
                "required": ["filename", "rows"],
            },
        },
    },
]

available_tools = {"list_files": list_files, "read_file": read_file, "save_report": save_report}

SYSTEM_PROMPT = (
    "You are a helpful office assistant with access to the user's documents through tools. "
    "ALWAYS call list_files first, then read_file for relevant documents, before answering. "
    "Never guess numbers; read the files first. "
    "When the user asks for a report, table or file, you MUST call save_report to create "
    "the real file. Do not just print the table as text. "
    "If the information isn't in the documents, say so."
)

SAVE_WORDS = ["save", "report", "export", "csv", "excel", "file"]


# ---------- THE AGENT LOOP ----------

def run_agent(question):
    """Run the agent. Returns (final_answer, list_of_steps)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    steps = []
    wants_file = any(word in question.lower() for word in SAVE_WORDS)
    saved = False
    reminded = False

    for step in range(15):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        msg = response.choices[0].message

        if not msg.tool_calls:
            if wants_file and not saved and not reminded:
                steps.append("Check: no file saved yet, reminding the model")
                messages.append({"role": "assistant", "content": msg.content or ""})
                messages.append({
                    "role": "user",
                    "content": "You have not saved the file yet. Call save_report now with the table.",
                })
                reminded = True
                continue
            return msg.content, steps

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            try:
                result = available_tools[tc.function.name](**args)
                if tc.function.name == "save_report":
                    saved = True
            except Exception as e:
                result = f"Error: {e}"
            steps.append(f"{tc.function.name} → {str(result)[:80]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    return "Stopped: too many steps.", steps


# ---------- WEB PAGE ----------

st.set_page_config(page_title="Invoice Agent", page_icon="📄")
st.title("📄 Invoice Document Agent")
st.caption("Upload invoices, ask questions, and download Excel-ready reports.")

# Sidebar: upload documents and download reports
with st.sidebar:
    st.header("1. Upload invoices")
    uploaded = st.file_uploader("Text files (.txt)", type=["txt"], accept_multiple_files=True)
    if uploaded:
        for file in uploaded:
            with open(os.path.join(DOCS_FOLDER, os.path.basename(file.name)), "wb") as f:
                f.write(file.getbuffer())
        st.success(f"Saved {len(uploaded)} file(s).")

    st.subheader("Documents")
    for name in sorted(os.listdir(DOCS_FOLDER)):
        st.write("•", name)

    st.header("2. Download reports")
    reports = sorted(os.listdir(OUTPUT_FOLDER))
    if not reports:
        st.write("No reports yet.")
    for name in reports:
        with open(os.path.join(OUTPUT_FOLDER, name), "rb") as f:
            st.download_button(f"⬇️ {name}", f.read(), file_name=name, key=name)

# Chat area
if "chat" not in st.session_state:
    st.session_state.chat = []

for role, text in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)

question = st.chat_input("Ask about your invoices...")
if question:
    st.session_state.chat.append(("user", question))
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.status("Agent is working...") as status:
            answer, steps = run_agent(question)
            for s in steps:
                st.write(s)
            status.update(label="Done", state="complete")
        st.markdown(answer)

    st.session_state.chat.append(("assistant", answer))
    st.rerun()  # refresh the sidebar so new reports appearstreamlit run app.py