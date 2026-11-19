"""
Pydantic schemas for business profiles.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip whitespace; turn empty strings into None."""
    if value is None:
        return None
    value = value.strip()
    return value or None


class BusinessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Acme AI"])
    industry: str = Field(..., min_length=1, max_length=255, examples=["B2B SaaS"])
    stage: Optional[str] = Field(None, max_length=100, examples=["seed"])
    size: Optional[str] = Field(None, max_length=100, examples=["1-10"])
    description: Optional[str] = Field(None, max_length=5000)
    goals: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=255)

    @field_validator("name", "industry")
    @classmethod
    def _required_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("stage", "size", "description", "goals", "location")
    @classmethod
    def _optional_clean(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v)


class BusinessUpdate(BaseModel):
    """Partial update: only fields sent by the client are changed."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, min_length=1, max_length=255)
    stage: Optional[str] = Field(None, max_length=100)
    size: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)
    goals: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=255)

    @field_validator("name", "industry")
    @classmethod
    def _required_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("stage", "size", "description", "goals", "location")
    @classmethod
    def _optional_clean(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v)


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
