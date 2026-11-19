from fastapi import APIRouter

router = APIRouter()

# GET    /short-term       - retrieve current short-term memory window
# GET    /long-term        - retrieve long-term memory entries
# POST   /long-term        - manually add a long-term memory entry
# DELETE /long-term/{id}   - remove a long-term memory entry
# POST   /search           - semantic search across memory
