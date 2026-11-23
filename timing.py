"""Summarise per-model call latency from a results file and extrapolate the full v0 runtime.

Usage: python3 timing.py [--results results/timing.jsonl] [--cells-per-model 1780]
1780 = 89 pairs x 4 prompt types x 5 samples. Latencies for batched local generation are the
batch wall time divided by the batch size, so the estimate already reflects batching.
"""
import argparse
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(ROOT, "results", "timing.jsonl"))
    ap.add_argument("--cells-per-model", type=int, default=1780)
    args = ap.parse_args()
    lat, tps, batched = defaultdict(list), defaultdict(list), defaultdict(set)
    for line in open(args.results, encoding="utf-8"):
        r = json.loads(line)
        if r.get("latency_s") is not None:
            lat[r["model_id"]].append(float(r["latency_s"]))
        if r.get("tokens_per_s"):
            tps[r["model_id"]].append(float(r["tokens_per_s"]))
        batched[r["model_id"]].add(r.get("batched"))
    print("| model | calls timed | mean s/call | median tokens/s | batch sizes seen | est. full run (%d cells) |" % args.cells_per_model)
    print("|---|---|---|---|---|---|")
    total = 0.0
    for m, L in lat.items():
        mean = sum(L) / len(L)
        est = mean * args.cells_per_model
        total += est
        med_tps = sorted(tps[m])[len(tps[m]) // 2] if tps[m] else float("nan")
        print("| %s | %d | %.2f | %.0f | %s | %.1f h |" % (m, len(L), mean, med_tps, sorted(b for b in batched[m] if b), est / 3600))
    print("| total | | | | | %.1f h |" % (total / 3600))


if __name__ == "__main__":
    main()
