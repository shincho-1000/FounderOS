# Orchestrates full insight report generation:
#   1. Pull memory + recent decisions
#   2. Fetch relevant news
#   3. Query documents
#   4. Call GeminiService with unified prompt
#   5. Persist insight report
