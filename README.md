# Invoice Document Agent

An AI agent that reads business invoices, extracts key information,
and generates an Excel-ready CSV summary report automatically.

## What it does
- Finds all documents in the `docs/` folder by itself
- Reads each invoice and extracts client, city, amounts, status and due date
- Answers questions like "Who still owes me money?"
- Saves a summary report to `output/` as a CSV file (opens in Excel)
- Checks its own work: if it forgets to save the report, it is reminded to do so

## How it works
The agent uses a tool-calling loop: the AI model decides which tool to use
(`list_files`, `read_file`, `save_report`), the Python code runs it, and the
result is sent back until the task is complete.

## Setup
1. Install requirements: `pip install -r requirements.txt`
2. Get a free API key from https://console.groq.com
3. Set it as an environment variable: `setx GROQ_API_KEY "your-key"`
4. Put your invoice files in the `docs/` folder
5. Run: `python doc_agent.py`

## Example
> You: Read all invoices and save a report called invoices_summary.csv

The agent reads every invoice and creates `output/invoices_summary.csv`.

## Built with
Python, Groq API (gpt-oss-120b), tool calling / agent loop