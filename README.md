# Invoice Document Agent

An AI agent that reads business invoices, extracts key information,
and generates Excel-ready CSV summary reports automatically, with a simple web interface.

## What it does
- Upload invoice files through a web page
- Finds and reads every document by itself
- Extracts client, city, amounts, status and due date
- Answers questions like "Who still owes me money?"
- Saves summary reports as CSV files (open in Excel) with a download button
- Checks its own work: if it forgets to save a requested report, it is reminded to do so

## How it works
The agent uses a tool-calling loop: the AI model decides which tool to use
(`list_files`, `read_file`, `save_report`), the Python code runs it, and the
result is sent back until the task is complete.

## Setup
1. Install requirements: `pip install -r requirements.txt`
2. Get a free API key from https://console.groq.com
3. Set it as an environment variable: `setx GROQ_API_KEY "your-key"`
4. Run the web app: `streamlit run app.py`
   (or the terminal version: `python doc_agent.py`)

## Example
> Read all invoices and save a report called invoices_summary.csv

The agent reads every invoice, creates the report, and a download button appears.

## Built with
Python, Streamlit, Groq API (gpt-oss-120b), tool calling / agent loop