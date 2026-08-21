import json,os, glob
# files = sorted(glob.glob("eval/reports/*.json"))[-3:]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "eval", "reports")
files = sorted(glob.glob(os.path.join(REPORTS, "*.json")))[-3:]
runs = [json.load(open(f, encoding="utf-8")) for f in files]

def fmt(v):
    return "n/a" if v is None else round(v, 2)

for i, run in enumerate(runs):
    print("run", i, "retrieval:", [fmt(r["retrieval_score"]) for r in run["results"]])

for i, run in enumerate(runs):
    print("run", i, "answer:   ", [fmt(r["answer_score"]) for r in run["results"]])

print([r["summary"]["answer_mean"] for r in runs])

# a = [f["answer"] for f in runs[0]["failures"]]
# b = [f["answer"] for f in runs[1]["failures"]]
# c = [f["answer"] for f in runs[2]["failures"]]
# print("identical:", a == b == c)


answers = [[r["answer"] for r in run["results"]] for run in runs]
print("identical:", all(a == answers[0] for a in answers))