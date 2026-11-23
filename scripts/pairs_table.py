"""Per-pair results table per model: country, public guess H, truth T, and the model's median
parsed answer for each prompt type. Writes results/<model_id>_pairs.md for every model found in the
results file (or those given with --models). Medians are over the parsed ("ok") samples of a cell.
Run: python3 scripts/pairs_table.py [--results results/results.jsonl] [--models a,b]
"""
import argparse, csv, json, os, statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = ["plain", "official", "public_guess", "memory_check"]
LABEL = {"immigrant_share": "Immigrants", "muslim_share": "Muslims", "wealth_top1": "Wealth top 1%"}


def fmt(x):
    if x is None:
        return ""
    return "%.1f" % x if (x < 10 and x != int(x)) else "%d" % round(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(ROOT, "results", "results.jsonl"))
    ap.add_argument("--pairs", default=os.path.join(ROOT, "data", "pairs.csv"))
    ap.add_argument("--models", help="comma-separated model_id list (default: all in the results file)")
    args = ap.parse_args()
    pairs = {(r["item_id"], r["country_iso3"]): r for r in csv.DictReader(open(args.pairs, encoding="utf-8"))}
    cells = defaultdict(list)
    for line in open(args.results, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("parse_status") == "ok":
            cells[(r["model_id"], r["item_id"], r["country_iso3"], r["prompt_type"])].append(float(r["parsed_value"]))
    models = args.models.split(",") if args.models else sorted({k[0] for k in cells})
    for m in models:
        out = ["# %s per-pair results" % m, "", "Median of parsed samples per cell; H = Ipsos average guess, T = truth used in data/pairs.csv.", ""]
        for item in ["immigrant_share", "muslim_share", "wealth_top1"]:
            rows = sorted((r for (it, _), r in pairs.items() if it == item), key=lambda r: r["country_name_ipsos"])
            out += ["**%s**" % LABEL.get(item, item), "", "| Country | Public guess H | Truth T | " + " | ".join(PROMPTS) + " |",
                    "|---|---|---|" + "---|" * len(PROMPTS)]
            for r in rows:
                vals = []
                for p in PROMPTS:
                    v = cells.get((m, item, r["country_iso3"], p))
                    vals.append(statistics.median(v) if v else None)
                T = float(r["t_value"])
                out.append("| %s | %s | %s | %s |" % (r["country_name_ipsos"], fmt(float(r["h_mean"])), "%.1f" % T if T < 10 else "%d" % round(T),
                                                   " | ".join(fmt(v) for v in vals)))
            out.append("")
        path = os.path.join(ROOT, "results", "%s_pairs.md" % m)
        open(path, "w", encoding="utf-8").write("\n".join(out))
        print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
