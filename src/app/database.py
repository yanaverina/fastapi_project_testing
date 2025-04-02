import asyncpg
from fastapi import HTTPException
import os

async def get_connection():
    try:
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "test_user"),
            password=os.getenv("DB_PASSWORD", "test_password"),
            database=os.getenv("DB_NAME", "test_db"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )
        
