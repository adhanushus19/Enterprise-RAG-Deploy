# Development Guide: Enterprise AI Knowledge Assistant

This document provides developer guidelines for setting up, running, testing, and contributing to the RAG Platform.

---

## 1. Local Development Setup

### Business Problem
Developers need a standardized, reproducible local environment that closely mirrors production configurations, avoiding "works on my machine" issues.

### Design Rationale
We utilize Docker Compose to manage database dependencies (PostgreSQL, Qdrant, Prometheus, Grafana) locally, while developers can run the Python services either directly in virtual environments for faster debugging or fully inside containers.

---

## 2. Quickstart Instructions

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- OpenAI API Key

### Step 1: Clone and Set Up Environment
Create a `.env` file in the root workspace directory:
```env
OPENAI_API_KEY=your-actual-openai-api-key
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/knowledge_assistant
QDRANT_HOST=localhost
QDRANT_PORT=6333
API_KEY=enterprise-secret-key-123
```

### Step 2: Spin Up Infrastructure Containers
Start PostgreSQL, Qdrant, Prometheus, and Grafana:
```bash
docker-compose up -d db qdrant prometheus grafana
```
Wait a few seconds for health checks to pass.

### Step 3: Run FastAPI Backend Locally
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Step 4: Run Streamlit Frontend Locally
1. Navigate to the frontend folder:
   ```bash
   cd ../frontend
   ```
2. Create virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Launch Streamlit:
   ```bash
   streamlit run app.py
   ```

---

## 3. Running the Test Suite

We use **pytest** with code coverage reporting. The configuration is isolated and does not require active Qdrant or PostgreSQL servers because it uses in-memory SQLite and mocked network services.

Run tests from the workspace root:
```bash
pytest --cov=backend/app --cov-report=term-missing tests/
```

### Engineering Tradeoffs
* *Tradeoff:* Mocking Qdrant and OpenAI saves token costs and network overhead during CI/CD execution. However, it does not catch schema mismatches. To balance this, integration tests should occasionally be executed against a local running docker test environment before major releases.

---

## 4. Troubleshooting & Database Ingest
- **Metadata Extraction Failures:** If you do not have an OpenAI API key set, the document parser will fall back to using default OS properties (e.g. author="System Ingest") and run normally without crashes.
- **Qdrant Payload Errors:** If Qdrant schemas change, enter Qdrant Dashboard (`http://localhost:6333/dashboard`) and delete the `knowledge_base` collection to let the backend rebuild it.
- **Future Improvements:** Integrate pre-commit hooks (using `black`, `flake8`, `mypy`) to enforce type hints and linting before code is pushed to version control.
