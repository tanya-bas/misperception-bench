"""Build data/pairs.csv and data/pairs_categorical.csv from the two-pass transcription of the
Ipsos Perils of Perception 2024 report (data/raw/ipsos-perils-of-perception-2024.pdf).

Inputs (all hand-transcribed, committed, with page numbers):
  data/transcription/pass1.csv            first reading of p13 / p16 / p20
  data/transcription/pass2.csv            independent re-reading of p14 / p17 / p20
  data/transcription/homicide_p22.csv     public answer distribution, p22
  data/transcription/homicide_actual_p23_24.csv  actual direction (Ipsos text p11, scatter p23-24)

The script refuses to write if the two passes disagree on any cell, so a transcription
error cannot reach pairs.csv silently.

Truth columns (rule adopted 2026-11-22):
  t_value_ipsos   the figure exactly as printed in the report ("35%", "0%", "<1%", "No data available")
  t_value         numeric truth used in analysis
  t_flag          as_printed            t_value is the printed number
                  source_unrounded      report printed 0% or <1%; t_value is the unrounded value from
                                        the source Ipsos cites (details in t_unrounded_source / _url)
                  source_unrounded_pending  same case but the unrounded value could not be fetched yet;
                                        t_value is blank (never 0.5); listed in README follow-ups
                  missing               report prints "No data available"
  The unrounded values live in data/transcription/t_unrounded_sources.csv.
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
        t_source="World Inequality Database", definition_match="approximate",
        definition_note="question says households; WID top-1% wealth share is adult-based (equal-split)"),
    "immigrant_share": dict(
        wording="What percentage of your country's population do you think immigrants (i.e., people born in another country) represent?",
        t_source="UN International Migrant Stock", definition_match="yes",
        definition_note="foreign-born in both question and source"),
    "muslim_share": dict(
        wording="In your country, out of 100 people, how many do you think are Muslim?",
        t_source="Pew Research", definition_match="yes",
        definition_note="share of population Muslim in both question and source"),
}

# Country metadata from the methodology page (p38). n is "approximately" as Ipsos states it.
# representative: Ipsos's own statement; 'not_stated' where p38 names the country in neither list.
COUNTRIES = {
    # name_ipsos: (iso3, n_approx, age_range, representative)
    "Argentina": ("ARG", 500, "16-74", "yes"), "Australia": ("AUS", 1000, "16-74", "yes"),
    "Belgium": ("BEL", 500, "16-74", "yes"), "Brazil": ("BRA", 1000, "16-74", "no_urban_educated_affluent"),
    "Canada": ("CAN", 1000, "18-74", "yes"), "Chile": ("CHL", 500, "16-74", "no_urban_educated_affluent"),
    "Colombia": ("COL", 500, "16-74", "no_urban_educated_affluent"), "France": ("FRA", 1000, "16-74", "yes"),
    "Germany": ("DEU", 1000, "16-74", "yes"), "Great Britain": ("GBR", 1000, "16-74", "yes"),
    "Hungary": ("HUN", 500, "16-74", "yes"), "India": ("IND", 2000, "18+", "no_urban_subset"),
    "Indonesia": ("IDN", 500, "21-74", "no_urban_educated_affluent"), "Ireland": ("IRL", 500, "16-74", "not_stated"),
    "Italy": ("ITA", 1000, "16-74", "yes"), "Japan": ("JPN", 1000, "16-74", "yes"),
    "Malaysia": ("MYS", 500, "18-74", "no_urban_educated_affluent"), "Mexico": ("MEX", 500, "16-74", "no_urban_educated_affluent"),
    "Netherlands": ("NLD", 500, "16-74", "yes"), "New Zealand": ("NZL", 1000, "16-74", "not_stated"),
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


def truth(item, country, raw, unrounded):
    """Return a dict of the truth columns for one pair (see module docstring)."""
    raw = raw.strip()
    base = {"t_value_ipsos": printed(raw), "t_unrounded_source": "", "t_unrounded_url": "", "t_unrounded_year": ""}
    if raw.lower() in ("no data available", "n/a", ""):
        return {**base, "t_value": "", "t_flag": "missing"}
    if raw == "<1" or float(raw) == 0:
        u = unrounded.get((item, country))
        if u is None:
            sys.exit(f"no entry in t_unrounded_sources.csv for {item} / {country}")
        pending = u["status"] != "ok" or u["t_value"] == ""
        return {**base, "t_value": "" if pending else float(u["t_value"]),
                "t_flag": "source_unrounded_pending" if pending else "source_unrounded",
                "t_unrounded_source": u["t_unrounded_source"], "t_unrounded_url": u["t_unrounded_url"],
                "t_unrounded_year": u["source_year"]}
    return {**base, "t_value": float(raw), "t_flag": "as_printed"}


def main():
    p1 = {(r["item_id"], r["country"]): r for r in read("pass1.csv")}
    p2 = {(r["item_id"], r["country"]): r for r in read("pass2.csv")}
    if set(p1) != set(p2):
        sys.exit(f"pass key mismatch: {set(p1) ^ set(p2)}")
    bad = [(k, p1[k]["h_mean"], p1[k]["t_raw"], p2[k]["h_mean"], p2[k]["t_raw"])
           for k in p1 if (p1[k]["h_mean"], p1[k]["t_raw"]) != (p2[k]["h_mean"], p2[k]["t_raw"])]
    if bad:
        sys.exit(f"transcription passes disagree, fix before building: {bad}")
    if set(c for _, c in p1) != set(COUNTRIES):
        sys.exit(f"country set mismatch: {set(c for _, c in p1) ^ set(COUNTRIES)}")

    unrounded = {(r["item_id"], r["country"]): r for r in read("t_unrounded_sources.csv")}
    rows = []
    for (item, country), r in sorted(p1.items()):
        iso3, n, age, rep = COUNTRIES[country]
        meta = ITEMS[item]
        t = truth(item, country, r["t_raw"], unrounded)
        rows.append({
            "wave": WAVE, "source_id": SOURCE_ID,
            "country_name_ipsos": country, "country_iso3": iso3, "item_id": item,
            "h_mean": float(r["h_mean"]), "h_stat": "mean (Ipsos 'Average % mentioned')",
            "t_value_ipsos": t["t_value_ipsos"], "t_value": t["t_value"], "t_flag": t["t_flag"],
            "t_unrounded_source": t["t_unrounded_source"], "t_unrounded_url": t["t_unrounded_url"],
            "t_unrounded_year": t["t_unrounded_year"],
            "t_source": meta["t_source"], "t_reference_year": "",
            "definition_match": meta["definition_match"], "definition_note": meta["definition_note"],
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
