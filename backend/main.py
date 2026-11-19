from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import (
    auth,
    business,
    decisions,
    documents,
    memory,
    news,
    insights,
)

app = FastAPI(
    title="Founder OS API",
    description="AI-powered business operating system for startups",
    version="0.1.0",
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
