import json
import os
import sys
import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    query_documents,
    generate_response,
    query_bm25,
    query_hybrid,
    judge,
    GENERATOR,
    model as GENERATOR_MODEL,
)

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "questions.json")
N_RESULTS = 10
MAX_CHARS = 1200
OVERLAP = 1
THRESHOLD = 0.75
Retriever_type = "bm25"


def contains(text, keywords):
    if not keywords:
        return 0.0
    return sum(kw in text for kw in keywords) / len(keywords)


def retrieve(question, n_results):
    if Retriever_type == "vec":
        return query_documents(question, n_results=n_results)
    if Retriever_type == "bm25":
        return query_bm25(question, n_results=n_results)
    return query_hybrid(question, n_results=n_results)


def tier_report(label, rows):
    """Print one difficulty tier. in-corpus and negatives never share a denominator."""
    in_corpus = [r for r in rows if r["retrieval_score"] is not None]
    negatives = [r for r in rows if r["retrieval_score"] is None]

    if in_corpus:
        r_hits = sum(r["retrieval_pass"] for r in in_corpus)
        a_hits = sum(r["answer_pass"] for r in in_corpus)
        r_mean = sum(r["retrieval_score"] for r in in_corpus) / len(in_corpus)
        a_mean = sum(r["answer_score"] for r in in_corpus) / len(in_corpus)
        print(f"{label:<6} retrieval {r_hits:>3}/{len(in_corpus):<3} ({r_hits/len(in_corpus):.0%})"
              f"   answer {a_hits:>3}/{len(in_corpus):<3} ({a_hits/len(in_corpus):.0%})"
              f"   keyword-mean {a_mean:.3f}   retrieval-mean {r_mean:.3f}")
    if negatives:
        refusals = sum(r["answer_pass"] for r in negatives)
        print(f"{label:<6} refusal   {refusals:>3}/{len(negatives):<3} ({refusals/len(negatives):.0%})")

    return {
        "in_corpus": len(in_corpus),
        "negatives": len(negatives),
        "retrieval_hits": sum(r["retrieval_pass"] for r in in_corpus),
        "answer_hits": sum(r["answer_pass"] for r in in_corpus),
        "refusals": sum(r["answer_pass"] for r in negatives),
    }


def main():
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    results = []

    for case in cases:
        question = case["question"]
        keywords = case["expected_keywords"]
        difficulty = case.get("difficulty", "easy")

        # gold_snippets is a LIST. Retrieval passes only when EVERY span is present —
        # that is what makes a multi-hop question unsatisfiable by a single chunk.
        # An empty list marks a negative: not in the corpus, PASS = the system refuses.
        snippets = case.get("gold_snippets") or []

        chunks = retrieve(question, N_RESULTS)
        joined = "\n".join(chunks)

        answer = generate_response(question, chunks)
        v = judge(question, case["gold_answer"], answer)

        if snippets:
            found = [s for s in snippets if s in joined]
            retrieval_score = len(found) / len(snippets)
            retrieval_pass = len(found) == len(snippets)
            missing = [s for s in snippets if s not in joined]
        else:
            retrieval_score = None
            retrieval_pass = None
            missing = []

        answer_score = contains(answer, keywords)
        answer_pass = answer_score >= THRESHOLD

        results.append({
            "question": question,
            "difficulty": difficulty,
            "type": case.get("_type", ""),
            "expected": keywords,
            "gold_snippets": snippets,
            "missing_snippets": missing,
            "retrieval_score": retrieval_score,
            "answer_score": answer_score,
            "retrieval_pass": retrieval_pass,
            "answer_pass": answer_pass,
            "answer": answer,
            "judge_verdict": v["verdict"],
            "judge_reason": v["reason"],
        })

        # per-question line — INSIDE the loop
        if retrieval_score is None:
            status = "REFUSED" if answer_pass else "HALLUCINATED"
            r_str = " n/a"
        else:
            status = "PASS" if answer_pass else ("RETRIEVED-ONLY" if retrieval_pass else "FAIL")
            r_str = f"{retrieval_score:.2f}"
        print(f"[{difficulty:<4} {status:<14}] r={r_str} a={answer_score:.2f} "
              f"judge={v['verdict']:<9} {question[:60]}")

    easy = [r for r in results if r["difficulty"] == "easy"]
    hard = [r for r in results if r["difficulty"] == "hard"]

    print("\n" + "=" * 78)
    print(f"generator: {GENERATOR} ({GENERATOR_MODEL})   retriever: {Retriever_type}   "
          f"n_results: {N_RESULTS}   threshold: {THRESHOLD}")
    print("-" * 78)
    summary = {}
    if easy:
        summary["easy"] = tier_report("easy", easy)
    if hard:
        summary["hard"] = tier_report("hard", hard)
    print("=" * 78)

    # judge vs keyword scoring, per tier — this is where the judge earns its cost
    for label, rows in (("easy", easy), ("hard", hard)):
        in_corpus = [r for r in rows if r["retrieval_score"] is not None]
        if not in_corpus:
            continue
        ctr = Counter(r["judge_verdict"] for r in in_corpus)
        disagree = [r for r in in_corpus
                    if r["answer_pass"] != (r["judge_verdict"] == "correct")]
        print(f"\n{label}: judge correct {ctr['correct']} partial {ctr['partial']} "
              f"incorrect {ctr['incorrect']}   |   disagreements {len(disagree)}/{len(in_corpus)}")
        for r in disagree:
            print(f"  Q: {r['question'][:70]}")
            print(f"     keyword {r['answer_score']:.2f} vs judge {r['judge_verdict']}")
            print(f"     reason: {r['judge_reason'][:150]}")
            print(f"     answer: {r['answer'][:150]}")

    # failures, attributed
    failures = [r for r in results
                if r["retrieval_score"] is not None and not r["answer_pass"]]
    if failures:
        print(f"\n--- {len(failures)} in-corpus failures ---")
        for f in failures:
            if not f["retrieval_pass"]:
                cause = "retrieval"
            elif f["retrieval_score"] - f["answer_score"] > 0.2:
                cause = "generation"
            else:
                cause = "generation (used all it had)"
            print(f"\n[{f['difficulty']}] {cause}")
            print(f"  Q: {f['question']}")
            print(f"  expected: {f['expected']}")
            print(f"  r={f['retrieval_score']:.2f} a={f['answer_score']:.2f}")
            if f["missing_snippets"]:
                print(f"  missing snippets: {f['missing_snippets']}")
            print(f"  answer: {f['answer'][:200]}")

    # hallucinations on negatives
    halluc = [r for r in results if r["retrieval_score"] is None and not r["answer_pass"]]
    if halluc:
        print(f"\n--- {len(halluc)} hallucinations on negatives ---")
        for r in halluc:
            print(f"\n[{r['difficulty']}] Q: {r['question']}")
            print(f"  answer: {r['answer'][:200]}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "reports"), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report = {
        "config": {
            "generator": GENERATOR,
            "generator_model": GENERATOR_MODEL,
            "retriever": Retriever_type,
            "n_results": N_RESULTS,
            "threshold": THRESHOLD,
            "metric": "keyword coverage + llm judge",
            "temperature": 0,
            "embedding_model": "text-embedding-3-small",
            "max_chars": MAX_CHARS,
            "overlap_paras": OVERLAP,
        },
        "summary": summary,
        "results": results,
    }
    path = os.path.join(os.path.dirname(__file__), "reports", f"{stamp}_{GENERATOR}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nwrote", path)


if __name__ == "__main__":
    main()