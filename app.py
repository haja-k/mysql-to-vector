from fastapi import FastAPI, HTTPException, Header
from dotenv import load_dotenv
from typing import List, Dict, Optional
import aiomysql, os

load_dotenv() 

app = FastAPI()

# MySQL configuration
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'db': os.getenv("DB_NAME"),
}

# Simple API key for security (replace with a strong key, e.g., `openssl rand -base64 32`)
API_KEY = os.getenv("APP_SECRET_KEY")

async def check_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or authorization != f'Bearer {API_KEY}':
        raise HTTPException(status_code=401, detail='Invalid or missing API key')

@app.get('/documents', response_model=List[Dict[str, str]])
async def get_documents(category: Optional[str] = None, authorization: Optional[str] = Header(None)):
    await check_api_key(authorization)

    try:
        # Create MySQL connection pool
        pool = await aiomysql.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # Query table (adjust column names as needed)
                query = 'SELECT id, genie_question, genie_answer, genie_questiondate, genie_sourcelink FROM tbl_genie_genie'
                params = []
                if category:
                    query += ' WHERE category = %s'
                    params.append(category)
                await cursor.execute(query, params)
                rows = await cursor.fetchall()

                # Format as documents for Dify
                documents = [
                    {
                        'question': row['genie_question'],
                        'answer': row['genie_answer']
                    } for row in rows
                ]

        pool.close()
        await pool.wait_closed()
        return documents

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database error: {str(e)}')