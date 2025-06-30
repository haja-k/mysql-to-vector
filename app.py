from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel
import aiomysql
from typing import List, Dict, Optional
import os
from contextlib import asynccontextmanager
import requests

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
    title="PVRA API",
    lifespan=lifespan,
    debug=os.getenv("APP_DEBUG", "False").lower() == "true"
)

# Define response model for original endpoint
class DocumentResponse(BaseModel):
    question: str
    answer: Optional[str] = ""
    link: Optional[str] = ""
    date: Optional[str] = ""

# Define response model for embeddings
class DocumentEmbeddingResponse(BaseModel):
    question: str
    answer: Optional[str] = ""
    link: Optional[str] = ""
    date: Optional[str] = ""
    question_embedding: List[float]
    answer_embedding: List[float]

# Helper function to get embeddings from external service
def get_embeddings(text: str, api_key: str) -> List[float]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    print('EMBEDDING_MODEL_HOST: ', os.getenv("EMBEDDING_MODEL_HOST"))
    data = {"model": os.getenv("EMBEDDING_MODEL_NAME"), "input": text}
    response = requests.post(
        os.getenv("EMBEDDING_MODEL_HOST"),
        headers=headers,
        json=data
    )
    response.raise_for_status()  # Raise an error for bad responses
    return response.json().get("embedding", [])  # Adjust based on actual response structure

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

@app.get('/documents/embeddings', response_model=List[DocumentEmbeddingResponse])
async def get_document_embeddings():
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
                api_key = os.getenv("EMBEDDING_API_KEY") 
                for row in rows:
                    question = row.get('genie_question') or ""
                    answer = row.get('genie_answer') or ""
                    print(question)
                    print('api key: ', api_key)
                    
                    # Get embeddings from external service
                    question_embedding = get_embeddings(question, api_key)
                    answer_embedding = get_embeddings(answer, api_key) if answer else []
                    
                    documents.append({
                        'question': question,
                        'answer': answer,
                        'link': row.get('genie_sourcelink') or "",
                        'date': str(row['genie_questiondate']) if row.get('genie_questiondate') else "",
                        'question_embedding': question_embedding,
                        'answer_embedding': answer_embedding
                    })
                return documents
                
    except aiomysql.Error as e:
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {str(e)}"
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