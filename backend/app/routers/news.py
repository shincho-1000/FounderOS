from fastapi import APIRouter

router = APIRouter()

# GET    /fetch            - fetch latest news relevant to the business
# GET    /search           - search news by keyword/topic
# GET    /saved            - list saved news articles
# POST   /save             - save a news article for context
# DELETE /saved/{id}       - remove a saved article
