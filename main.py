from fastapi import FastAPI, Request, HTTPException
from ingestion import ingestData
from response_generation import generateResponse
import logging


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

app = FastAPI()

@app.post("/hackrx/run")
async def receive_webhook(request: Request):
    data = await request.json()

    url = data.get("documents")
    questions = data.get("questions")
    
    check,document_hash = await ingestData(url)
    if check:
        logging.info("Data ingestion complete. Generating responses ...")
        answers = await generateResponse(url,document_hash,questions)
    else:
        logging.error("Data ingestion failed")
        raise HTTPException(status_code=500, detail="data ingestion failed")

    if answers:
        logging.info("Answer generation successful")
        return {"answers":answers}
    else:
        logging.error("Answer generation failed")
        raise HTTPException(status_code=500, detail="answer generation failed")