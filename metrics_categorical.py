"""Metrics for the categorical track from results/results.jsonl (track == "categorical") and the
categorical data tables; writes results/metrics_categorical.md.

Per model (cell = one pair x prompt type; option cells take the modal parsed option across
samples, number cells the median):
  quality      ok / refusal / unparseable / out_of_range / truncated rates per prompt type
  accuracy     share of plain and official cells whose modal option is in the truth set, per source and pooled
  inheritance  on rows where a public majority (> 50%) picks a wrong option: share of plain cells equal to that
               majority option (sides with the public), equal to the truth (sides with the truth), or other
  flattening   per item across countries, logit(M_public) on logit(share correct): slope, bootstrap CI, corr,
               mean |M_public - share correct| in points; pooled with item fixed effects
  memorization share of memory_check cells within 5 (and 2) points of the real share correct, plus corr
  distributions (if results/distributions.jsonl exists) mean entropy in bits per prompt type and, for option
               prompts, mean probability on the truth option and on the public-majority option; for number
               prompts the share of bimodal cells
Run: python3 metrics_categorical.py [--results results/results.jsonl] [--out results/metrics_categorical.md]
"""
import argparse
import json
import os
from collections import Counter, defaultdict

import numpy as np

import distributions

ROOT = os.path.dirname(os.path.abspath(__file__))
CLIP = 0.0005
PROMPTS = ["plain", "official", "public_guess", "memory_check"]


def logit(v):
    p = np.clip(np.asarray(v, dtype=float) / 100.0, CLIP, 1 - CLIP)
    return np.log(p / (1 - p))


def ols(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.var(x) == 0:
        return None, None
    b = np.cov(x, y, bias=True)[0, 1] / np.var(x)
    return b, float(np.mean(y) - b * np.mean(x))


def boot(fn, n, rng, reps):
    vals = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        v = fn(idx)
        if v is not None and np.isfinite(v):
            vals.append(v)
    return tuple(np.percentile(vals, [2.5, 97.5])) if vals else (float("nan"), float("nan"))


def fmt(v, d=2):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else ("%%.%df" % d) % v


def demean(x, groups):
    x = np.asarray(x, float).copy()
    for g in set(groups):
        m = np.asarray([gg == g for gg in groups])
        x[m] = x[m] - x[m].mean()
    return x


def load_results(path):
    """cells[(model,item,iso3,prompt)] -> list of parsed values; meta[(model,item,iso3)] -> row fields."""
    cells, meta, status, dist_keys = defaultdict(list), {}, defaultdict(lambda: defaultdict(int)), {}
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("track") != "categorical":
            continue
        k = (r["model_id"], r["item_id"], r["country_iso3"], r["prompt_type"])
        status[(r["model_id"], r["prompt_type"])][r["parse_status"]] += 1
        if r["parse_status"] == "ok":
            cells[k].append(r["parsed_value"])
        meta[(r["model_id"], r["item_id"], r["country_iso3"])] = {
            "source": r["source_id"], "truth_set": r["truth_set"], "majority": r["public_majority_option"],
            "pct_correct": float(r["pct_correct"]), "country": r["country"]}
        dist_keys[k] = r["model_id"] + ":" + r["prompt_sha256"]
    return cells, meta, status, dist_keys


def cell_value(prompt, vals):
    if prompt in ("plain", "official"):
        return Counter(vals).most_common(1)[0][0]
    return float(np.median([float(v) for v in vals]))


def model_metrics(model, cells, meta, status, dists, dist_keys, rng, reps):
    L = ["## %s" % model, ""]
    val = {k: cell_value(k[3], v) for k, v in cells.items() if k[0] == model and v}
    sources = sorted({m["source"] for (mm, _, _), m in meta.items() if mm == model})
    summary = {"model": model}

    L += ["### Response quality", "", "| prompt | n | ok | refusal | unparseable | out_of_range | truncated |", "|---|---|---|---|---|---|---|"]
    for pt in PROMPTS:
        st = status.get((model, pt), {})
        n = sum(st.values())
        if n:
            L.append("| %s | %d | %s |" % (pt, n, " | ".join("%.0f%%" % (100.0 * st.get(s, 0) / n) for s in ["ok", "refusal", "unparseable", "out_of_range", "truncated"])))
    L.append("")

    L += ["### Accuracy of the model's own answer (modal option in the truth set)", "", "| scope | cells | plain accuracy | official accuracy |", "|---|---|---|---|"]
    for scope in ["pooled"] + sources:
        keys = [(i, c) for (mm, i, c), m in meta.items() if mm == model and (scope == "pooled" or m["source"] == scope)]
        accs = {}
        for pt in ("plain", "official"):
            got = [(val[(model, i, c, pt)] in meta[(model, i, c)]["truth_set"]) for i, c in keys if (model, i, c, pt) in val]
            accs[pt] = (float(np.mean(got)), len(got)) if got else (float("nan"), 0)
        if accs["plain"][1] or accs["official"][1]:
            L.append("| %s | %d | %s | %s |" % (scope, max(accs["plain"][1], accs["official"][1]), "%.0f%%" % (100 * accs["plain"][0]) if accs["plain"][1] else "n/a", "%.0f%%" % (100 * accs["official"][0]) if accs["official"][1] else "n/a"))
        if scope == "pooled":
            summary["acc_plain"], summary["acc_official"] = accs["plain"][0], accs["official"][0]
    L.append("")

    L += ["### Inheritance where a public majority (> 50%) is wrong, plain prompt", "",
          "| scope | rows | sides with public majority | sides with truth | other |", "|---|---|---|---|---|"]
    for scope in ["pooled"] + sources:
        rows = [(i, c, m) for (mm, i, c), m in meta.items() if mm == model and (scope == "pooled" or m["source"] == scope)
                and m["majority"] not in ("", "no_majority") and m["majority"] not in m["truth_set"] and (model, i, c, "plain") in val]
        if not rows:
            continue
        pub = sum(val[(model, i, c, "plain")] == m["majority"] for i, c, m in rows)
        tru = sum(val[(model, i, c, "plain")] in m["truth_set"] for i, c, m in rows)
        L.append("| %s | %d | %.0f%% | %.0f%% | %.0f%% |" % (scope, len(rows), 100.0 * pub / len(rows), 100.0 * tru / len(rows), 100.0 * (len(rows) - pub - tru) / len(rows)))
        if scope == "pooled":
            summary["inherit_public"], summary["inherit_truth"], summary["inherit_rows"] = pub / len(rows), tru / len(rows), len(rows)
    L.append("")

    L += ["### Flattening: logit(M_public) on logit(share correct) across countries", "",
          "| item | countries | slope | 95% CI | corr | mean abs(M_public - share correct) |", "|---|---|---|---|---|---|"]
    items = sorted({i for (mm, i, c) in meta if mm == model})
    pooled_x, pooled_y, pooled_g = [], [], []
    for item in items:
        keys = [(i, c) for (mm, i, c) in meta if mm == model and i == item and (model, i, c, "public_guess") in val]
        if len(keys) < 5:
            continue
        mp = np.array([val[(model, i, c, "public_guess")] for i, c in keys]); h = np.array([meta[(model, i, c)]["pct_correct"] for i, c in keys])
        lm, lh = logit(mp), logit(h)
        b, _ = ols(lh, lm)
        ci = boot(lambda idx: ols(lh[idx], lm[idx])[0], len(keys), rng, reps)
        corr = float(np.corrcoef(lh, lm)[0, 1]) if np.std(lm) > 0 and np.std(lh) > 0 else float("nan")
        L.append("| %s | %d | %s | [%s, %s] | %s | %s |" % (item, len(keys), fmt(b), fmt(ci[0]), fmt(ci[1]), fmt(corr), fmt(float(np.mean(np.abs(mp - h))), 1)))
        pooled_x += list(lh); pooled_y += list(lm); pooled_g += [item] * len(keys)
    if len(pooled_x) >= 5:
        x, y = np.array(pooled_x), np.array(pooled_y)
        b, _ = ols(demean(x, pooled_g), demean(y, pooled_g))

        def ps(idx):
            g = [pooled_g[i] for i in idx]
            return ols(demean(x[idx], g), demean(y[idx], g))[0]
        ci = boot(ps, len(x), rng, reps)
        L.append("| pooled (item FE) | %d | %s | [%s, %s] | | |" % (len(x), fmt(b), fmt(ci[0]), fmt(ci[1])))
        summary["flat_pooled"] = b
        allp = [(val[(model, i, c, "public_guess")], meta[(model, i, c)]["pct_correct"]) for (mm, i, c) in meta if mm == model and (model, i, c, "public_guess") in val]
        summary["public_err"] = float(np.mean([abs(a - b2) for a, b2 in allp])) if allp else None
    L.append("")

    L += ["### Memorization check (memory_check vs real share correct)", "", "| scope | cells | within 2 pts | within 5 pts | corr |", "|---|---|---|---|---|"]
    for scope in ["pooled"] + sources:
        keys = [(i, c) for (mm, i, c), m in meta.items() if mm == model and (scope == "pooled" or m["source"] == scope) and (model, i, c, "memory_check") in val]
        if len(keys) < 5:
            continue
        mm_ = np.array([val[(model, i, c, "memory_check")] for i, c in keys]); h = np.array([meta[(model, i, c)]["pct_correct"] for i, c in keys])
        corr = float(np.corrcoef(mm_, h)[0, 1]) if np.std(mm_) > 0 else float("nan")
        L.append("| %s | %d | %.0f%% | %.0f%% | %s |" % (scope, len(keys), 100 * np.mean(np.abs(mm_ - h) <= 2), 100 * np.mean(np.abs(mm_ - h) <= 5), fmt(corr)))
        if scope == "pooled":
            summary["memory_within5"] = float(np.mean(np.abs(mm_ - h) <= 5))
    L.append("")

    if dists:
        L += ["### Answer distributions (from results/distributions.jsonl)", "",
              "| prompt | cells with a distribution | mean entropy (bits) | mean P(truth option) | mean P(public majority option) | bimodal cells |", "|---|---|---|---|---|---|"]
        for pt in PROMPTS:
            ents, pt_truth, pt_maj, bim, n = [], [], [], 0, 0
            for (mm, i, c, p), key in dist_keys.items():
                if mm != model or p != pt or key not in dists:
                    continue
                e = dists[key]; n += 1
                if e.get("entropy_bits") is not None:
                    ents.append(e["entropy_bits"])
                if e["kind"] == "option":
                    m = meta[(model, i, c)]
                    pt_truth.append(sum(e["option_probs"].get(t, 0.0) for t in m["truth_set"]))
                    if m["majority"] in e["option_probs"]:
                        pt_maj.append(e["option_probs"][m["majority"]])
                else:
                    bim += bool(e.get("bimodal"))
            if n:
                L.append("| %s | %d | %s | %s | %s | %s |" % (pt, n, fmt(float(np.mean(ents))) if ents else "n/a",
                                                             fmt(float(np.mean(pt_truth))) if pt_truth else "n/a", fmt(float(np.mean(pt_maj))) if pt_maj else "n/a",
                                                             ("%.0f%%" % (100.0 * bim / n)) if pt in ("public_guess", "memory_check") else "n/a"))
                if pt == "plain" and ents:
                    summary["entropy_plain"] = float(np.mean(ents))
        L.append("")
    return L, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(ROOT, "results", "results.jsonl"))
    ap.add_argument("--distributions", default=os.path.join(ROOT, "results", "distributions.jsonl"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "metrics_categorical.md"))
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    cells, meta, status, dist_keys = load_results(args.results)
    dists = distributions.load_entries(args.distributions)
    models = sorted({k[0] for k in cells})
    lines = ["# Categorical track metrics", "", "Source: `%s`. Option cells = modal parsed option across samples; number cells = median. Log-odds clip = %g. "
             "Inheritance counts only rows where more than half of the public chose a wrong option." % (os.path.relpath(args.results, ROOT), CLIP), ""]
    summaries = []
    for m in models:
        Lm, s = model_metrics(m, cells, meta, status, dists, dist_keys, rng, args.boot)
        lines += Lm
        summaries.append(s)
    head = ["| model | plain accuracy | official accuracy | majority-wrong rows | sides with public | sides with truth | flatten slope pooled | abs(M_public - share correct) | memory within 5 | mean entropy plain (bits) |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        pc = lambda v: "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else "%.0f%%" % (100 * v)
        head.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (s["model"], pc(s.get("acc_plain")), pc(s.get("acc_official")), s.get("inherit_rows", "n/a"),
                                                                     pc(s.get("inherit_public")), pc(s.get("inherit_truth")), fmt(s.get("flat_pooled")), fmt(s.get("public_err"), 1), pc(s.get("memory_within5")), fmt(s.get("entropy_plain"))))
    lines = lines[:4] + ["## Summary", ""] + head + [""] + lines[4:]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(head))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
