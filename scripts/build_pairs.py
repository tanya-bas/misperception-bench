"""Build data/pairs.csv and data/pairs_categorical.csv from the hand transcription of the
Ipsos Perils of Perception 2024 report (data/raw/ipsos-perils-of-perception-2024.pdf).

Inputs (all hand-transcribed, committed, with page numbers):
  data/transcription/ipsos_2024_estimates.csv    average guess and printed actual, p13 / p16 / p20
  data/transcription/homicide_p22.csv            public answer distribution, p22
  data/transcription/homicide_actual_p23_24.csv  actual direction (Ipsos text p11, scatter p23-24)

The transcription was checked on 2026-11-22 by an independent second reading of p14, p17
and p20; all 90 cells agreed, and the second reading was deleted afterwards (data/README.md).

Truth columns (rule adopted 2026-11-22):
  t_value_ipsos   the figure exactly as printed in the report ("35%", "0%", "<1%", "No data available")
  t_value         numeric truth used in analysis
  t_flag          as_printed            t_value is the printed number
                  world_bank            immigrant_share only (decision 2026-11-22): t_value is the World Bank
                                        WDI SM.POP.TOTL.ZS value from data/countries.csv (UN DESA series,
                                        unrounded, year in t_reference_year); the printed figure stays in
                                        t_value_ipsos
                  pew_2020              muslim_share only (decision 2026-11-22): t_value is Pew's 2020
                                        estimate from the June 2025 "Religious Composition of the World's
                                        Population 2010-2020" release, read from
                                        data/validation/truth_crosscheck.csv (rows whose source_name is
                                        PEW_2020_SOURCE and source_year is 2020); printed figure stays in
                                        t_value_ipsos
                  wid_2024              wealth_top1 only (decision 2026-11-22): t_value is the World Inequality
                                        Database top-1% share of net personal wealth, 2024 (WID 2026 release
                                        via the Our World in Data mirror), read from
                                        data/validation/truth_crosscheck.csv (rows whose source_name is
                                        WID_2024_SOURCE); fills Peru, which the report prints as
                                        "No data available"; printed figure stays in t_value_ipsos
                  as_printed / missing  no longer produced by any v0 item; kept as the fallback for items
                                        without a primary-source rule
  No row carries a placeholder: every t_value is a real number.
Run: python3 -I scripts/build_pairs.py
"""
import csv, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")

WAVE = "ipsos_2024"
SOURCE_ID = "ipsos_perils_2024_report"
FIELDWORK = ("2024-09-20", "2024-10-04")

# Verbatim wordings and T sources. Must match data/items.yaml (validate.py checks). Pages come from the transcription files.
ITEMS = {
    "wealth_top1": dict(
        wording="What percentage of your country's total household wealth do you think is owned by the top 1% of richest households?",
        t_source="World Inequality Database, top 1% share of net personal wealth, 2024 (WID 2026 release via Our World in Data mirror)",
        definition_match="approximate",
        definition_note="question says households; WID top-1% wealth share is adult-based (equal-split); Ipsos cites WID, T taken from the current WID 2024 value for every country (decision 2026-11-22)"),
    "immigrant_share": dict(
        wording="What percentage of your country's population do you think immigrants (i.e., people born in another country) represent?",
        t_source="World Bank WDI SM.POP.TOTL.ZS (UN DESA International Migrant Stock)", definition_match="yes",
        definition_note="foreign-born in both question and source; Ipsos cites UN International Migrant Stock, T taken from the World Bank copy of the same series (decision 2026-11-22)"),
    "muslim_share": dict(
        wording="In your country, out of 100 people, how many do you think are Muslim?",
        t_source="Pew Research Center, Religious Composition of the World's Population 2010-2020 (June 2025), 2020 estimate",
        definition_match="yes",
        definition_note="share of population Muslim in both question and source; Ipsos cites Pew, T taken from Pew's 2020 estimate in the June 2025 release for every country (decision 2026-11-22)"),
}

# Per-row overrides of the definition columns (checked against the sources in data/validation/truth_crosscheck.csv).
DEFINITION_OVERRIDES = {
    ("wealth_top1", "Peru"): ("approximate", "question says households; WID top-1% wealth share is adult-based (equal-split); WID marks Peru as modeled, and the Ipsos report prints 'No data available' for it"),
    ("immigrant_share", "India"): ("approximate", "question says foreign-born; UN DESA derives India's migrant stock from foreign-citizen data rather than place of birth (World Bank copy of the same series)"),
    ("immigrant_share", "Indonesia"): ("approximate", "question says foreign-born; UN DESA derives Indonesia's migrant stock from foreign-citizen data rather than place of birth (World Bank copy of the same series)"),
}

# Exact source_name of the Pew 2020 rows in data/validation/truth_crosscheck.csv (the same file also holds
# the 2010 column of the 2025 release and the 2010 column of the 2015 release; neither is used).
WID_2024_SOURCE = "World Inequality Database (WID.world) 2026 release, top 1% share of net personal wealth, as mirrored by Our World in Data (interpolations/extrapolations excluded)"
PEW_2020_SOURCE = "Pew Research Center, Religious Composition by Country 2010-2020 (June 2025 release; country table embedded in the interactive page), Muslims % 2020"

# Country metadata from the methodology page (p38). n is "approximately" as Ipsos states it.
# representative: Ipsos's own statement; Ireland and New Zealand are named in neither p38 list and are
# treated as representative by author decision 2026-11-22.
COUNTRIES = {
    # name_ipsos: (iso3, n_approx, age_range, representative)
    "Argentina": ("ARG", 500, "16-74", "yes"), "Australia": ("AUS", 1000, "16-74", "yes"),
    "Belgium": ("BEL", 500, "16-74", "yes"), "Brazil": ("BRA", 1000, "16-74", "no_urban_educated_affluent"),
    "Canada": ("CAN", 1000, "18-74", "yes"), "Chile": ("CHL", 500, "16-74", "no_urban_educated_affluent"),
    "Colombia": ("COL", 500, "16-74", "no_urban_educated_affluent"), "France": ("FRA", 1000, "16-74", "yes"),
    "Germany": ("DEU", 1000, "16-74", "yes"), "Great Britain": ("GBR", 1000, "16-74", "yes"),
    "Hungary": ("HUN", 500, "16-74", "yes"), "India": ("IND", 2000, "18+", "no_urban_subset"),
    "Indonesia": ("IDN", 500, "21-74", "no_urban_educated_affluent"), "Ireland": ("IRL", 500, "16-74", "yes"),
    "Italy": ("ITA", 1000, "16-74", "yes"), "Japan": ("JPN", 1000, "16-74", "yes"),
    "Malaysia": ("MYS", 500, "18-74", "no_urban_educated_affluent"), "Mexico": ("MEX", 500, "16-74", "no_urban_educated_affluent"),
    "Netherlands": ("NLD", 500, "16-74", "yes"), "New Zealand": ("NZL", 1000, "16-74", "yes"),
    "Peru": ("PER", 500, "16-74", "no_urban_educated_affluent"), "Poland": ("POL", 500, "16-74", "yes"),
    "Singapore": ("SGP", 500, "21-74", "no_urban_educated_affluent"), "South Africa": ("ZAF", 500, "18-74", "no_urban_educated_affluent"),
    "South Korea": ("KOR", 500, "16-74", "yes"), "Spain": ("ESP", 1000, "16-74", "yes"),
    "Sweden": ("SWE", 500, "16-74", "yes"), "Thailand": ("THA", 500, "20-74", "no_urban_educated_affluent"),
    "Türkiye": ("TUR", 500, "18-74", "no_urban_educated_affluent"), "United States": ("USA", 1000, "18-74", "yes"),
}


def read(name):
    with open(os.path.join(D, "transcription", name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def printed(raw):
    """Reconstruct the cell exactly as printed: '35' -> '35%', '<1' -> '<1%', text unchanged."""
    raw = raw.strip()
    return raw if raw.lower() in ("no data available", "n/a") or raw.endswith("%") else raw + "%"


def truth(item, country, raw, pew, wdi, wid):
    """Return a dict of the truth columns for one pair (see module docstring)."""
    raw = raw.strip()
    base = {"t_value_ipsos": printed(raw), "t_unrounded_source": "", "t_unrounded_url": "", "t_unrounded_year": "",
            "t_reference_year": ""}
    iso3 = COUNTRIES[country][0]
    if item == "immigrant_share":
        # World Bank series is T for this item regardless of what Ipsos printed (decision 2026-11-22).
        w = wdi[iso3]
        if w["migrant_stock_pct_wdi"] == "":
            sys.exit(f"no World Bank migrant stock value in countries.csv for {country}")
        return {**base, "t_value": float(w["migrant_stock_pct_wdi"]), "t_flag": "world_bank",
                "t_reference_year": w["migrant_stock_pct_year"]}
    if item == "wealth_top1":
        # WID 2024 value is T for this item regardless of what Ipsos printed (decision 2026-11-22).
        if iso3 not in wid:
            sys.exit(f"no WID 2024 value in truth_crosscheck.csv for {country}")
        return {**base, "t_value": float(wid[iso3]), "t_flag": "wid_2024", "t_reference_year": "2024"}
    if item == "muslim_share":
        # Pew 2020 estimate is T for this item regardless of what Ipsos printed (decision 2026-11-22).
        if iso3 not in pew:
            sys.exit(f"no Pew 2020 value in truth_crosscheck.csv for {country}")
        return {**base, "t_value": float(pew[iso3]), "t_flag": "pew_2020", "t_reference_year": "2020"}
    if raw.lower() in ("no data available", "n/a", ""):
        return {**base, "t_value": "", "t_flag": "missing"}
    if raw == "<1" or float(raw) == 0:
        sys.exit(f"{item} / {country}: report prints a rounded zero and no rule exists for this item")
    return {**base, "t_value": float(raw), "t_flag": "as_printed"}


def main():
    p1 = {(r["item_id"], r["country"]): r for r in read("ipsos_2024_estimates.csv")}
    if set(c for _, c in p1) != set(COUNTRIES):
        sys.exit(f"country set mismatch: {set(c for _, c in p1) ^ set(COUNTRIES)}")

    with open(os.path.join(D, "countries.csv"), encoding="utf-8") as f:
        wdi = {r["country_iso3"]: r for r in csv.DictReader(f)}
    with open(os.path.join(D, "validation", "truth_crosscheck.csv"), encoding="utf-8") as f:
        pew = {r["country_iso3"]: r["candidate_value"] for r in csv.DictReader(f)
               if r["item_id"] == "muslim_share" and r["source_year"] == "2020" and r["source_name"] == PEW_2020_SOURCE}
    if len(pew) != 30:
        sys.exit(f"expected 30 Pew 2020 muslim_share rows in truth_crosscheck.csv, found {len(pew)}")
    with open(os.path.join(D, "validation", "truth_crosscheck.csv"), encoding="utf-8") as f:
        wid = {r["country_iso3"]: r["candidate_value"] for r in csv.DictReader(f)
               if r["item_id"] == "wealth_top1" and r["source_year"] == "2024" and r["source_name"] == WID_2024_SOURCE}
    if len(wid) != 30:
        sys.exit(f"expected 30 WID 2024 wealth_top1 rows in truth_crosscheck.csv, found {len(wid)}")
    rows = []
    for (item, country), r in sorted(p1.items()):
        iso3, n, age, rep = COUNTRIES[country]
        meta = ITEMS[item]
        t = truth(item, country, r["t_raw"], pew, wdi, wid)
        defn_match, defn_note = DEFINITION_OVERRIDES.get((item, country), (meta["definition_match"], meta["definition_note"]))
        rows.append({
            "wave": WAVE, "source_id": SOURCE_ID,
            "country_name_ipsos": country, "country_iso3": iso3, "item_id": item,
            "h_mean": float(r["h_mean"]), "h_stat": "mean (Ipsos 'Average % mentioned')",
            "t_value_ipsos": t["t_value_ipsos"], "t_value": t["t_value"], "t_flag": t["t_flag"],
            "t_unrounded_source": t["t_unrounded_source"], "t_unrounded_url": t["t_unrounded_url"],
            "t_unrounded_year": t["t_unrounded_year"],
            "t_source": meta["t_source"], "t_reference_year": t["t_reference_year"],
            "definition_match": defn_match, "definition_note": defn_note,
            "question_wording": meta["wording"],
            "source_page": r["page"],  # pass-1 page; the two-pass outcome is reported by validate.py, not per row
            "fieldwork_start": FIELDWORK[0], "fieldwork_end": FIELDWORK[1],
            "n_country_approx": n, "age_range": age, "representative_sample": rep,
        })
    out = os.path.join(D, "pairs.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("wrote", out, len(rows), "rows")

    # Categorical side table: homicide trend.
    actual = {r["country"]: r for r in read("homicide_actual_p23_24.csv")}
    crow = []
    for r in read("homicide_p22.csv"):
        c = r["country"]; iso3, n, age, rep = COUNTRIES[c]
        hi, sa, lo = int(r["pct_higher"]), int(r["pct_same"]), int(r["pct_lower"])
        majority = "higher" if hi > 50 else ("lower" if lo > 50 else ("same" if sa > 50 else "no_majority"))
        plural = max((hi, "higher"), (sa, "same"), (lo, "lower"))[1]
        a = actual[c]
        crow.append({
            "wave": WAVE, "source_id": SOURCE_ID, "country_name_ipsos": c, "country_iso3": iso3,
            "item_id": "homicide_trend",
            "question_wording": "Do you think the homicide rate in your country is higher, lower, or about the same as in 2000?",
            "pct_higher": hi, "pct_same": sa, "pct_lower": lo,
            "public_majority": majority, "public_plurality": plural,
            "actual_direction": a["actual_direction"],
            "approx_change_per_100k_from_chart": a["approx_change_per_100k_from_chart"],
            "actual_direction_source": "Ipsos text p11 ('about the same or lower in all countries except Mexico'); scatter p23-24; underlying source UN Office on Drugs and Crime",
            "chart_page": a["chart_page"], "source_page": 22, "note": a["note"],
            "fieldwork_start": FIELDWORK[0], "fieldwork_end": FIELDWORK[1],
            "n_country_approx": n, "age_range": age, "representative_sample": rep,
        })
    out2 = os.path.join(D, "pairs_categorical.csv")
    with open(out2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(crow[0].keys())); w.writeheader(); w.writerows(crow)
    print("wrote", out2, len(crow), "rows")


if __name__ == "__main__":
    main()
