"""
Postgres backward-compatibility shim pointing to database.py
"""
from app.db.database import Base, SessionLocal, get_db, init_db, engine

__all__ = ["Base", "SessionLocal", "get_db", "init_db", "engine"]
