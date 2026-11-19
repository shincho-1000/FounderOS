# Short-term memory: sliding window of recent conversation turns
# Stored in MongoDB (TTL-indexed collection)
# - get_window(session_id) -> list[MemoryEntry]
# - append(session_id, entry: MemoryEntry)
# - clear(session_id)
