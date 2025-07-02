from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel
import aiomysql
import psycopg2
from typing import List, Dict, Optional
import os
from contextlib import asynccontextmanager
import requests
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Application Lifespan Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mysql_pool = await aiomysql.create_pool(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME", "db_ses"),
        minsize=1,
        maxsize=10
    )
    app.state.pgv_pool = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        database=os.getenv("PGVECTOR_DB_NAME")
    )
    app.state.pg_pool = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        database=os.getenv("PG_DB_NAME")
    )
    yield
    app.state.mysql_pool.close()
    await app.state.mysql_pool.wait_closed()
    app.state.pgv_pool.close()
    app.state.pg_pool.close()

app = FastAPI(
    title="PVRA API",
    lifespan=lifespan,
    debug=os.getenv("APP_DEBUG", "False").lower() == "true"
)

# Define response models
class DocumentResponse(BaseModel):
    question: str
    answer: Optional[str] = ""
    link: Optional[str] = ""
    date: Optional[str] = ""

# Helper function to get embeddings and ensure correct dimensionality
def get_embeddings(text: str, expected_dim: int = 4096) -> List[float]:
    host = os.getenv("EMBEDDING_MODEL_HOST")
    api_key = os.getenv("EMBEDDING_API_KEY")
    model_name = os.getenv("EMBEDDING_MODEL_NAME")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": model_name,
        "input": text
    }
    try:
        response = requests.post(
            f"{host}/embeddings",
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Embedding response: {result}")
        embedding = result.get("data", [{}])[0].get("embedding", [])
        if not embedding or len(embedding) != expected_dim:
            logger.warning(f"Embedding has wrong dimensions (got {len(embedding)}, expected {expected_dim}). Padding with zeros.")
            embedding = np.pad(embedding, (0, max(0, expected_dim - len(embedding))), mode='constant').tolist()
        return embedding
    except requests.exceptions.RequestException as e:
        logger.error(f"Embedding service error: {str(e)}, Response: {e.response.text if e.response else 'No response'}")
        # Return zero vector of expected dimension on failure
        return [0.0] * expected_dim

# Helper function to update embeddings in pgvector database
def update_embeddings_in_pgv(pgv_conn, question_id: int, question: str, answer: str):
    question_embedding = get_embeddings(question)
    answer_embedding = get_embeddings(answer) if answer else get_embeddings("")
    
    logger.debug(f"Updating embeddings - question_id: {question_id}, question_embedding length: {len(question_embedding)}, answer_embedding length: {len(answer_embedding)}")
    
    with pgv_conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE genie_documents
            SET question_embedding = %s::vector, answer_embedding = %s::vector
            WHERE id = %s
            """,
            (question_embedding, answer_embedding, question_id)
        )
    pgv_conn.commit()

@app.get('/documents')
async def get_documents():
    try:
        async with app.state.mysql_pool.acquire() as conn:
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
            detail="MySQL service unavailable"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

@app.post('/documents/sync-embeddings')
async def sync_embeddings():
    try:
        # Get the last migrated ID from PostgreSQL with transaction handling
        last_migrated_id = 0
        with app.state.pg_pool.cursor() as pg_cursor:
            try:
                pg_cursor.execute("SELECT COALESCE(MAX(id_migrated), 0) FROM migration_tracker")
                last_migrated_id = pg_cursor.fetchone()[0]
            except psycopg2.Error as e:
                logger.error(f"Permission or table error on migration_tracker: {str(e)}")
                app.state.pg_pool.rollback()  # Rollback to clear aborted state
                raise HTTPException(
                    status_code=503,
                    detail=f"Permission denied or table migration_tracker missing: {str(e)}"
                )

        async with app.state.mysql_pool.acquire() as mysql_conn:
            async with mysql_conn.cursor(aiomysql.DictCursor) as mysql_cursor:
                # Fetch rows from MySQL based on the last migrated ID from PostgreSQL
                await mysql_cursor.execute("""
                    SELECT id, genie_question, genie_answer, genie_questiondate, genie_sourcelink
                    FROM tbl_genie_genie
                    WHERE id > %s
                """, (last_migrated_id,))
                rows = await mysql_cursor.fetchall()

        # Use pre-existing PostgreSQL connections from app state
        pgv_conn = app.state.pgv_pool
        pg_conn = app.state.pg_pool

        try:
            if not rows:
                return {"status": "success", "synced": 0, "message": "No new rows to sync."}

            # Check existing questions in PostgreSQL to avoid duplicates
            existing_questions = set()
            with pgv_conn.cursor() as pgv_cursor:
                try:
                    pgv_cursor.execute("SELECT question FROM genie_documents")
                    existing_questions = {row[0] for row in pgv_cursor.fetchall()}
                except psycopg2.Error as e:
                    logger.error(f"Permission error on genie_documents: {str(e)}")
                    pgv_conn.rollback()
                    raise HTTPException(
                        status_code=503,
                        detail=f"Permission denied for table genie_documents: {str(e)}"
                    )

            for row in rows:
                question = row.get('genie_question') or ""
                if question in existing_questions:
                    continue  # Skip if question already exists

                answer = row.get('genie_answer') or ""

                with pgv_conn.cursor() as pgv_cursor:
                    try:
                        pgv_cursor.execute(
                            """
                            INSERT INTO genie_documents (question, answer, link, date)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (question) DO UPDATE SET date = EXCLUDED.date
                            RETURNING id
                            """,
                            (question, answer, row.get('genie_sourcelink'), row['genie_questiondate'])
                        )
                        question_id = pgv_cursor.fetchone()[0]
                    except psycopg2.Error as e:
                        logger.error(f"Insert error on genie_documents: {str(e)}")
                        pgv_conn.rollback()
                        raise HTTPException(
                            status_code=503,
                            detail=f"Insert error on genie_documents: {str(e)}"
                        )

                update_embeddings_in_pgv(pgv_conn, question_id, question, answer)

            with pg_conn.cursor() as pg_cursor:
                pg_cursor.execute(
                    """
                    INSERT INTO migration_tracker (id_migrated)
                    VALUES (%s)
                    ON CONFLICT (id) DO UPDATE SET id_migrated = EXCLUDED.id_migrated
                    """,
                    (rows[-1]['id'],)
                )
            pg_conn.commit()
            pgv_conn.commit()
            return {"status": "success", "synced": len(rows)}
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL query error: {str(e)}")
            pgv_conn.rollback()
            pg_conn.rollback()
            raise HTTPException(
                status_code=503,
                detail=f"PostgreSQL query error: {str(e)}"
            )
        finally:
            # Connections are managed by lifespan, no need to close here
            pass

    except aiomysql.Error as e:
        logger.error(f"MySQL service unavailable: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"MySQL service unavailable: {str(e)}"
        )
    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"PostgreSQL connection error: {str(e)}"
        )
    except requests.RequestException as e:
        logger.error(f"Embedding service unavailable: {str(e.response.text) if hasattr(e, 'response') and e.response else str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {str(e.response.text) if hasattr(e, 'response') and e.response else str(e)}"
        )
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

@app.get("/healthcheck")
async def healthcheck():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)