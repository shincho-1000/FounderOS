from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import init_db
from app.db.mongo import connect_mongo, close_mongo
from app.routers import (
    auth,
    business,
    decisions,
    documents,
    memory,
    news,
    insights,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── Startup ──
    print("🚀 Starting Founder OS API...")

    # SQLite: create tables
    await init_db()
    print("✅ SQLite database initialised — tables created.")

    # MongoDB Atlas: connect
    try:
        await connect_mongo()
    except Exception as e:
        print(f"⚠️  MongoDB connection failed (non-fatal): {e}")

    yield

    # ── Shutdown ──
    await close_mongo()
    print("👋 Founder OS API shut down.")


app = FastAPI(
    title="Founder OS API",
    description="AI-powered business operating system for startups",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(business.router, prefix="/api/v1/business", tags=["Business"])
app.include_router(decisions.router, prefix="/api/v1/decisions", tags=["Decisions"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(news.router, prefix="/api/v1/news", tags=["News"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["Insights"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": "Founder OS API"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
