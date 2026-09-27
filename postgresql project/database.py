import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL or "YOUR_POSTGRES_PASSWORD" in DATABASE_URL or "placeholder" in DATABASE_URL.lower():
        raise ValueError("DATABASE_URL is absent, a placeholder, or invalid.")
    
    # Try parsing URL first to avoid leaking credentials if an error occurs
    try:
        parsed = urlparse(DATABASE_URL)
        # If parsing works, connect via the URL or parameters
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        # Sanitize any potential credential leak in the error message
        raise RuntimeError("Failed to connect to PostgreSQL. Please check your DATABASE_URL configuration.")

def test_connection():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        print("PostgreSQL connected successfully!")
        return True
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        test_connection()
    except Exception as e:
        print(f"Configuration Error: {e}")
