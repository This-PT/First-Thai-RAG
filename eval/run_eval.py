import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import query_documents, generate_response

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "questions.json")
N_RESULTS = 15


def contains_all(text, keywords):
    return all(kw in text for kw in keywords)


def contains_any(text, keywords):
    return any(kw in text for kw in keywords)


def main():
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    retrieval_hits = 0
    answer_hits = 0
    failures = []

    for case in cases:
        question = case["question"]
        keywords = case["expected_keywords"]

        chunks = query_documents(question, n_results=N_RESULTS)
        joined = "\n".join(chunks)

        # Did retrieval surface the evidence at all?
        retrieved_ok = contains_any(joined, keywords)

        # Did the final answer actually state it?
        answer = generate_response(question, chunks)
        answered_ok = contains_all(answer, keywords)

        retrieval_hits += retrieved_ok
        answer_hits += answered_ok

        status = "PASS" if answered_ok else ("RETRIEVED-ONLY" if retrieved_ok else "FAIL")
        print(f"[{status}] {question}")

        if not answered_ok:
            failures.append(
                {
                    "question": question,
                    "expected": keywords,
                    "retrieved_evidence": retrieved_ok,
                    "answer": answer,
                }
            )

    total = len(cases)
    print("\n" + "=" * 50)
    print(f"Retrieval hit rate: {retrieval_hits}/{total} ({retrieval_hits / total:.0%})")
    print(f"Answer accuracy:    {answer_hits}/{total} ({answer_hits / total:.0%})")
    print("=" * 50)

    if failures:
        print("\nFailures worth inspecting:\n")
        for f in failures:
            cause = "generation" if f["retrieved_evidence"] else "retrieval"
            print(f"  Q: {f['question']}")
            print(f"  expected: {f['expected']}")
            print(f"  likely cause: {cause}")
            print(f"  answer: {f['answer'][:200]}\n")


if __name__ == "__main__":
    main()