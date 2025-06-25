from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel
import aiomysql
from typing import List, Dict, Optional
import os
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Application Lifespan Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create connection pool
    app.state.pool = await aiomysql.create_pool(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        minsize=1,
        maxsize=10
    )
    yield
    # Shutdown: Close connection pool
    app.state.pool.close()
    await app.state.pool.wait_closed()

app = FastAPI(
    title="Genie Genie API",
    lifespan=lifespan,
    debug=os.getenv("APP_DEBUG", "False").lower() == "true"
)

# Define proper response model with Optional fields
class DocumentResponse(BaseModel):
    question: str
    answer: Optional[str] = ""
    link: Optional[str] = ""
    date: Optional[str] = ""

@app.get('/documents', response_model=List[DocumentResponse])
async def get_documents():
    try:
        async with app.state.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute('''
                    SELECT 
                        genie_question, 
                        genie_answer, 
                        genie_questiondate, 
                        genie_sourcelink 
                    FROM tbl_genie_genie
                ''')
                rows = await cursor.fetchall()
                
                documents = []
                for row in rows:
                    documents.append({
                        'question': row.get('genie_question') or "",
                        'answer': row.get('genie_answer') or "",
                        'link': row.get('genie_sourcelink') or "",
                        'date': str(row['genie_questiondate']) if row.get('genie_questiondate') else ""
                    })
                return documents
                
    except aiomysql.Error as e:
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

@app.get("/healthcheck")
async def healthcheck():
    """Endpoint to verify service is running"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)