import hashlib, asyncio
from sqlalchemy import Column, String, Text, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import os

Base = declarative_base()

class QAEntry(Base):
    __tablename__ = "qa_entries"
    document_hash = Column(String, primary_key=True)
    question_hash = Column(String, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

async def get_answer(document_hash: str, question_hash: str):
    async with AsyncSessionLocal() as session:
        stmt = select(QAEntry).filter_by(document_hash=document_hash, question_hash=question_hash)
        result = await session.execute(stmt)
        response =  result.scalars().first()
        return response

async def add_qa_entry(document_hash: str, question: str, answer: str):
    question_hash = hash_text(question)
    async with AsyncSessionLocal() as session:
        entry = QAEntry(
            document_hash=document_hash,
            question_hash=question_hash,
            question=question,
            answer=answer
        )
        session.add(entry)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return None
        return entry

async def update_answer(document_hash: str, question_hash: str, new_answer: str):
    async with AsyncSessionLocal() as session:
        stmt = select(QAEntry).filter_by(document_hash=document_hash, question_hash=question_hash)
        result = await session.execute(stmt)
        entry = result.scalars().first()
        if entry:
            entry.answer = new_answer
            await session.commit()
            return True
        return False

async def checkCache(document_hash: str, questions) -> tuple[list,list]:
    answers = []
    unanswered = []
    for i, q in enumerate(questions):
        q_hash = hash_text(q)
        print(f"\nQuestion {i+1}: {q}")
        response = await get_answer(document_hash,q_hash)
        if response:
            print(f"Answer: {response.answer}")
            print("-----------------------------------")
            answers.append(response.answer)
            unanswered.append("Cached")
        else:
            print("No answer in cache")
            print("-----------------------------------")
            unanswered.append(q)
            answers.append(None)
            
    return answers,unanswered