from fastapi import FastAPI, Request, HTTPException
from ingestion import ingestData
from cache import checkCache
from response_generation import generateResponse
from contextlib import asynccontextmanager
from cache import init_db
import logging


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
app = FastAPI(lifespan=lifespan)


@app.post("/hackrx/run")
async def receive_webhook(request: Request):
    data = await request.json()

    url = data.get("documents")
    questions = data.get("questions")
    
    check,document_hash = await ingestData(url)
    if check:
        logging.info("Data ingestion complete. Generating responses ...")
        answers,unanswered = await checkCache(document_hash,questions)
    else:
        logging.error("Data ingestion failed")
        raise HTTPException(status_code=500, detail="data ingestion failed")
    
    not_cached = [i for i, result in enumerate(answers) if result is None]
    if not_cached:
        logging.info(f"Answers for questions {not_cached} weren't in cache. Generating answers ...")
        generated_answers = await generateResponse(url,document_hash,unanswered)
        if generated_answers:
            logging.info("Answer generation successful")
            for i, ans in enumerate(answers):
                if ans is None:
                    answers[i] = generated_answers[i]
            return {"answers":answers}
        else:
            logging.error("Answer generation failed")
        raise HTTPException(status_code=500, detail="answer generation failed")
    else:
        logging.info("Answers found in cache. Skipping generation ...")
        return {"answers":answers}
        