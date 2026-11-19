"""
Memory router: declares routes and dependencies only; logic lives in the controller.
Everything is scoped to the authenticated user's business.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Response, status

from app.controllers.memory_controller import MemoryController
from app.models.schemas.memory import (
    LongTermEntryCreate,
    LongTermEntryOut,
    MemoryCategory,
    MemoryContext,
    MemorySummaryOut,
    ShortTermEntryOut,
)

router = APIRouter()

BusinessId = Depends(MemoryController.require_business_id)


@router.get("/short-term", response_model=list[ShortTermEntryOut],
            summary="Recent interactions (chronological)")
async def get_short_term(business_id: str = BusinessId):
    return await MemoryController.get_short_term(business_id)


@router.delete("/short-term", status_code=status.HTTP_204_NO_CONTENT,
               summary="Reset conversation: clears short-term memory and summary")
async def reset_conversation(business_id: str = BusinessId):
    await MemoryController.reset_conversation(business_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=MemorySummaryOut,
            summary="Rolling summary of older interactions")
async def get_summary(business_id: str = BusinessId):
    return await MemoryController.get_summary(business_id)


@router.get("/long-term", response_model=list[LongTermEntryOut],
            summary="List long-term memory (optionally by category)")
async def list_long_term(
    category: Optional[MemoryCategory] = None,
    business_id: str = BusinessId,
):
    return await MemoryController.list_long_term(business_id, category)


@router.post("/long-term", response_model=LongTermEntryOut,
             status_code=status.HTTP_201_CREATED,
             summary="Add a long-term memory entry (deduplicated)")
async def add_long_term(
    data: LongTermEntryCreate,
    business_id: str = BusinessId,
):
    return await MemoryController.add_long_term(business_id, data)


@router.delete("/long-term/{entry_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a long-term memory entry")
async def delete_long_term(entry_id: str, business_id: str = BusinessId):
    await MemoryController.delete_long_term(business_id, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/context", response_model=MemoryContext,
            summary="Exactly what the LLM will see (all three tiers)")
async def get_context(business_id: str = BusinessId):
    return await MemoryController.get_context(business_id)
