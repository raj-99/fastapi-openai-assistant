from psycopg import connect
from app.core.config import settings
from pgvector.psycopg import register_vector

def get_db_connection():
    conn = connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password
    )
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        create_table_query = """CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY,source TEXT,chunk_index INT NOT NULL,content TEXT NOT NULL,metadata JSONB,embedding VECTOR(1536));"""
        cur.execute(create_table_query)
    conn.commit()
    register_vector(conn)
    return conn