from fastapi import APIRouter

router = APIRouter()

# POST   /generate         - generate a full business insight report
# GET    /                 - list past insight reports
# GET    /{insight_id}     - get a specific insight report
