from fastapi import APIRouter

router = APIRouter()

# POST   /upload           - upload and index a document (PDF, DOCX, TXT)
# GET    /                 - list uploaded documents
# DELETE /{document_id}    - remove a document and its index
# POST   /query            - RAG query against indexed documents
