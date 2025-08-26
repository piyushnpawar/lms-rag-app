from fastapi import FastAPI, Request,Response, HTTPException
from ingestion import ingestData
from cache import checkCache
from response_generation import generateResponse
from lms_handling import logIn, logOut, fetchFiles
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


@app.post("/login")
async def loginToLMS(request: Request, response:Response):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    status_code, subjects, logout_url = logIn(username,password)
    response.status_code = status_code
    return {
        "status": status_code,
        "subjects": subjects,
        "logout_url": logout_url
    }

@app.get("/logout")
def logoutOfLMS(response:Response):
    status_code = logOut()
    response.status_code = status_code
    return {}

@app.post("/fetch")
async def fetchSubjectFiles(request: Request, response: Response):
    data = await request.json()
    subject = data.get("subject")
    subject_url = data.get("url")
    status_code,files = fetchFiles(subject,subject_url)
    response.status_code = status_code
    return {"files": files}

@app.post("/upload")
async def receive_file(request: Request):
    data = await request.json()
    subject = data.get("subject")
    file_name = data.get("file_name")
    file_link = data.get("file_link")
    
    status = await ingestData(subject,file_name,file_link)
    return {"status": status}

@app.post("/query")
async def query_llm(request: Request):
    data = await request.json()
    questions = data.get("questions")
    answers,unanswered = await checkCache(questions)
    not_cached = [i for i, result in enumerate(answers) if result is None]
    if not_cached:
        logging.info(f"Answers for questions {not_cached} weren't in cache. Generating answers ...")
        generated_answers = await generateResponse(unanswered)
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