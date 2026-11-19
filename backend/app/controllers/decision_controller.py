# Orchestrates a decision query:
#   1. Fetch relevant long-term memory
#   2. Attach short-term context window
#   3. Fetch relevant news headlines
#   4. Query RAG index for relevant documents
#   5. Build composite prompt and call GeminiService
#   6. Persist decision to Postgres, store context snapshot in Mongo
