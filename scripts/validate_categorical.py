"""Validation checks for the categorical fact-question track (data/categorical/). Prints a report and writes
it into data/categorical/README.md between the <!-- validation:start --> and <!-- validation:end --> markers.

Checks (no raw files needed; everything is read from the committed CSVs):
  1. every row's option shares plus pct_dk sum to 100 within rounding (+-1 for whole-percent tables, +-2 for the
     climate stacked-bar distributions, which round each segment separately)
  2. pct_correct equals the share on truth_option (sum over the options in truth_option); exact for Eurobarometer and
     Gapminder, within 2 points for the 5 climate items whose distribution comes from the supplement while
     pct_correct comes from Figure 6 (the gaps are listed)
  3. countries per item and items per source; rows without a truth (the flagged item)
  4. rows where the public majority is wrong: an option has more than half of all answers and it is not the truth
     (the inheritance test cases); also the softer count of rows where fewer than half answer correctly
  5. wording, options and truth in items_categorical.yaml match pairs_categorical_v1.csv
  6. Eurobarometer truth-coding check: the workbooks' own 'Average of correct answers' sheets (EB 522 QC5_5,
     EB 104 SD20aR1) must equal the mean of pct_correct over the items of that question, per country
  7. transcription agreement: Figure 6 pass 1 (pdftotext -layout) vs pass 2 (pdftotext -raw); supplement pass 1 vs
     pass 2 and how each cell was resolved; Gapminder text layer vs the visual pass; the supplement distributions vs
     the Figure 6 indicator they should reproduce; Gapminder printed 'Average' vs the mean of the 7 countries
  8. countries_extra.csv covers every country in pairs_categorical_v1.csv that is not in data/countries.csv;
     income groups; missing GDP / web presence
  9. field hygiene: fieldwork dates are YYYY-MM-DD or YYYY-MM; n_country present except for Gapminder
Run: python3 -I scripts/validate_categorical.py
"""
import csv, json, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
C = os.path.join(D, "categorical")
T = os.path.join(C, "transcription")


def read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truth_set(r):
    return [t.strip() for t in r["truth_option"].split(" | ")] if r["truth_option"] else []


def main():
    out = []
    pairs = read(os.path.join(C, "pairs_categorical_v1.csv"))
    for r in pairs:
        r["_opts"] = json.loads(r["options"]); r["_p"] = json.loads(r["pct_per_option"])
    by_source = defaultdict(list)
    for r in pairs:
        by_source[r["source_id"]].append(r)
    clim_dist = {r["item_id"] for r in pairs if r["source_id"].startswith("climate") and len(r["_opts"]) > 2}

    # 1. sums
    bad = []
    for r in pairs:
        tol = 2 if r["item_id"] in clim_dist else 1
        s = sum(r["_p"].values()) + (float(r["pct_dk"]) if r["pct_dk"] != "" else 0)
        if abs(s - 100) > tol:
            bad.append((r["item_id"], r["country_iso3"], s))
        if set(r["_p"]) != set(r["_opts"]) - {"Don't know"}:
            bad.append((r["item_id"], r["country_iso3"], "options/pct keys differ"))
    out.append(f"1. Sum check: {len(pairs)} rows; shares (+ don't know) outside 100 +- rounding: {bad or 'none'}.")

    # 2. pct_correct vs truth share
    gaps, exact_bad = [], []
    for r in pairs:
        ts = truth_set(r)
        if not ts:
            continue
        share = sum(r["_p"][t] for t in ts)
        diff = float(r["pct_correct"]) - share
        if r["item_id"] in clim_dist:
            if abs(diff) > 2:
                exact_bad.append((r["item_id"], r["country_iso3"], r["pct_correct"], share))
            elif diff != 0:
                gaps.append((r["item_id"], r["country_iso3"], int(float(r["pct_correct"])), share))
        elif diff != 0:
            exact_bad.append((r["item_id"], r["country_iso3"], r["pct_correct"], share))
    out.append(f"2. pct_correct equals the share on truth_option: violations {exact_bad or 'none'}.")
    out.append(f"   Climate items with a supplement distribution: pct_correct (Figure 6) differs from the summed supplement shares by 1-2 points in {len(gaps)} of {sum(1 for r in pairs if r['item_id'] in clim_dist)} rows: {gaps}")

    # 3. coverage
    cpi = Counter(r["item_id"] for r in pairs)
    ips = {s: len({r["item_id"] for r in rows}) for s, rows in by_source.items()}
    cps = {s: len({r["country_iso3"] for r in rows}) for s, rows in by_source.items()}
    notruth = sorted({r["item_id"] for r in pairs if not r["truth_option"]})
    out.append(f"3. Items per source: {ips}; countries per source: {cps}.")
    out.append(f"   Countries per item: {dict(cpi)}")
    out.append(f"   Items without an assigned truth (kept with include_in_main = false): {notruth}")

    # 4. majority wrong
    wrong = [r for r in pairs if r["truth_option"] and r["public_majority_option"] != "no_majority" and r["public_majority_option"] not in truth_set(r)]
    minority_correct = [r for r in pairs if r["truth_option"] and float(r["pct_correct"]) < 50]
    out.append(f"4. Rows where the public majority (an option above 50% of all answers) is wrong: {len(wrong)} of {sum(1 for r in pairs if r['truth_option'])} rows with a truth.")
    by_item = defaultdict(list)
    for r in wrong:
        by_item[r["item_id"]].append(r["country_iso3"])
    for item in sorted(by_item, key=lambda i: -len(by_item[i])):
        out.append(f"   {item}: {len(by_item[item])} countries ({', '.join(by_item[item])})")
    out.append(f"   Rows where fewer than half answer correctly (no single wrong option need exceed 50%): {len(minority_correct)}; per item: "
               f"{dict(Counter(r['item_id'] for r in minority_correct))}")
    out.append(f"   Rows with no majority option: {sum(1 for r in pairs if r['public_majority_option'] == 'no_majority')}")

    # 5. yaml consistency (substring checks; no yaml module in the plain-Python toolchain)
    ytxt = open(os.path.join(C, "items_categorical.yaml"), encoding="utf-8").read()
    yitems = re.findall(r"^  - item_id: (\S+)", ytxt, flags=re.M)
    first = {}
    for r in pairs:
        first.setdefault(r["item_id"], r)
    miss = [i for i in first if i not in yitems] + [i for i in yitems if i not in first]
    nomatch = [i for i, r in first.items() if json.dumps(r["question_wording"], ensure_ascii=False) not in ytxt
               or json.dumps(r["_opts"], ensure_ascii=False) not in ytxt or json.dumps(r["truth_option"], ensure_ascii=False) not in ytxt]
    excluded = re.findall(r"^  - item_id: (\S+)\n(?:    .*\n)*?    include_in_main: false", ytxt, flags=re.M)
    out.append(f"5. items_categorical.yaml: {len(yitems)} items; missing/extra vs pairs: {miss or 'none'}; wording/options/truth not found verbatim: {nomatch or 'none'}; include_in_main = false: {excluded}.")

    # 6. Eurobarometer truth-coding check against the workbooks' average-of-correct-answers sheets
    eb = read(os.path.join(T, "eurobarometer_true_false.csv"))
    summary = {(r["source_id"], r["country_iso3"]): int(r["pct_true_or_correct"]) for r in eb if r["row_type"] == "summary"}
    out.append("6. Eurobarometer truth coding vs the workbooks' 'Average of correct answers' sheets (EB 522 QC5_5 over QC5.1-4; EB 104 SD20aR1 over SD20a.1-3):")
    for src in ("eb522_volume_a", "eb104_volume_a"):
        rows = [r for r in by_source[src] if r["truth_option"]]
        per_c = defaultdict(list)
        for r in rows:
            per_c[r["country_iso3"]].append(float(r["pct_correct"]))
        diffs = {c: round(sum(v) / len(v) - summary[(src, c)], 1) for c, v in per_c.items() if (src, c) in summary}
        big = {c: d for c, d in diffs.items() if abs(d) > 1}
        out.append(f"   {src}: {len(diffs)} countries compared; max |mean(pct_correct) - sheet| = {max(abs(d) for d in diffs.values()):.1f} points; countries over 1 point: {big or 'none'}")
    out.append("   eb516_volume_a: the workbook has no average-of-correct-answers sheet (QA20T gives only a grouped count), so the QA20 coding is not machine-checked.")

    # 7. transcription agreement
    f1 = {(r["item_id"], r["column"]): r["pct_correct"] for r in read(os.path.join(T, "climate_fig6_pass1_layout.csv"))}
    f2 = {(r["item_id"], r["column"]): r["pct_correct"] for r in read(os.path.join(T, "climate_fig6_pass2_raw.csv"))}
    fdis = [k for k in f1 if f1[k] != f2.get(k)]
    out.append(f"7. Transcription agreement.")
    out.append(f"   Figure 6: {len(f1)} cells (14 rows x 22 columns incl. the two group averages); pass 1 (-layout) vs pass 2 (-raw) disagreements: {len(fdis)} {fdis or ''}")
    supp = read(os.path.join(T, "climate_supplement_distributions.csv"))
    cells = {}
    for r in supp:
        cells.setdefault((r["country_iso3"], r["panel"]), r)
    res = Counter(r["resolution"].split(":")[0] for r in cells.values())
    p1ok = sum(1 for r in cells.values() if r["pass1_result"] == "ok"); p2ok = sum(1 for r in cells.values() if r["pass2_result"] == "ok")
    nontrivial = [(k, r["pass1_layout_tokens"], r["pass1_result"], r["pass2_raw_tokens"], r["pass2_result"], r["resolution"])
                  for k, r in cells.items() if r["pass1_result"] != "ok" or r["pass2_result"] != "ok"]
    out.append(f"   Supplement: {len(cells)} panel cells (20 countries x 5 panels, {len(supp)} values); pass 1 clean: {p1ok}, pass 2 clean: {p2ok}; resolution: {dict(res)}.")
    for k, t1, r1, t2, r2, how in nontrivial:
        out.append(f"     {k[0]} panel {k[1]}: layout '{t1}' -> {r1}; raw '{t2}' -> {r2}; used: {how}")
    # supplement vs Figure 6
    fig6 = {(r["item_id"], r["column"]): int(r["pct_correct"]) for r in read(os.path.join(T, "climate_fig6_pass1_layout.csv"))}
    dist = defaultdict(dict)
    for r in supp:
        dist[(r["country_iso3"], r["panel"])][r["option"]] = int(r["pct"])
    comp = {"A": ("clim_cc_real_anthropogenic", ["A lot", "Most"]), "B": ("clim_halving_insufficient", ["No"]),
            "D_droughts": ("clim_droughts_likely", ["Very likely", "Somewhat likely"]), "D_sea": ("clim_sea_level_likely", ["Very likely", "Somewhat likely"]),
            "D_volcanic": ("clim_volcanic_unlikely", ["Somewhat unlikely", "Very unlikely"])}
    for panel, (item, opts) in comp.items():
        d = {iso: sum(dist[(iso, panel)][o] for o in opts) - fig6[(item, iso)] for (iso, p) in dist if p == panel}
        out.append(f"   Supplement panel {panel} vs Figure 6 '{item}': diff (supplement - figure) by country: {dict(sorted(d.items()))}; max |diff| {max(abs(v) for v in d.values())}")
    g1 = read(os.path.join(T, "gapminder_pass1_textlayer.csv"))
    g2 = {(r["item_id"], r["country"], r["option"]): r["pct"] for r in read(os.path.join(T, "gapminder_pass2_visual.csv"))}
    gblank = sorted({(r["item_id"], r["country"], r["flag"]) for r in g1 if r["pct"] == ""})
    gdis = [(r["item_id"], r["country"], r["option"], r["pct"], g2[(r["item_id"], r["country"], r["option"])]) for r in g1 if r["pct"] != "" and r["pct"] != g2[(r["item_id"], r["country"], r["option"])]]
    gflag = sorted({(r["item_id"], r["country"], r["flag"]) for r in g1 if r["flag"] and r["pct"] != ""})
    out.append(f"   Gapminder: {len(g1)} cells (9 questions x 8 rows incl. 'Average' x 3 options); text layer vs visual pass disagreements: {len(gdis)} {gdis or ''}; cells the text layer left blank (filled from the visual pass): {gblank or 'none'}; cells with a text-layer note: {gflag or 'none'}")
    # Gapminder printed average vs mean of countries
    gm = defaultdict(dict)
    for (item, country, option), v in g2.items():
        gm[(item, option)][country] = int(v)
    avg_gap = {}
    for (item, option), d in gm.items():
        m = sum(v for c, v in d.items() if c != "Average") / 7
        avg_gap[(item.split("_")[1], option)] = round(m - d["Average"], 1)
    out.append(f"   Gapminder printed 'Average' vs unweighted mean of the 7 countries: max |diff| = {max(abs(v) for v in avg_gap.values()):.1f} points (cells over 1 point: {dict((k, v) for k, v in avg_gap.items() if abs(v) > 1) or 'none'})")

    # 8. countries
    base = {r["country_iso3"] for r in read(os.path.join(D, "countries.csv"))}
    extra = {r["country_iso3"]: r for r in read(os.path.join(C, "countries_extra.csv"))}
    need = sorted({r["country_iso3"] for r in pairs} - base)
    missing = [c for c in need if c not in extra]
    out.append(f"8. countries_extra.csv: {len(extra)} rows; countries in pairs not in data/countries.csv: {len(need)}; missing from countries_extra.csv: {missing or 'none'}; "
               f"income groups: {dict(Counter(r['wb_income_group'] for r in extra.values()))}; GDP missing: {[c for c, r in extra.items() if r['gdp_pcap_ppp'] == ''] or 'none'}; "
               f"web presence missing: {[c for c, r in extra.items() if r['enwiki_mentions'] == ''] or 'none'}.")

    # 9. hygiene
    datebad = [(r["item_id"], r["country_iso3"]) for r in pairs if not all(re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", r[k]) for k in ("fieldwork_start", "fieldwork_end"))]
    nbad = [(r["source_id"]) for r in pairs if r["n_country"] == "" and r["source_id"] != "gapminder_refugee_2023_report"]
    out.append(f"9. Fieldwork dates malformed: {datebad or 'none'}; n_country blank outside Gapminder: {sorted(set(nbad)) or 'none'}; "
               f"Gapminder rows (n_country blank by design, total n = 1,632 over 7 countries): {len(by_source['gapminder_refugee_2023_report'])}.")

    report = "\n".join(out)
    print(report)
    readme = os.path.join(C, "README.md")
    if os.path.exists(readme):
        txt = open(readme, encoding="utf-8").read()
        if "<!-- validation:start -->" in txt:
            new = re.sub(r"<!-- validation:start -->.*?<!-- validation:end -->",
                         lambda m: "<!-- validation:start -->\n```\n" + report + "\n```\n<!-- validation:end -->", txt, flags=re.S)
            open(readme, "w", encoding="utf-8").write(new)
            print("\n(README validation section updated)")
    if bad or exact_bad or miss or nomatch or missing or datebad or nbad or fdis or gdis:
        sys.exit("validation found problems")


if __name__ == "__main__":
    main()
