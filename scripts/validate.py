"""Validation checks for the v0 dataset. Prints a markdown report and writes it into
data/README.md between the <!-- validation:start --> and <!-- validation:end --> markers.

Checks:
  1. percent items: H and T inside [0, 100]; t_flag summary; any T that is 0 or blank (logit undefined)
  2. 30 countries per item; missing T listed
  3. question wording in pairs.csv appears verbatim in data/items.yaml
  4. immigrant_share: Ipsos printed figure (t_value_ipsos) vs the World Bank T used (t_value), per country
  5. definition_match summary per item
  6. 2024 vs comparator-wave immigrant-share averages from report p19 (validation artifact only)
Run: python3 -I scripts/validate.py
"""
import csv, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")


def read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    out = []
    pairs = read(os.path.join(D, "pairs.csv"))
    pct = [r for r in pairs]  # all three v0 items are percent items

    # 1. ranges
    bad = [r for r in pct if not (0 <= float(r["h_mean"]) <= 100) or (r["t_value"] != "" and not (0 <= float(r["t_value"]) <= 100))]
    zeros = [(r["item_id"], r["country_name_ipsos"]) for r in pct if r["t_value"] in ("0.0", "")]
    flags = Counter((r["item_id"], r["t_flag"]) for r in pct)
    pend = [(r["item_id"], r["country_name_ipsos"]) for r in pct if r["t_flag"] == "source_unrounded_pending"]
    out.append(f"1. Range check: {len(pct)} rows, {len(bad)} outside [0,100].")
    out.append(f"   t_flag counts: {dict(flags)}")
    out.append(f"   T zero or blank (logit undefined): {zeros or 'none'}; source_unrounded_pending: {pend or 'none'}")
    unr = [(r["item_id"], r["country_name_ipsos"], r["t_value_ipsos"], r["t_value"]) for r in pct if r["t_flag"] == "source_unrounded"]
    out.append(f"   printed vs unrounded for source_unrounded rows: {unr}")

    # 2. coverage
    cnt = Counter(r["item_id"] for r in pct)
    miss = [(r["item_id"], r["country_name_ipsos"], r["t_value_ipsos"]) for r in pct if r["t_flag"] == "missing"]
    out.append(f"2. Countries per item: {dict(cnt)}. Missing T: {miss}")

    # 3. wording consistency with items.yaml
    yaml_text = open(os.path.join(D, "items.yaml"), encoding="utf-8").read()
    wordings = {r["item_id"]: r["question_wording"] for r in pct}
    nomatch = [i for i, w in wordings.items() if w not in yaml_text]
    out.append(f"3. Question wording present verbatim in items.yaml for all items: {'yes' if not nomatch else 'NO: ' + str(nomatch)}.")

    # 4. immigrant_share: Ipsos printed figure vs the World Bank T actually used
    countries = {r["country_iso3"]: r for r in read(os.path.join(D, "countries.csv"))}
    out.append("4. immigrant_share: Ipsos printed figure (t_value_ipsos) vs World Bank WDI T used (t_value):")
    out.append("   | country | Ipsos printed | WDI T (year) | printed - T |")
    out.append("   |---|---|---|---|")
    big = 0
    for r in sorted((r for r in pct if r["item_id"] == "immigrant_share"), key=lambda r: r["country_iso3"]):
        printed = r["t_value_ipsos"].rstrip("%")
        if not re.fullmatch(r"\d+(\.\d+)?", printed):
            out.append(f"   | {r['country_name_ipsos']} | {r['t_value_ipsos']} | {r['t_value']} ({r['t_reference_year']}) | n/a |"); continue
        diff = float(printed) - float(r["t_value"])
        flag = " **>2pp**" if abs(diff) > 2 else ""
        big += abs(diff) > 2
        out.append(f"   | {r['country_name_ipsos']} | {r['t_value_ipsos']} | {float(r['t_value']):.1f} ({r['t_reference_year']}) | {diff:+.1f}{flag} |")
    out.append(f"   Countries where |printed - T| > 2 points: {big}. T is the World Bank series (decision 2026-11-22); differences reflect the UN DESA release Ipsos used and Ipsos rounding to whole percents.")

    # 5. definition match
    dm = Counter((r["item_id"], r["definition_match"]) for r in pct)
    out.append(f"5. definition_match per item: {dict(dm)}. 'approximate' = wealth_top1 (households in question, adults in WID).")

    # 6. comparator artifact
    comp = read(os.path.join(D, "validation", "ipsos_comparator_immigrant_share_p19.csv"))
    diffs = [(r["country"], int(r["avg_guess_2024"]) - int(r["avg_guess_comparator"])) for r in comp]
    out.append(f"6. 2024 vs comparator wave (report p19) immigrant-share average guess, 13 countries: {diffs}.")
    out.append("   Caveat: the p19 legend says 2018 but the base note describes the 2014 wave (14 countries, Aug 2014). Stored under data/validation/, not used in pairs.csv.")

    # sample total
    n_total = sum(int(r["n_country_approx"]) for r in pct if r["item_id"] == "immigrant_share")
    out.append(f"7. Sum of Ipsos 'approximately' per-country samples: {n_total} vs 22,989 interviews stated on p38 (Ipsos rounds per-country n).")
    wp_missing = [c for c, r in countries.items() if r["enwiki_mentions"] == ""]
    out.append(f"8. countries.csv: {len(countries)} rows; web_presence missing for: {wp_missing or 'none'}; "
               f"income groups: {dict(Counter(r['wb_income_group'] for r in countries.values()))}.")

    report = "\n".join(out)
    print(report)
    readme = os.path.join(D, "README.md")
    if os.path.exists(readme):
        txt = open(readme, encoding="utf-8").read()
        new = re.sub(r"<!-- validation:start -->.*?<!-- validation:end -->",
                     "<!-- validation:start -->\n```\n" + report + "\n```\n<!-- validation:end -->", txt, flags=re.S)
        open(readme, "w", encoding="utf-8").write(new)
        print("\n(README validation section updated)")


if __name__ == "__main__":
    main()
