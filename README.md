# 🚀 PVRA API: Vectorizing MySQL Data For LLM

A FastAPI-based service that transforms your MySQL database into a powerful vector search engine for AI applications using pgvector and embeddings.

## 📋 Table of Contents
- [🎯 Overview](#-overview)
- [🛠️ Installation](#️-installation)
- [⚙️ Configuration](#️-configuration)
- [🔗 API Endpoints](#-api-endpoints)
- [💡 Usage Examples](#-usage-examples)
- [🔌 Dify Integration](#-dify-integration)
- [🔧 Troubleshooting](#-troubleshooting)

## 🎯 Overview

### Problem Statement
Your client's MySQL database contains dynamic content that needs to power a chatbot, but traditional knowledge bases are static and don't sync with live data updates.

### Solution Architecture
```
MySQL Database → PostgreSQL + pgvector → Dify Workflow → AI Chatbot
```

### Key Features
- 🔄 **Real-time sync** between MySQL and PostgreSQL
- 🔍 **Vector similarity search** using embeddings
- 🤖 **Dify integration** through API nodes
- 📊 **Custom embedding model** (Qwen/Qwen3-Embedding-8B)

## 🛠️ Installation

### Prerequisites
| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8+ | Runtime environment |
| MySQL | Any | Source database |
| PostgreSQL | Latest | Vector database |
| pgvector | Latest | Vector extension |
| Embedding API | Compatible | Text embeddings |

### Quick Start
1. **Clone and setup:**
```bash
git clone <your-repo>
cd pvra-api
pip install -r requirements.txt
```

2. **Install dependencies:**
```bash
pip install fastapi uvicorn aiomysql psycopg2-binary python-dotenv pydantic requests numpy
```

3. **Run the API:**
```bash
run.bat
# or
python main.py
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file with the following configuration:

```env
# 🗄️ MySQL Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=db_ses

# 🐘 PostgreSQL Configuration
PG_HOST=localhost
PG_PORT=5432
PG_USER=your_pg_user
PG_PASSWORD=your_pg_password
PGVECTOR_DB_NAME=your_pgvector_db
PG_DB_NAME=your_pg_db

# 🧠 Embedding Service Configuration
EMBEDDING_MODEL_HOST=https://api.openai.com/v1
EMBEDDING_API_KEY=your_api_key
EMBEDDING_MODEL_NAME=text-embedding-3-large

# ⚙️ Application Configuration
APP_DEBUG=false
```

### Database Schema

**MySQL Source Table (`tbl_genie_genie`)**
```sql
CREATE TABLE tbl_genie_genie (
    id INT PRIMARY KEY AUTO_INCREMENT,
    genie_question TEXT,
    genie_answer TEXT,
    genie_questiondate DATE,
    genie_sourcelink TEXT
);
```

**PostgreSQL Vector Table (`genie_documents`)**
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE genie_documents (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    answer TEXT,
    link TEXT,
    date DATE,
    question_embedding vector(4096),
    answer_embedding vector(4096)
);

CREATE TABLE migration_tracker (
    id SERIAL PRIMARY KEY,
    id_migrated INTEGER
);
```

## 🔗 API Endpoints

| Endpoint | Method | Description | Use Case |
|----------|--------|-------------|----------|
| `/healthcheck` | GET | Health status | Monitoring |
| `/documents` | GET | All documents | Data overview |
| `/documents/sync-embeddings` | POST | Sync & embed | Data updates |
| `/search` | POST | Detailed search | Full results |
| `/search-simple` | POST | Simple search | Dify integration |

### 🔍 Search Endpoints Details

#### `/search` - Detailed Search
**Request:**
```json
{
  "query": "government policies",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "question": "What are the current government policies?",
      "answer": "The government has implemented several policies...",
      "link": "https://example.com/policies",
      "date": "2024-01-10",
      "similarity_score": 0.85
    }
  ],
  "total_results": 1
}
```

#### `/search-simple` - Dify-Optimized Search
**Request:**
```json
{
  "query": "healthcare system",
  "limit": 3,
  "similarity_threshold": 0.8
}
```

**Response:**
```json
{
  "context": "Result 1:\nQuestion: How does the healthcare system work?\nAnswer: The healthcare system operates through...\nSource: https://example.com/healthcare\nDate: 2024-01-10\nRelevance: 0.850\n\nResult 2:\n...",
  "sources": [
    {
      "question": "How does the healthcare system work?",
      "link": "https://example.com/healthcare",
      "date": "2024-01-10",
      "similarity_score": 0.85
    }
  ],
  "total_results": 1
}
```

## 💡 Usage Examples

### Testing with cURL

**Health Check:**
```bash
curl -X GET http://localhost:5000/healthcheck
```

**Search Documents:**
```bash
curl -X POST http://localhost:5000/search-simple \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the capital of Malaysia?",
    "limit": 5,
    "similarity_threshold": 0.7
  }'
```

**Sync Embeddings:**
```bash
curl -X POST http://localhost:5000/documents/sync-embeddings \
  -H "Content-Type: application/json"
```

### Testing with Postman

1. **Create new POST request**
2. **Set URL:** `http://localhost:5000/search-simple`
3. **Add header:** `Content-Type: application/json`
4. **Body (raw JSON):**
```json
{
  "query": "your search query here",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

## 🔌 Dify Integration

### Workflow Configuration

**Step 1: Add API Node**
- **URL:** `http://your-server:5000/search-simple`
- **Method:** POST
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "query": "{{user_query}}",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

**Step 2: Configure LLM Node**
```
Based on the following knowledge base information:
{{api_node.context}}

Please answer the user's question: {{user_query}}

Sources: {{api_node.sources}}
```

### Workflow Flow
```
User Input → API Node (search-simple) → LLM Node → Response
```

## 🔧 Troubleshooting

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Connection Error | `MySQL service unavailable` | ✅ Check MySQL server & credentials |
| Embedding Error | `Embedding service unavailable` | ✅ Verify API key & service URL |
| Search Error | `Database search error` | ✅ Check pgvector extension & table |
| No Results | Empty search results | ✅ Lower similarity threshold |

### Performance Optimization

| Parameter | Recommended Value | Impact |
|-----------|-------------------|---------|
| `similarity_threshold` | 0.5-0.7 | Lower = more results |
| `limit` | 3-10 | Higher = slower response |
| Vector dimensions | 4096 | Match your embedding model |

### Debug Checklist
- [ ] Check server logs for detailed errors
- [ ] Test `/healthcheck` endpoint
- [ ] Verify database connections
- [ ] Test embedding service manually
- [ ] Confirm data exists in both databases

## 📊 API Response Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | ✅ Success | Request completed successfully |
| 422 | ⚠️ Validation Error | Invalid request body |
| 500 | ❌ Server Error | Internal server error |
| 503 | 🔴 Service Unavailable | Database/service down |

## 🔐 Security Best Practices

- 🔒 Use environment variables for sensitive data
- 🛡️ Implement rate limiting in production
- 🔑 Add authentication for protected endpoints
- ✅ Validate all input data
- 🌐 Use HTTPS in production

## 📝 Technical Notes

### Embedding Model
- **Model:** Qwen/Qwen3-Embedding-8B
- **Dimensions:** 4096
- **Hosting:** Custom deployment (not open source API)

### Current Status
- ✅ Core functionality complete
- 🔄 Dify integration in progress
- 📊 Performance optimization ongoing

## 🆘 Support

If you encounter issues:
1. 📖 Check the troubleshooting section
2. 🔍 Review server logs for detailed errors
3. ⚙️ Verify environment variables
4. 🧪 Test individual components

---

**Made with ❤️ for dynamic AI knowledge bases**