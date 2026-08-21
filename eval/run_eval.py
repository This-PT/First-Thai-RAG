import json
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import query_documents, generate_response,query_bm25

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "questions.json")
N_RESULTS = 10
MAX_CHARS  = 1200
OVERLAP    = 1
Retriever_Vec = False

results = []

def contains(text, keywords):
    return sum(kw in text for kw in keywords)/len(keywords)





def main():
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    retrieval_total = 0
    answer_total    = 0.0
    retrieval_hits = 0
    answer_hits = 0
    failures = []
    THRESHOLD = 0.75
    n_results = 10

    for case in cases:
        question = case["question"]
        keywords = case["expected_keywords"]

        if Retriever_Vec:
            chunks = query_documents(question, n_results=n_results)
        else:
            chunks = query_bm25(question, n_results=n_results)

        joined = "\n".join(chunks)


        answer = generate_response(question, chunks)





        # retrieval_score = contains(joined,keywords)
        
        gold = case.get("gold_snippet")
        retrieval_score = None if gold is None else float(gold in joined)
        answer_score = contains(answer,keywords)


        retrieval_pass = None if retrieval_score is None else retrieval_score >= THRESHOLD
        answer_pass = answer_score >= THRESHOLD

        # dict
        results.append({
                    "question": question,
                    "expected": keywords,
                    "retrieval_score": retrieval_score,
                    "answer_score": answer_score,
                    "retrieval_pass": bool(retrieval_pass),
                    "answer_pass": bool(answer_pass),
                    "answer": answer,
                })


    in_corpus = [r for r in results if r["retrieval_score"] is not None]
    negatives = [r for r in results if r["retrieval_score"] is None]

    retrieval_hits = sum(r["retrieval_pass"] for r in in_corpus)
    answer_hits    = sum(r["answer_pass"]    for r in in_corpus)
    refusals       = sum(r["answer_pass"]    for r in negatives)



    print(f"in-corpus  retrieval {retrieval_hits}/{len(in_corpus)}")
    print(f"in-corpus  answer    {answer_hits}/{len(in_corpus)}")
    print(f"negatives  refusal   {refusals}/{len(negatives)}")

    answer_mean = sum(r["answer_score"] for r in in_corpus) / len(in_corpus) if len(in_corpus) != 0 else 0
    print("mean :",answer_mean)

    r_str = " n/a" if retrieval_score is None else f"{retrieval_score:.2f}"
    

    if retrieval_score is None:
        status = "REFUSED" if answer_pass else "HALLUCINATED"
    else:
        status = "PASS" if answer_pass else ("RETRIEVED-ONLY" if retrieval_pass else "FAIL")

    print(f"[{status}] r={r_str} a={answer_score:.2f}  {question}")
    if not answer_pass:
        failures.append(
            {
                "question": question,
                "expected": keywords,
                "retrieval_score": retrieval_score,
                "answer_score" : answer_score,
                "answer": answer,
            }
        )
    # print("ans_score : ",answer_score)
    total = len(cases)
    print("\n" + "=" * 50)
    print(f"Retrieval hit rate: {retrieval_hits}/{total} ({retrieval_hits / total:.2f})")
    print(f"Answer accuracy:    {answer_hits}/{total} ({answer_hits / total:.2f})")
    print("=" * 50)

    failures = [r for r in in_corpus if not r["answer_pass"]]

    for f in failures:
        gap = f["retrieval_score"] - f["answer_score"]
        if f["retrieval_score"] < THRESHOLD:
            cause = "retrieval"
        elif gap > 0.2:
            cause = "generation"
        else:
            cause = "generation (used all it had)"
        print(cause)
        print(f"  Q: {f['question']}")
        print(f"  expected: {f['expected']}")
        print(f"  r={f['retrieval_score']:.2f} a={f['answer_score']:.2f}  cause: {cause}")
        print(f"  answer: {f['answer'][:200]}\n")

    os.makedirs(os.path.join(os.path.dirname(__file__), "reports"), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    report = {
        "config": {
            "n_results": N_RESULTS,
            "threshold": THRESHOLD,
            "metric": "keyword coverage",
            "model": "gpt-4o-mini",
            "temperature": 0,
            "embedding_model": "text-embedding-3-small",
            "max_chars": MAX_CHARS,
            "overlap_paras": OVERLAP,
        },
        "summary": {
            "retrieval_hits": retrieval_hits,
            "retrieval_mean": retrieval_total / total,
            "answer_hits": answer_hits,
            "answer_mean": answer_mean,
        },
        "results": results,
        "failures": failures,
    }
    path = os.path.join(os.path.dirname(__file__), "reports", f"{stamp}.json")
    json.dump(report, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", path)

if __name__ == "__main__":
    main()