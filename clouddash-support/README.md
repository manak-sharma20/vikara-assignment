# CloudDash Multi-Agent Support System

A beginner-friendly multi-agent customer support system for a fictional SaaS product called "CloudDash". This prototype demonstrates dynamic routing, RAG (Retrieval-Augmented Generation), and agent handover logging using Claude-3-Haiku.

## Setup

```bash
git clone https://github.com/your-username/clouddash-support.git
cd clouddash-support
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env
python knowledge_base/ingest.py   # Load KB articles
uvicorn api.main:app --reload     # Start the server

# In a separate terminal or simply double-click the file in your file explorer:
# Open `index.html` in your browser to interact with the Chat UI.
```

## Architecture overview

The system acts as a smart dispatcher for incoming support messages. Incoming chat messages first hit the Orchestrator, which classifies the user's intent into one of four categories using Llama 3 via Groq. Based on this intent, the system routes the query to one of four specialized agents: Triage, Technical, Billing, or Escalation. Each agent receives a unique system prompt, combined with context retrieved from a local ChromaDB instance via a simple RAG pipeline. When an intent shifts (e.g. going from a technical question to a billing question), the Orchestrator logs a handover event in a flat file for audit purposes.

## Design decisions

- **Why ChromaDB**: Simple to set up, runs locally with no extra dependencies, and requires no API key or external network calls.
- **Why no LangChain**: Avoiding complex abstraction layers makes the codebase easier to read, explain, and modify for a beginner.
- **Why flat files for logs**: Using a `.jsonl` text file for handovers is extremely simple and avoids the overhead of setting up a relational database for a prototype.
- **Why Groq & Llama 3**: It provides an excellent balance of high speed and low cost, perfect for rapid prototyping and testing.
- **Why FastAPI**: It offers a fast, modern, and simple way to build REST APIs with automatic request validation using Pydantic.
- **Why plain Python logic**: Preferring `if/elif` statements and minimal OOP ensures the control flow remains transparent and beginner-friendly.

## Known limitations

- **Sessions are in-memory**: All conversation histories are lost upon server restart because they are stored in a simple Python dictionary.
- **No API authentication**: The endpoints are currently public and unauthenticated, lacking tokens or user verification.
- **Limited scalability**: Reading flat `.jsonl` files and keeping sessions in-memory won't scale across multiple worker processes.
- **Hardcoded user intent classes**: Intent classification relies on a single LLM call with a static prompt rather than a more robust embedding-based router.

## Running the test scenarios

To run the full suite of integration tests (ensure your `GROQ_API_KEY` is set):

```bash
pytest tests/ -v
```
