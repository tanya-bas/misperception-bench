"""Re-parse every reply in a results file with the current parse.py and rewrite parse_status,
parsed_value and parse_note in place. The runner stores the parse at generation time; when the
parser changes (e.g. the 2026-11-22 refusal fix for typographic apostrophes) run this so the stored
status matches the current rules. metrics.py reads the stored status.
Run: python3 scripts/reparse_results.py [results/results.jsonl]
"""
import json, os, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import parse  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "results.jsonl")
rows, changed, before, after = [], 0, Counter(), Counter()
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    old = (r.get("parse_status"), r.get("parsed_value"))
    v, status, note = parse.parse_number(r.get("raw_text"))
    if r.get("finish_reason") == "length" and status != "ok":
        status = "truncated"  # keep the runner's convention for cut-off replies
    r["parsed_value"], r["parse_status"], r["parse_note"] = v, status, note
    before[(r["model_id"], old[0])] += 1
    after[(r["model_id"], status)] += 1
    changed += (old != (status, v))
    rows.append(r)
with open(path, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("rows", len(rows), "changed", changed)
for m in sorted({k[0] for k in after}):
    print(m, {k[1]: n for k, n in sorted(after.items()) if k[0] == m})
