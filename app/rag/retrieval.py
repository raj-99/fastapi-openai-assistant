from pgvector import Vector
from app.core.db import get_db_connection

def retrieve_top_k(query_vector: list[float], top_k: int = 5):
    sql = """
SELECT id, source, chunk_index, content,
       1 - (embedding <=> %s) AS score
FROM documents
ORDER BY embedding <=> %s
LIMIT %s;
"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (Vector(query_vector), Vector(query_vector), top_k))
            rows = cur.fetchall()
    
    return [
        {
            "id": row[0], 
            "source": row[1],
            "chunk_index": row[2],
            "content": row[3], 
            "score": float(row[4]) if row[4] is not None else 0.0,
        } 
        for row in rows
    ]