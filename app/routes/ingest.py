import uuid
from fastapi import APIRouter, HTTPException
from app.schemas import IngestTextRequest, IngestTextResponse
from app.core.db import get_db_connection
from app.rag.embeddings import embed_texts
from app.rag.chunking import chunk_text

router = APIRouter()

@router.post("/ingest/text", response_model=IngestTextResponse)
def ingest_text(request: IngestTextRequest) -> IngestTextResponse:
    doc_id = str(uuid.uuid4())
    
    # Step 1: Chunk the text
    chunks = chunk_text(request.text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No content to ingest.")
    
    # Step 2: Generate embeddings for each chunk
    vectors = embed_texts(chunks)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                cur.execute(
                    """
                    INSERT INTO documents (id, source, chunk_index, chunk_text, metadata, embedding)
                    """,
                    (f"{doc_id}:{i}", request.source, i, chunk, request.metadata, vector)
                )
    return IngestTextResponse(document_id=doc_id, chunks_created=len(chunks))