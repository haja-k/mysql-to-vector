## Vectorizing MySQL Data For LLM

### Getting Started
- Create environment file named .env and update the variables accordingly as shown in .env.example file
- To run the API: ``` run.bat ```
- Open new terminal and try curl: ``` curl -H "Authorization: Bearer <your app secret code>" http://127.0.0.1:5000/documents ```
- Check embedding model's customd eployment: ```curl -X POST http://172.26.x.x:x/v1/embeddings -H "Content-Type: application/json" -H "Authorization: Bearer your_actual_api_key" -d "{\"model\": \"Qwen/Qwen3-Embedding-8B\", \"input\": \"Hello\"}"```

### Good to know
- The embedding model has been hosted somewhere else, not using existing open source api to get the models
- I am using Qwen/Qwen3-Embedding-8B embedding model for this codebase

### How this works 
``` diff 
! In progress, might update from time to time bcs I am still researching. 
```
#### Problem statement:
- I have client's MySQL database schema hosted in other server that is intended to become their chatbot knowledge base. 
- I am using Dify to orchestrate the chatbot workflow but Dify's knowledge base is static, unchanged data while my client's data is going to be updated through their web platform from time to time.

#### Proposed solution
- Hence, I am thinking of making an API node inside my Dify workflow orchestration. This API will act just like the 'Knowledge Retrieval' node in my Dify, passing the embedded data chunk to the next LLM node. 
- I need to make sure the data retireved from client's database is readable by LLM so it can process response to user queries properly.

#### Current flow:
MySQL > Postgres PGVector > Dify Integration