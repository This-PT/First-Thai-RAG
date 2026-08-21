# First-Thai-RAG 

A Retrieval-Augmented Generation (RAG) pipeline built from scratch for **Thai-language documents**.

Most RAG tutorials assume English text. Thai breaks several of their assumptions — there are no spaces between words, no sentence-ending punctuation, and characters carry combining marks that must never be separated from their base. This project handles those cases explicitly.


**Current results** — 19-question eval set (14 answerable, 5 not in the corpus):

| retriever | retrieval | answer | refusal |
|---|---|---|---|
| vector (OpenAI embeddings) | 8/14 (57%) | 8/14 (57%) | 5/5 |
| **BM25 (PyThaiNLP newmm)** | **13/14 (93%)** | **13/14 (93%)** | 5/5 |

Corpus: 71,000 characters of Thai text about WWI and Siam's entry into it.


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


## How I measure it 

the eval set has 19 questions. 14 have answers in corpus . 5 do not for testing the refuse of system instead of making something up.

**Retrieval** is scored with a gold_snippet: a phrase from the sentence that actually answers the question. If that phrase is not in the retrieved chunks, retrieval failed.

**Answers** are scored by keyword coverage: how many expected keywords appear in the answer, as a fraction.

**Refusal** is scored separately, only on the 5 out-of-corpus questions. Correct = the answer contains ไม่ทราบ.



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

- **gpt-3.5-turbo produces malformed Thai** Early output contained broken Thai words. Checking the retrieved chunks showed they were clean, isolating the fault to generation rather than retrieval. Switching to gpt-4o-mini resolved it — and costs less.

- **My first metric was lying to me** I used to score retrieval by checking if a keyword appeared anywhere in the 10 retrieved chunks. That reported 80%.

**The problem** : the keyword can appear in a chunk about a different topic so that the answer of the question never retrived

**fixed** : switching to gold_snippet and found that the honest number was 57%.

- **One sentence answers three of my questions, and vector search never found it** 

**The problem** : since one word can appear more than one time, the old vector search is not accurate in this case.

**fixed** : Using BM25 , BM25 weights words by how rare they are. In my corpus:

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




### Update

- **20/08/26** i found that my RAG had a big problem which is retrieval failure some . Since,retrieval_score is 1.0 but after i read all chunks i realize that i couldn't answer it either . So the score
was lying.
**The reason**: my score only checks if the keyword appears somewhere in the 10 chunks. If key words showed up in chunk about a different topic, so the score said 1.0 — but the sentence that really answers the question was never retrieved.