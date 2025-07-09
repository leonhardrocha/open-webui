curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjdjNjAyZDMyLTI4ZDUtNGYyMi1hYzQzLTc0YWNkODA1MTMzNSJ9.Mt32lWdOSttCfFHyDF46jPR5JlK76qK5aoDBPUp5cPA" \
-X POST http://localhost:3000/api/chat/completions \
-d '{
      "model": "llama3.1",
      "messages": [
        {
          "role": "user",
          "content": "Why is the sky blue?"
        }
      ]
    }'