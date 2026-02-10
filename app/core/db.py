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
    register_vector(conn)
    return conn