"""Validation checks for the dataset (waves ipsos_2024 and ipsos_2020). Prints a markdown report and writes it
into data/README.md between the <!-- validation:start --> and <!-- validation:end --> markers.

Checks, per wave where it matters:
  1. percent items: H and T inside [0, 100]; t_flag summary; any T that is 0 or blank (logit undefined)
  2. countries per item and wave; rows without a usable T listed
  3. question wording in pairs.csv appears verbatim in data/items.yaml
  4. every item: Ipsos printed figure (t_value_ipsos) vs the T used (t_value), per country; >2-point gaps listed
  5. definition_match summary per item
  6. stated sample sizes per wave
  7. countries.csv coverage
  8. categorical table per wave; 9. Royaumont T identical to 2024 T
 10. pairs_banded.csv (Earth Day 2022): 31 countries, band percentages sum to about 100, midpoint mean reproduces the deck's all-country mean
Run: python3 -I scripts/validate.py
"""
import csv, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
WAVES = ("ipsos_2024", "ipsos_2020", "ipsos_royaumont_2023")
STATED_INTERVIEWS = {"ipsos_2024": "22,989 interviews stated on p38", "ipsos_2020": "16,000 interviews stated on p53",
                     "ipsos_royaumont_2023": "10,000 interviews stated on p1"}
SAMPLE_ITEM = {"ipsos_2024": "immigrant_share", "ipsos_2020": "deaths_cancer", "ipsos_royaumont_2023": "wealth_top1"}
ITEM_ORDER = {"ipsos_2024": ("wealth_top1", "immigrant_share", "muslim_share"), "ipsos_royaumont_2023": ("wealth_top1", "immigrant_share", "muslim_share")}  # report order of the v0 README; other waves in pairs.csv order
T_NOTE = {
    "ipsos_2024": "T is the World Bank WDI 2024 series (immigrant_share), Pew's 2020 estimate (muslim_share) and WID 2024 (wealth_top1), decisions 2026-11-22; differences reflect the older source vintages Ipsos used and Ipsos rounding to whole percents.",
    "ipsos_royaumont_2023": "T is copied from the ipsos_2024 row of the same country (one vintage per item across waves, decision 2026-11-22); the deck's printed actual (WID, IOM World Migration Report 2022, World Population Review) is kept in t_value_ipsos only.",
    "ipsos_2020": "T is the printed GBD 2017 figure itself (fallback after the Our World in Data pull was refused, decision 2026-11-22), so printed and used differ only where the printed actual is swapped between two adjacent rows (cardiovascular, Saudi Arabia and Germany) or is a rounded 0.0 left blank.",
}


def read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def items_in(rows):
    seen = []
    for r in rows:
        if r["item_id"] not in seen:
            seen.append(r["item_id"])
    return seen


def main():
    out = []
    pairs = read(os.path.join(D, "pairs.csv"))
    pct = [r for r in pairs]  # every pairs.csv row is a percent item
    by_wave = {w: [r for r in pct if r["wave"] == w] for w in WAVES}
    unknown = [r["wave"] for r in pct if r["wave"] not in WAVES]
    if unknown:
        out.append(f"0. UNKNOWN waves in pairs.csv: {sorted(set(unknown))}")

    # 1. ranges
    out.append(f"1. Range check: {len(pct)} rows ({', '.join(f'{w}: {len(by_wave[w])}' for w in WAVES)}).")
    for w in WAVES:
        rows = by_wave[w]
        bad = [r for r in rows if not (0 <= float(r["h_mean"]) <= 100) or (r["t_value"] != "" and not (0 <= float(r["t_value"]) <= 100))]
        zeros = [(r["item_id"], r["country_name_ipsos"], r["t_value_ipsos"]) for r in rows if r["t_value"] in ("0.0", "")]
        flags = Counter((r["item_id"], r["t_flag"]) for r in rows)
        small = [(r["item_id"], r["country_name_ipsos"], r["t_value_ipsos"], r["t_value"]) for r in rows if r["t_value"] != "" and float(r["t_value"]) < 1]
        out.append(f"   {w}: {len(bad)} outside [0,100].")
        out.append(f"   t_flag counts: {dict(flags)}")
        out.append(f"   T zero or blank (logit undefined): {zeros or 'none'}")
        out.append(f"   T below 1 percent (printed figure, T used): {small or 'none'}")

    # 2. coverage
    out.append("2. Countries per item:")
    for w in WAVES:
        cnt = Counter(r["item_id"] for r in by_wave[w])
        miss = [(r["item_id"], r["country_name_ipsos"], r["t_value_ipsos"]) for r in by_wave[w] if r["t_flag"] in ("missing", "source_unrounded_pending")]
        out.append(f"   {w}: {dict(cnt)}. Rows without usable T: {miss or 'none'}")

    # 3. wording consistency with items.yaml
    yaml_text = open(os.path.join(D, "items.yaml"), encoding="utf-8").read()
    wordings = {r["item_id"]: r["question_wording"] for r in pct}
    nomatch = [i for i, w in wordings.items() if w not in yaml_text]
    out.append(f"3. Question wording present verbatim in items.yaml for all {len(wordings)} items: {'yes' if not nomatch else 'NO: ' + str(nomatch)}.")

    # 4. all items: Ipsos printed figure vs the T actually used
    countries = {r["country_iso3"]: r for r in read(os.path.join(D, "countries.csv"))}
    out.append("4. Ipsos printed figure (t_value_ipsos) vs T used (t_value), per item; rows where |printed - T| > 2 points are flagged:")
    for w in WAVES:
        rows = by_wave[w]
        out.append(f"   wave {w}")
        for item in ITEM_ORDER.get(w) or items_in(rows):
            src = next(r["t_source"] for r in rows if r["item_id"] == item)
            out.append(f"   {item} (T source: {src})")
            out.append("   | country | Ipsos printed | T used (year) | printed - T |")
            out.append("   |---|---|---|---|")
            big = []
            for r in sorted((r for r in rows if r["item_id"] == item), key=lambda r: r["country_iso3"]):
                printed = r["t_value_ipsos"].rstrip("%").replace(",", ".")  # the Royaumont deck prints a decimal comma
                if r["t_value"] == "" or not re.fullmatch(r"\d+(\.\d+)?", printed):
                    out.append(f"   | {r['country_name_ipsos']} | {r['t_value_ipsos']} | {r['t_value'] or 'missing'} ({r['t_reference_year']}) | n/a |"); continue
                diff = float(printed) - float(r["t_value"])
                flag = " **>2pp**" if abs(diff) > 2 else ""
                if abs(diff) > 2:
                    big.append(r["country_name_ipsos"])
                out.append(f"   | {r['country_name_ipsos']} | {r['t_value_ipsos']} | {float(r['t_value']):.2f} ({r['t_reference_year']}) | {diff:+.2f}{flag} |")
            out.append(f"   {item}: countries where |printed - T| > 2 points: {len(big)} {big or ''}")
        out.append(f"   {T_NOTE[w]}")

    # 5. definition match
    dm = Counter((r["item_id"], r["definition_match"]) for r in pct)
    out.append(f"5. definition_match per item: {dict(dm)}. 'approximate' = wealth_top1 (households in question, adults in WID), immigrant_share India/Indonesia (citizenship-based stock), and every Hong Kong row of ipsos_2020 (actual from healthyhk.gov.hk, not GBD).")

    # 6. stated sample sizes
    out.append("6. Sum of Ipsos 'approximately' per-country samples (one item per wave; Ipsos rounds per-country n):")
    for w in WAVES:
        rows = by_wave[w]
        item = SAMPLE_ITEM[w]
        ns = [r["n_country_approx"] for r in rows if r["item_id"] == item]
        numeric = [int(n) for n in ns if re.fullmatch(r"\d+", n)]
        out.append(f"   {w} ({item}, {len(ns)} countries): {sum(numeric)} from {len(numeric)} stated n ({len(ns) - len(numeric)} not_stated) vs {STATED_INTERVIEWS[w]}.")

    # 7. countries.csv
    wp_missing = [c for c, r in countries.items() if r["enwiki_mentions"] == ""]
    used = {r["country_iso3"] for r in pct}
    out.append(f"7. countries.csv: {len(countries)} rows; web_presence missing for: {wp_missing or 'none'}; "
               f"income groups: {dict(Counter(r['wb_income_group'] for r in countries.values()))}; "
               f"pairs.csv countries without a countries.csv row: {sorted(used - set(countries)) or 'none'}.")

    # 8. categorical table per wave
    cat = read(os.path.join(D, "pairs_categorical.csv"))
    out.append(f"8. pairs_categorical.csv: {len(cat)} rows; per wave: {dict(Counter(r['wave'] for r in cat))}; "
               f"rows with a determinable public majority: {sum(1 for r in cat if r['public_majority'])}; actual_direction counts: {dict(Counter(r['actual_direction'] for r in cat))}.")

    # 9. cross-wave truth consistency: Royaumont rows must carry the 2024 T of the same country
    t24 = {(r["item_id"], r["country_iso3"]): (r["t_value"], r["t_flag"]) for r in by_wave["ipsos_2024"]}
    mism = [(r["item_id"], r["country_name_ipsos"]) for r in by_wave["ipsos_royaumont_2023"] if t24.get((r["item_id"], r["country_iso3"])) != (r["t_value"], r["t_flag"])]
    out.append(f"9. ipsos_royaumont_2023 T identical to the ipsos_2024 T of the same country for all {len(by_wave['ipsos_royaumont_2023'])} rows: {'yes' if not mism else 'NO: ' + str(mism)}.")

    # 10. banded table (Earth Day 2022)
    banded = read(os.path.join(D, "pairs_banded.csv"))
    sums = {r["country_name_ipsos"]: int(r["pct_sum"]) for r in banded}
    low = {c: v for c, v in sums.items() if v < 95 or v > 103}
    tr = next(r for r in read(os.path.join(D, "transcription", "ipsos_earthday_2022_p21.csv")) if r["code"] == "TOT")
    import json
    mids = json.loads(banded[0]["band_midpoints"]); tot = [int(tr[k]) for k in ("pct_0_075", "pct_1_175", "pct_2_275", "pct_3_4")]
    tot_mean = sum(p * m for p, m in zip(tot, mids)) / sum(tot)
    means = [float(r["h_mean_midpoint"]) for r in banded]
    out.append(f"10. pairs_banded.csv: {len(banded)} rows ({len(set(r['country_iso3'] for r in banded))} countries); waves {dict(Counter(r['wave'] for r in banded))}; "
               f"bands + don't-know sum: min {min(sums.values())}, max {max(sums.values())}; rows outside [95, 103]: {low or 'none'} (the deck prints no further category); "
               f"don't-know blank for: {[r['country_name_ipsos'] for r in banded if r['pct_dk'] == ''] or 'none'}; "
               f"h_mean_midpoint range {min(means):.2f} to {max(means):.2f}; all-country column recomputed with the same midpoints = {tot_mean:.2f} vs 2.1 printed on p20; "
               f"T = {set(r['t_value'] for r in banded)} ({set(r['t_flag'] for r in banded)}), printed {set(r['t_value_ipsos'] for r in banded)}; "
               f"countries without a countries.csv row: {sorted(set(r['country_iso3'] for r in banded) - set(countries)) or 'none'}.")

    report = "\n".join(out)
    print(report)
    readme = os.path.join(D, "README.md")
    if os.path.exists(readme):
        txt = open(readme, encoding="utf-8").read()
        new = re.sub(r"<!-- validation:start -->.*?<!-- validation:end -->",
                     lambda m: "<!-- validation:start -->\n```\n" + report + "\n```\n<!-- validation:end -->", txt, flags=re.S)
        open(readme, "w", encoding="utf-8").write(new)
        print("\n(README validation section updated)")


if __name__ == "__main__":
    main()
