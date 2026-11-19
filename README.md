# Founder OS

> AI-powered operating system for startups — business intelligence, decision support, and long-term memory in one platform.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| AI / LLM | Google Gemini API |
| RAG / Indexing | LlamaIndex |
| Relational DB | PostgreSQL |
| Document DB | MongoDB |
| Frontend | React (Vite) |
| News Engine | newsdata.io / GDELT / DuckDuckGo |

## Project Structure

```
Founderos/
├── backend/
│   ├── app/
│   │   ├── routers/        # FastAPI route definitions
│   │   ├── controllers/    # Business logic handlers
│   │   ├── services/       # Core service layer (Gemini, memory, indexing)
│   │   ├── models/         # Pydantic schemas + ORM models
│   │   ├── db/             # Postgres & Mongo connection/session helpers
│   │   ├── memory/         # Short-term & long-term memory modules
│   │   ├── news/           # News scraping engine
│   │   └── utils/          # Shared utilities
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── store/
│   ├── package.json
│   └── Dockerfile
├── storage/                # LlamaIndex vector/index storage
├── docker-compose.yml
├── .env.example
└── README.md
```

## Getting Started

```bash
cp .env.example .env
# fill in your API keys in .env
docker-compose up --build
```

Backend runs at `http://localhost:8000`  
Frontend runs at `http://localhost:5173`  
API docs at `http://localhost:8000/docs`
