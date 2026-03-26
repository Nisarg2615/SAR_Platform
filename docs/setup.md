# SAR Platform Setup Guide

Welcome to the SAR Platform! This guide will walk you through the complete setup of the local development environment, including both the FastAPI backend and the Next.js frontend, as well as necessary environment variables.

## Prerequisites

- **Python 3.10+** (for the FastAPI backend and AI agents)
- **Node.js 18+** and **npm** (for the Next.js frontend)
- **Docker & Docker Compose** (optional, but recommended for Neo4j, PostgreSQL, Redis)
- **Groq API Key** (for fast, free LLM inference using Llama 3)

---

## 1. Environment Configuration

### Root Environment Variables
Create a file named `.env.local` in the **root directory** of the repository:

```env
# .env.local (Root Directory)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=sarplatform123

POSTGRES_URI=postgresql://saruser:sarpass123@localhost:5432/sardb
REDIS_URL=redis://localhost:6379

# Groq API Key for Agent 3 (Narrative Generation)
GROQ_API_KEY=your_groq_api_key_here
```

### Frontend Environment Variables
By default, the frontend will connect to `http://localhost:8000`. You can configure this by creating `.env.local` inside the `ui/nextjs` directory:

```env
# ui/nextjs/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 2. Backend Setup (FastAPI & LangGraph)

The backend powers the 6-agent LangGraph pipeline, handling data ingestion, risk scoring (XGBoost), and LLM narrative generation.

1. **Navigate to the root directory**:
   ```bash
   cd SAR-platform
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the FastAPI server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The backend API will run at `http://localhost:8000`. You can view the docs at `http://localhost:8000/docs`.

---

## 3. Frontend Setup (Next.js v14/16)

The frontend provides a premium "Black Theme" SaaS UI for managing cases and running the Agent demo scenarios.

1. **Navigate to the frontend directory**:
   ```bash
   cd ui/nextjs
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Start the Next.js development server**:
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:3000`.

---

## 4. (Optional) Infrastructure Setup

The SAR Platform is designed for graceful degradation. It will fall back to using in-memory databases and mocking if external services are not available, allowing you to run the demo instantly out-of-the-box.

However, for full persistence and graph relationships, you can spin up the supporting infrastructure using Docker:

```bash
docker-compose up -d
```
This will start Neo4j, PostgreSQL, Redis, and other supporting services in the background.

---

## 5. Running the Pipeline Demo

Once both the backend and frontend are running:

1. Open `http://localhost:3000` in your browser.
2. Navigate to the **Demo Center** (from the sidebar).
3. Click **Run All 3 Scenarios** to simulate end-to-end processing (Transaction -> Risk Score -> Groq Narrative -> Hash).
4. After completion, click **View Full Report** to see the 5-tab breakdown of the case.
5. In the **SAR Report** tab, test the **Download PDF** feature to get a beautifully formatted, text-based PDF containing the 8-part FIU-IND STR report.
