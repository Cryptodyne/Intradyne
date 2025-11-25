# INTRADYNE v1.1

## System Status
- **Identity**: Autonomous, Ultra-Strict Shariah, Hybrid-Risk AI Trading System.
- **Architecture**: Hybrid Ensemble (7 Engines) + RAG (Rulebook/SOPs).
- **Frontend**: Next.js (Local Dashboard).
- **Backend**: FastAPI + Python.

## Setup

1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Initialize Knowledge Base (RAG)**:
    ```bash
    python -m scripts.ingest_knowledge
    ```

3.  **Run Backend**:
    ```bash
    python main.py
    ```

4.  **Run Frontend**:
    ```bash
    cd src/interface
    npm run dev
    ```

## Directory Structure
- `config/`: Governance documents (Rules, SOPs).
- `src/core/`: Main logic (Coordinator, RAG).
- `src/engines/`: The 7 Hybrid Engines.
- `src/interface/`: Next.js Web Dashboard.
- `data/`: Logs and Vector Store.
