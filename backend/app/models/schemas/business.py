"""
Pydantic schemas for business profiles.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BusinessCreate(BaseModel):
    name: str
    industry: str
    stage: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[str] = None
    location: Optional[str] = None


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[str] = None
    location: Optional[str] = None


class BusinessOut(BaseModel):
    id: str
    user_id: str
    name: str
    industry: str
    stage: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
