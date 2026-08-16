# First-Thai-RAG 

A Retrieval-Augmented Generation (RAG) pipeline built from scratch for **Thai-language documents**.

Most RAG tutorials assume English text. Thai breaks several of their assumptions — there are no spaces between words, no sentence-ending punctuation, and characters carry combining marks that must never be separated from their base. This project handles those cases explicitly.

## Architecture

```
Thai .txt documents
        │
        ▼
  split_thai()          paragraph-aware chunking, combining-mark safe
        │
        ▼
  OpenAI embeddings     text-embedding-3-small
        │
        ▼
  ChromaDB              persistent vector store on disk
        │
        ▼
  similarity search     top-N nearest chunks for a question
        │
        ▼
  gpt-4o-mini           answers grounded in the retrieved chunks
```

**Two phases:**

- **Indexing** (run once): load → chunk → embed → store in ChromaDB.
- **Querying** (run per question): embed the question → retrieve nearest chunks → build a grounded prompt → generate the answer.

## Keyword-based 
evaluation is unreliable for Thai because register shifts (ราชาศัพท์) change vocabulary for the same fact — this motivated moving toward LLM-as-judge scoring.




## Setup

```bash
git clone https://github.com/This-PT/First-Thai-RAG.git
cd First-Thai-RAG

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-your-key-here
```

Place your Thai `.txt` documents in the data directory, then:

```bash
python main.py index  | for loading,chunking and embedding 
python main.py ask "question"  | for asing question 
python eval/run_eval.py  |  for run eval
rmdir /s chroma_persistent_storage | for clearing old embedding
```


## Findings

gpt-3.5-turbo produces malformed Thai. Early output contained broken Thai words. Checking the retrieved chunks showed they were clean, isolating the fault to generation rather than retrieval. Switching to gpt-4o-mini resolved it — and costs less.




## evaluate results



## Results

**Tuned configuration:** `max_chars=1200`, `overlap_paras=1`, `n_results=10`

Arrived at by sweeping one parameter at a time against a fixed 15-question evaluation set.

### Chunk size (overlap_paras=1, n_results=5)

| max_chars | Retrieval | Answer |
|---|---|---|
| 600 | 8/15 (53%) | 8/15 (53%) |
| **1200** | **12/15 (80%)** | **10/15 (67%)** |
| 1800 | 12/15 (80%) | 10/15 (67%) |
| 2500 | 11/15 (73%) | 11/15 (73%) |

600 is clearly too small — fragments produce embeddings that don't represent a complete idea, so the right chunk never surfaces. At 2500 the tradeoff inverts: retrieval degrades because larger chunks average into blurrier vectors, while answer quality improves because a retrieved chunk carries more context.

### Paragraph overlap (max_chars=1200, n_results=5)

| overlap_paras | Retrieval | Answer |
|---|---|---|
| **1** | **12/15 (80%)** | **10/15 (67%)** |
| 3 | 11/15 (73%) | 9/15 (60%) |
| 5 | 11/15 (73%) | 8/15 (53%) |

More overlap made everything worse, with answer accuracy degrading faster than retrieval. Overlap creates near-duplicate chunks, so the top-N slots fill with repeats of the same content — crowding out genuinely different chunks and diluting the prompt.

### Retrieved chunks (max_chars=1200, overlap_paras=1)

| n_results | Retrieval | Answer |
|---|---|---|
| 3 | 12/15 (80%) | 10/15 (67%) |
| 5 | 12/15 (80%) | 10/15 (67%) |
| **10** | **12/15 (80%)** | **11/15 (73%)** |
| 15 | 13/15 (87%) | 11/15 (73%) |

Retrieval is nearly flat from 3 to 10 — the most diagnostic result here. The failing questions aren't ranked slightly too low; their correct chunk is absent from the top ten entirely. Retrieving *more* won't fix them, retrieving *better* will, which motivates hybrid search and reranking. `n_results=15` buys one retrieval hit and no answer improvement while nearly doubling prompt size, so 10 is the better operating point.

### Caveats

- **n = 15**, so one question is 6.7% — single-question differences are noise. The data strongly supports only that 600 is worse than 1200+; the overlap trend is suggestive because it's monotonic across three settings.
- **The negative case structurally fails the retrieval check.** Its expected keyword (`ไม่ทราบ`) can't appear in retrieved Thai chunks, so it counts as a retrieval miss every run. The achievable ceiling is 14/15, making the best result 13/14 (93%) rather than 87%.



overall best setup =  chunk_size = 1200 / overlaps = 1/N_RESULTS = 10