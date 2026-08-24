from fastapi import FastAPI
from pydantic import BaseModel
from main import answer_question

app = FastAPI()

class Q(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Q):
    return {"answer": answer_question(q.question)}