"""Compute the v0 metrics from results/results.jsonl and data/pairs.csv, write results/metrics.md.

Per model (cell = median of the parsed samples for one pair x prompt type):
  quality     ok / refusal / unparseable / out_of_range / truncated rates per prompt type
  noise floor mean within-cell SD across samples vs between-country SD of cell medians, per item
  H1a         variance ratio per item: var over countries of logit(M_public) / var of logit(H), bootstrap CI
  flattening  slope of logit(M_public) on logit(H) across countries, per item and pooled with item fixed effects
              (demeaned within item), bootstrap CI on the slope, plus raw-scale SDs of M_public and H. A slope
              below 1 means the model's simulated public varies less across countries than the real public.
              The variance ratio can exceed 1 even then, when the model tracks a truth that varies more than
              human guesses do; the slope is the direct flattening measure.
  H2a         lambda: slope of (logit M_plain - logit T) on (logit H - logit T), pooled and per item, bootstrap CI
  H2b         compression: slope and intercept of logit M_plain on logit T, next to the human slope (logit H on logit T)
  H3          knowing vs saying: mean |M_official - T| vs mean |M_public - H| (points), and where M_plain sits on the
              H-T segment, s = (M_plain - T) / (H - T), median over pairs with |H - T| >= 3
  memory      share of pairs where the memory_check answer is within 2 (and 5) points of H, plus corr(M_memory, H)
Log-odds use p = value/100 clipped to [CLIP, 1-CLIP]; CLIP = 0.0005 (0.05%), so Pew's 0.004% Muslim share
in Colombia is floored rather than sent to -infinity. Bootstraps resample pairs (or countries) with replacement.
Run: python3 metrics.py [--results results/results.jsonl] [--out results/metrics.md] [--boot 1000]
"""
import argparse
import csv
import json
import os
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
CLIP = 0.0005
ITEMS = ["wealth_top1", "immigrant_share", "muslim_share"]


def logit(v):
    p = np.clip(np.asarray(v, dtype=float) / 100.0, CLIP, 1 - CLIP)
    return np.log(p / (1 - p))


def ols(x, y):
    """Slope and intercept of y on x with an intercept; None if fewer than 3 points."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.var(x) == 0:
        return None, None
    b = np.cov(x, y, bias=True)[0, 1] / np.var(x)
    return b, float(np.mean(y) - b * np.mean(x))


def boot(fn, n, rng, reps):
    """Percentile 95% CI of fn(indices) over bootstrap resamples of range(n)."""
    vals = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        v = fn(idx)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return tuple(np.percentile(vals, [2.5, 97.5]))


def fmt(v, d=2):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else ("%%.%df" % d) % v


def demean_by_group(x, groups):
    """Subtract each group's mean from x (item fixed effects for the pooled flattening fit)."""
    x = np.asarray(x, float)
    out = x.copy()
    for g in set(groups):
        mask = np.asarray([gg == g for gg in groups])
        out[mask] = x[mask] - x[mask].mean()
    return out


def load_pairs(path):
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["item_id"] not in ITEMS or r["t_flag"] == "missing" or r["t_value"] == "":
            continue
        out[(r["item_id"], r["country_iso3"])] = {"H": float(r["h_mean"]), "T": float(r["t_value"]), "country": r["country_name_ipsos"]}
    return out


def load_results(path):
    cells = defaultdict(list)   # (model, item, iso3, prompt) -> parsed ok values
    status = defaultdict(lambda: defaultdict(int))  # (model, prompt) -> status -> count
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue  # a run in progress may leave a partial last line
        k = (r["model_id"], r["item_id"], r["country_iso3"], r["prompt_type"])
        status[(r["model_id"], r["prompt_type"])][r["parse_status"]] += 1
        if r["parse_status"] == "ok":
            cells[k].append(float(r["parsed_value"]))
    return cells, status


def model_metrics(model, cells, status, pairs, rng, reps):
    """Return (markdown lines, summary dict) for one model."""
    L = ["## %s" % model, ""]
    # cell medians and SDs
    med = {}
    sd = defaultdict(list)
    for (m, item, iso, pt), vals in cells.items():
        if m != model:
            continue
        med[(item, iso, pt)] = float(np.median(vals))
        if len(vals) > 1:
            sd[(item, pt)].append(float(np.std(vals, ddof=1)))

    # quality
    L += ["### Response quality", "", "| prompt | n | ok | refusal | unparseable | out_of_range | truncated |", "|---|---|---|---|---|---|---|"]
    for pt in ["plain", "official", "public_guess", "memory_check"]:
        st = status.get((model, pt), {})
        n = sum(st.values())
        if n == 0:
            continue
        L.append("| %s | %d | %s |" % (pt, n, " | ".join("%.0f%%" % (100.0 * st.get(s, 0) / n) for s in ["ok", "refusal", "unparseable", "out_of_range", "truncated"])))
    L.append("")

    # noise floor
    L += ["### Noise floor (percent points)", "", "| item | prompt | mean within-cell SD | between-country SD of medians | ratio |", "|---|---|---|---|---|"]
    for item in ITEMS:
        for pt in ["plain", "public_guess"]:
            meds = [v for (i, iso, p), v in med.items() if i == item and p == pt]
            if len(meds) < 3:
                continue
            w = float(np.mean(sd[(item, pt)])) if sd[(item, pt)] else float("nan")
            b = float(np.std(meds, ddof=1))
            L.append("| %s | %s | %s | %s | %s |" % (item, pt, fmt(w), fmt(b), fmt(w / b if b else float("nan"))))
    L.append("")

    summary = {"model": model}

    # coverage: pairs with at least one parsed sample, per item x prompt (a run in progress shows partial counts)
    L += ["### Coverage (pairs with at least one parsed sample)", "", "| item | plain | official | public_guess | memory_check |", "|---|---|---|---|---|"]
    for item in ITEMS:
        counts = [sum(1 for (i, iso, p) in med if i == item and p == pt) for pt in ["plain", "official", "public_guess", "memory_check"]]
        L.append("| %s | %s |" % (item, " | ".join(str(c) for c in counts)))
        print("coverage %s %s: plain=%d official=%d public_guess=%d memory_check=%d" % ((model, item) + tuple(counts)))
    L.append("")

    # H1a variance ratio (public_guess)
    L += ["### H1a variance ratio, logit scale (model public_guess vs human H)", "", "| item | countries | VR | 95% CI | corr(M_public, H) |", "|---|---|---|---|---|"]
    for item in ITEMS:
        keys = [(item, iso) for (item2, iso) in pairs if item2 == item and (item, iso, "public_guess") in med]
        if len(keys) < 5:
            continue
        mp = logit([med[(item, iso, "public_guess")] for item, iso in keys])
        h = logit([pairs[k]["H"] for k in keys])
        vr = float(np.var(mp, ddof=1) / np.var(h, ddof=1))
        ci = boot(lambda idx: float(np.var(mp[idx], ddof=1) / np.var(h[idx], ddof=1)) if np.var(h[idx]) > 0 else None, len(keys), rng, reps)
        corr = float(np.corrcoef(mp, h)[0, 1])
        L.append("| %s | %d | %s | [%s, %s] | %s |" % (item, len(keys), fmt(vr), fmt(ci[0]), fmt(ci[1]), fmt(corr)))
        summary["VR_" + item] = vr
    L.append("")

    # flattening: slope of logit(M_public) on logit(H); < 1 = the simulated public varies less than the real one
    L += ["### Flattening: slope of logit(M_public) on logit(H) across countries", "",
          "Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).", "",
          "| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |", "|---|---|---|---|---|---|---|---|"]
    pooled_keys = []
    for item in ITEMS:
        keys = [(item, iso) for (item2, iso) in pairs if item2 == item and (item, iso, "public_guess") in med]
        pooled_keys += keys
        if len(keys) < 5:
            continue
        raw_mp = np.array([med[(item, iso, "public_guess")] for item, iso in keys])
        raw_h = np.array([pairs[k]["H"] for k in keys])
        mp, h = logit(raw_mp), logit(raw_h)
        b, a = ols(h, mp)
        ci = boot(lambda idx: ols(h[idx], mp[idx])[0], len(keys), rng, reps)
        corr = float(np.corrcoef(h, mp)[0, 1]) if np.std(mp) > 0 else float("nan")
        L.append("| %s | %d | %s | [%s, %s] | %s | %s | %s | %s |" % (item, len(keys), fmt(b), fmt(ci[0]), fmt(ci[1]), fmt(a), fmt(corr), fmt(float(np.std(raw_mp, ddof=1)), 1), fmt(float(np.std(raw_h, ddof=1)), 1)))
        summary["flat_" + item] = b
    if len(pooled_keys) >= 5 and len({k[0] for k in pooled_keys}) >= 1:
        groups = [k[0] for k in pooled_keys]
        mp = logit([med[(k[0], k[1], "public_guess")] for k in pooled_keys])
        h = logit([pairs[k]["H"] for k in pooled_keys])
        mp_d, h_d = demean_by_group(mp, groups), demean_by_group(h, groups)
        b, _ = ols(h_d, mp_d)

        def pooled_slope(idx):
            g = [groups[i] for i in idx]
            return ols(demean_by_group(h[idx], g), demean_by_group(mp[idx], g))[0]
        ci = boot(pooled_slope, len(pooled_keys), rng, reps)
        corr = float(np.corrcoef(h_d, mp_d)[0, 1]) if np.std(mp_d) > 0 else float("nan")
        L.append("| pooled (item FE) | %d | %s | [%s, %s] | 0 | %s | | |" % (len(pooled_keys), fmt(b), fmt(ci[0]), fmt(ci[1]), fmt(corr)))
        summary["flat_pooled"] = b
    L.append("")

    # H2a lambda and H2b compression on the plain prompt
    L += ["### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale", "",
          "| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |",
          "|---|---|---|---|---|---|---|---|"]
    for scope in ["pooled"] + ITEMS:
        keys = [k for k in pairs if (scope == "pooled" or k[0] == scope) and (k[0], k[1], "plain") in med]
        if len(keys) < 5:
            continue
        mp = logit([med[(k[0], k[1], "plain")] for k in keys])
        h = logit([pairs[k]["H"] for k in keys])
        t = logit([pairs[k]["T"] for k in keys])
        lam, _ = ols(h - t, mp - t)
        ci = boot(lambda idx: ols((h - t)[idx], (mp - t)[idx])[0], len(keys), rng, reps)
        bm, am = ols(t, mp)
        bh, ah = ols(t, h)
        L.append("| %s | %d | %s | [%s, %s] | %s | %s | %s | %s |" % (scope, len(keys), fmt(lam), fmt(ci[0]), fmt(ci[1]), fmt(bm), fmt(am), fmt(bh), fmt(ah)))
        if scope == "pooled":
            summary["lambda"] = lam
            summary["slope_model"] = bm
            summary["slope_human"] = bh
    L.append("")

    # H3 knowing vs saying (percent points)
    L += ["### H3 knowing vs saying (percent points)", "", "| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |", "|---|---|---|---|---|---|---|"]
    for scope in ["pooled"] + ITEMS:
        keys = [k for k in pairs if (scope == "pooled" or k[0] == scope) and all((k[0], k[1], p) in med for p in ["plain", "official", "public_guess"])]
        if len(keys) < 5:
            continue
        H = np.array([pairs[k]["H"] for k in keys]); T = np.array([pairs[k]["T"] for k in keys])
        Mo = np.array([med[(k[0], k[1], "official")] for k in keys]); Mp = np.array([med[(k[0], k[1], "public_guess")] for k in keys]); Ml = np.array([med[(k[0], k[1], "plain")] for k in keys])
        gap = np.abs(H - T) >= 3
        s = np.median((Ml[gap] - T[gap]) / (H[gap] - T[gap])) if gap.sum() >= 3 else float("nan")
        L.append("| %s | %d | %s | %s | %s | %s | %s |" % (scope, len(keys), fmt(np.mean(np.abs(Mo - T)), 1), fmt(np.mean(np.abs(Mp - H)), 1), fmt(np.mean(np.abs(Ml - T)), 1), fmt(np.mean(np.abs(Ml - H)), 1), fmt(s)))
        if scope == "pooled":
            summary["official_err"] = float(np.mean(np.abs(Mo - T)))
            summary["public_err"] = float(np.mean(np.abs(Mp - H)))
            summary["s_plain"] = float(s)
    L.append("")

    # memory check
    L += ["### Memorization check (memory_check prompt vs Ipsos H)", "", "| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |", "|---|---|---|---|---|"]
    for scope in ["pooled"] + ITEMS:
        keys = [k for k in pairs if (scope == "pooled" or k[0] == scope) and (k[0], k[1], "memory_check") in med]
        if len(keys) < 5:
            continue
        H = np.array([pairs[k]["H"] for k in keys]); Mm = np.array([med[(k[0], k[1], "memory_check")] for k in keys])
        w2 = float(np.mean(np.abs(Mm - H) <= 2)); w5 = float(np.mean(np.abs(Mm - H) <= 5))
        corr = float(np.corrcoef(Mm, H)[0, 1]) if np.std(Mm) > 0 else float("nan")
        L.append("| %s | %d | %.0f%% | %.0f%% | %s |" % (scope, len(keys), 100 * w2, 100 * w5, fmt(corr)))
        if scope == "pooled":
            summary["memory_within2"] = w2
    L.append("")
    return L, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(ROOT, "results", "results.jsonl"))
    ap.add_argument("--pairs", default=os.path.join(ROOT, "data", "pairs.csv"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "metrics.md"))
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    pairs = load_pairs(args.pairs)
    cells, status = load_results(args.results)
    models = sorted({k[0] for k in cells})
    lines = ["# v0 metrics", "", "Source: `%s` (%d pairs with truth). Cell value = median of parsed samples. Log-odds clip = %g." % (os.path.relpath(args.results, ROOT), len(pairs), CLIP), "",
             "Flattening (\"flatten slope\" columns): slope of logit(M_public) on logit(H) across countries. A slope below 1 means the "
             "model's simulated public varies less across countries than the real public. The H1a variance ratio can exceed 1 even "
             "when answers are flat, because the model tracks a truth that varies more across countries than human guesses do; the "
             "slope is the direct flattening measure. The pooled slope demeans within item (item fixed effects).", ""]
    summaries = []
    for m in models:
        L, s = model_metrics(m, cells, status, pairs, rng, args.boot)
        lines += L
        summaries.append(s)
    head = ["| model | VR wealth | VR immigrants | VR Muslim | flatten slope wealth | flatten slope immigrants | flatten slope Muslim | flatten slope pooled | lambda | model slope | human slope | abs(M_official - T) | abs(M_public - H) | s(M_plain) | memory within 2 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        head.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            s["model"], fmt(s.get("VR_wealth_top1")), fmt(s.get("VR_immigrant_share")), fmt(s.get("VR_muslim_share")),
            fmt(s.get("flat_wealth_top1")), fmt(s.get("flat_immigrant_share")), fmt(s.get("flat_muslim_share")), fmt(s.get("flat_pooled")),
            fmt(s.get("lambda")), fmt(s.get("slope_model")), fmt(s.get("slope_human")), fmt(s.get("official_err"), 1), fmt(s.get("public_err"), 1), fmt(s.get("s_plain")),
            "n/a" if s.get("memory_within2") is None else "%.0f%%" % (100 * s["memory_within2"])))
    lines = lines[:6] + ["## Summary", ""] + head + [""] + lines[6:]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(head))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
