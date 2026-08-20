import json
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import query_documents, generate_response

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "questions.json")
N_RESULTS = 10
MAX_CHARS  = 1200
OVERLAP    = 1
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


    for case in cases:
        question = case["question"]
        keywords = case["expected_keywords"]

        chunks = query_documents(question, n_results=N_RESULTS)
        joined = "\n".join(chunks)
        answer = generate_response(question, chunks)

        retrieval_score = contains(joined,keywords)
        answer_score = contains(answer,keywords)

        retrieval_pass = retrieval_score >= THRESHOLD
        answer_pass = answer_score >= THRESHOLD

        retrieval_total += retrieval_score
        answer_total += answer_score
        retrieval_hits += retrieval_pass
        answer_hits += answer_pass

        results.append({
            "question": question,
            "expected": keywords,
            "retrieval_score": retrieval_score,
            "answer_score": answer_score,
            "retrieval_pass": bool(retrieval_pass),
            "answer_pass": bool(answer_pass),
            "answer": answer,
        })


        status = "PASS" if answer_pass else ("RETRIEVED-ONLY" if retrieval_pass else "FAIL")
        print(f"[{status}] r={retrieval_score:.2f} a={answer_score:.2f}  {question}")

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

    if failures:
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
            "answer_mean": answer_total / total,
        },
        "results": results,
        "failures": failures,
    }
    path = os.path.join(os.path.dirname(__file__), "reports", f"{stamp}.json")
    json.dump(report, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", path)

if __name__ == "__main__":
    main()