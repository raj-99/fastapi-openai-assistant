from psycopg import connect
from app.core.config import settings

def get_db_connection():
    conn = connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password
    )
    return conn