# Long-term memory: persistent facts and learnings about the business
# Stored in MongoDB, vector-searchable via LlamaIndex embeddings
# - add(business_id, content: str, metadata: dict)
# - search(business_id, query: str, top_k: int) -> list[MemoryEntry]
# - delete(memory_id)
