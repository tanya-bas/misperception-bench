"""Answer distributions for the 360 unique v0 prompts (Ipsos 2024, 90 pairs x 4 prompt types) on every
model in models.yaml, and a bimodality summary against H and T.

Reads the v0 results snapshot (results/v0/results.jsonl) for the prompt texts and, for harmony models
(gpt-oss), the sample-0 reasoning that fixes the answer position; writes results/v0/distributions.jsonl
(one entry per model x prompt; resume-safe) and results/v0/distributions_summary.md.

Summary, per model and item, over the pairs with |H - T| >= 10: how often the plain and public_guess
distributions put at least MASS_MIN of their probability within 5 points of T and also within 5 points
of H ("bimodal H/T"), the mean mass near T vs near H, the general bimodality rate (two peaks, see
distributions.py), mean entropy, and the time the extra passes took.
Run: .venv/bin/python scripts/distributions_v0.py [--models qwen3.5-9b] [--limit N] [--prune 1e-4]
"""
import argparse
import csv
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import distributions  # noqa: E402
import providers  # noqa: E402
import run as runner  # noqa: E402

V0 = os.path.join(ROOT, "results", "v0", "results.jsonl")
OUT = os.path.join(ROOT, "results", "v0", "distributions.jsonl")
SUMMARY = os.path.join(ROOT, "results", "v0", "distributions_summary.md")
PAIRS = os.path.join(ROOT, "data", "pairs.csv")
MASS_MIN = 0.15
WINDOW = 5
GAP = 10


def load_v0():
    """Unique (model_id, prompt_text) with the sample-0 row and settings."""
    out = {}
    for line in open(V0, encoding="utf-8"):
        r = json.loads(line)
        k = (r["model_id"], r["prompt_text"])
        if k not in out or r["sample_idx"] == 0:
            out[k] = r
    return out


def compute(models, rows, limit, prune):
    existing = distributions.load_existing(OUT)
    timing = {}
    with open(OUT, "a", encoding="utf-8") as f:
        for m in models:
            todo = [r for (mid, text), r in rows.items() if mid == m["model_id"] and distributions.dist_key(mid, text) not in existing]
            if limit:
                todo = todo[:limit]
            if not todo:
                print("%s: nothing to do" % m["model_id"])
                continue
            print("loading %s..." % m["model_id"], flush=True)
            handle = providers.load_local(m)
            t0, passes = time.time(), 0
            try:
                for i, r in enumerate(todo, 1):
                    cp = {"prompt_text": r["prompt_text"], "answer_kind": "number"}
                    e = distributions.compute_entry(handle, m, cp, r.get("raw_generation"), r["settings"], prune=prune)
                    e.update({"track": "numeric", "wave": r.get("wave", "ipsos_2024"), "item_id": r["item_id"], "country_iso3": r["country_iso3"],
                              "prompt_type": r["prompt_type"], "prompt_variant": "v1"})
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
                    f.flush()
                    passes += e["passes"]
                    if i % 30 == 0 or i == len(todo):
                        dt = time.time() - t0
                        print("  %s %d/%d prompts, %d passes, %.0fs (%.2fs per prompt)" % (m["model_id"], i, len(todo), passes, dt, dt / i), flush=True)
            finally:
                providers.unload_local(handle)
            timing[m["model_id"]] = {"prompts": len(todo), "passes": passes, "seconds": round(time.time() - t0, 1)}
    return timing


def summarize(timing):
    pairs = {(r["item_id"], r["country_iso3"]): (float(r["h_mean"]), float(r["t_value"])) for r in csv.DictReader(open(PAIRS, encoding="utf-8"))
             if r["wave"] == "ipsos_2024" and r["t_value"] != ""}
    entries = list(distributions.load_entries(OUT).values())
    models = sorted({e["model_id"] for e in entries})
    items = ["wealth_top1", "immigrant_share", "muslim_share"]
    L = ["# v0 answer distributions: bimodality against H and T", "",
         "Entries: %d (results/v0/distributions.jsonl). Candidates 0-100 at the answer position; see distributions.py for the digit-tree method. "
         "Pairs with |H - T| >= %d only. Mass near X = probability within %d points of X; 'bimodal H/T' = both masses >= %.2f. "
         "'bimodal (peaks)' = at least two local maxima >= 0.05 at least 3 apart, any pair." % (len(entries), GAP, WINDOW, MASS_MIN), ""]
    if timing:
        L += ["## Timing", "", "| model | prompts | extra forward passes | seconds | s per prompt |", "|---|---|---|---|---|"]
        for mid, t in timing.items():
            L.append("| %s | %d | %d | %.0f | %.2f |" % (mid, t["prompts"], t["passes"], t["seconds"], t["seconds"] / max(t["prompts"], 1)))
        L.append("")
    L += ["## Bimodality on divergent pairs", "", "| model | prompt | item | pairs | mass near T (mean) | mass near H (mean) | bimodal H/T | bimodal (peaks) | mean entropy (bits) | mass outside 0-100 (mean) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        for pt in ["plain", "public_guess"]:
            for scope in ["pooled"] + items:
                sel = [e for e in entries if e["model_id"] == m and e["prompt_type"] == pt and (scope == "pooled" or e["item_id"] == scope)
                       and (e["item_id"], e["country_iso3"]) in pairs and abs(pairs[(e["item_id"], e["country_iso3"])][0] - pairs[(e["item_id"], e["country_iso3"])][1]) >= GAP]
                if not sel:
                    continue
                mt, mh, bht, bpk, ent, outside = [], [], 0, 0, [], []
                for e in sel:
                    H, T = pairs[(e["item_id"], e["country_iso3"])]
                    pr = e["probs"]
                    near_t = sum(pr[i] for i in range(101) if abs(i - T) <= WINDOW)
                    near_h = sum(pr[i] for i in range(101) if abs(i - H) <= WINDOW)
                    mt.append(near_t); mh.append(near_h)
                    bht += (near_t >= MASS_MIN and near_h >= MASS_MIN)
                    bpk += bool(e.get("bimodal")); outside.append(e.get("mass_outside", 0.0))
                    if e.get("entropy_bits") is not None:
                        ent.append(e["entropy_bits"])
                n = len(sel)
                L.append("| %s | %s | %s | %d | %.2f | %.2f | %.0f%% | %.0f%% | %.2f | %.3f |" % (
                    m, pt, scope, n, sum(mt) / n, sum(mh) / n, 100.0 * bht / n, 100.0 * bpk / n, (sum(ent) / len(ent)) if ent else float("nan"), sum(outside) / n))
    L.append("")
    open(SUMMARY, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    print("wrote", SUMMARY)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="comma-separated model_id list (default: all in models.yaml)")
    ap.add_argument("--limit", type=int, help="prompts per model (testing)")
    ap.add_argument("--prune", type=float, default=1e-4)
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()
    models = runner.load_models()
    if args.models:
        want = set(args.models.split(","))
        models = [m for m in models if m["model_id"] in want]
    timing = {} if args.summary_only else compute(models, load_v0(), args.limit, args.prune)
    if timing:
        json.dump(timing, open(os.path.join(ROOT, "results", "v0", "distributions_timing.json"), "w"), indent=1)
    prev = os.path.join(ROOT, "results", "v0", "distributions_timing.json")
    if not timing and os.path.exists(prev):
        timing = json.load(open(prev))
    summarize(timing)


if __name__ == "__main__":
    main()
