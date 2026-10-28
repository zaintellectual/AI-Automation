import csv
import json
import os
from groq import Groq

client = Groq()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_FOLDER = os.path.join(SCRIPT_DIR, "docs")
OUTPUT_FOLDER = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=== DOC AGENT v3 is running ===")
print("Running file:", os.path.abspath(__file__))
print("Reports will be saved in:", OUTPUT_FOLDER)


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
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".csv"):
        safe_name += ".csv"
    path = os.path.join(OUTPUT_FOLDER, safe_name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return f"Saved {len(rows)} rows to output/{safe_name}"


# ---------- TOOL DESCRIPTIONS ----------

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
                "Each row is an object with the same keys, e.g. "
                "{\"invoice\": \"001\", \"client\": \"Ali Traders\", \"total_pkr\": 65000}."
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
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    wants_file = any(word in question.lower() for word in SAVE_WORDS)
    saved = False
    reminded = False

    for step in range(15):
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            # Check the work: user wanted a file but none was saved → remind once
            if wants_file and not saved and not reminded:
                print("  [check] No file was saved yet, reminding the model...")
                messages.append({"role": "assistant", "content": msg.content or ""})
                messages.append({
                    "role": "user",
                    "content": "You have not saved the file yet. Call save_report now with the table.",
                })
                reminded = True
                continue
            return msg.content

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
            print(f"  [step {step + 1}] {tc.function.name} -> {str(result)[:80]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return "Stopped: too many steps."


# ---------- CHAT WITH YOUR DOCUMENTS ----------

while True:
    question = input("\nYou: ")
    if question.lower() == "quit":
        break
    print("AI:", run_agent(question))