from fastapi import FastAPI
from pydantic import BaseModel
from main import answer_question
from fastapi.responses import HTMLResponse

app = FastAPI()

class Q(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Q):
    return {"answer": answer_question(q.question)}


PAGE = """
<!doctype html>
<html lang="th">
<head><meta charset="utf-8"><title>Thai RAG</title>
<style>
 body{font-family:sans-serif;max-width:640px;margin:60px auto;padding:0 16px}
 textarea{width:100%;height:80px;font-size:16px;padding:8px}
 button{margin-top:8px;padding:8px 20px;font-size:16px}
 #out{margin-top:24px;padding:16px;background:#f4f4f4;border-radius:6px;
      white-space:pre-wrap;min-height:40px}
</style></head>
<body>
<h2>ถามเกี่ยวกับสงครามโลกครั้งที่ 1</h2>
<textarea id="q" placeholder="ซาราเจโวเป็นเมืองหลวงของจังหวัดใด"></textarea>
<button onclick="ask()">ถาม</button>
<div id="out"></div>
<script>
async function ask(){
  const out = document.getElementById('out');
  out.textContent = 'กำลังคิด...';
  const r = await fetch('/ask', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({question: document.getElementById('q').value})
  });
  const d = await r.json();
  out.textContent = d.answer;
}
</script>
</body></html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE