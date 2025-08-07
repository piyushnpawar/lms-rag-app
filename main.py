from fastapi import FastAPI, Request
from ingestion import ingestData

app = FastAPI()

@app.post("/hackrx/run")
async def receive_webhook(request: Request):
    data = await request.json()

    url = data.get("documents")
    ingestData(url)
    
    print(data.get("questions"))
    return {"message": "Webhook received!"}
