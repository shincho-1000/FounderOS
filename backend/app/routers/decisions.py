from fastapi import APIRouter

router = APIRouter()

# POST   /query            - ask Gemini for a business decision
# GET    /history          - get past decisions for the business
# GET    /{decision_id}    - get a specific decision
# DELETE /{decision_id}    - remove a decision from history
