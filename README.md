### Vectorizing MySQL Data For LLM

#### Getting Started
- Create environment file named .env and update the variables accordingly as shown in .env.example file
- To run the API: ``` run.bat ```
- Open new terminal and try curl: ``` curl -H "Authorization: Bearer <your app secret code>" http://127.0.0.1:5000/documents ```
- Check embedding model's customd eployment: ```curl -X POST http://172.26.x.x:x/v1/embeddings -H "Content-Type: application/json" -H "Authorization: Bearer your_actual_api_key" -d "{\"model\": \"Qwen/Qwen3-Embedding-8B\", \"input\": \"Hello\"}"```

#### Good to know
- The embedding model has been hosted somewhere else, not using existing open source api to get the models