"""Build data/pairs.csv and data/pairs_categorical.csv from the hand transcriptions of two Ipsos
Perils of Perception reports.

Wave ipsos_2024 (data/raw/ipsos-perils-of-perception-2024.pdf), inputs hand-transcribed with page numbers:
  data/transcription/ipsos_2024_estimates.csv    average guess and printed actual, p13 / p16 / p20
  data/transcription/homicide_p22.csv            public answer distribution, p22
  data/transcription/homicide_actual_p23_24.csv  actual direction (Ipsos text p11, scatter p23-24)
  Checked on 2026-11-22 by an independent second reading of p14, p17 and p20; all 90 cells agreed,
  and the second reading was deleted afterwards (data/README.md).

Wave ipsos_2020 (data/raw/ipsos-perils-of-perception-2020-causes-of-death.pdf), transcribed 2026-11-22:
  data/transcription/ipsos_2020_estimates.csv    "Avg. guess" and "Actual" per country for the six
                                                 causes whose per-country page is internally consistent
                                                 (cancer p13, cardiovascular p14, neurological p15, HIV/STIs
                                                 p16, interpersonal violence p18, suicide p23)
  data/transcription/ipsos_2020_defective_pages.csv  p19, p21 and p25 as printed, not used (README)
  Pass 1 read the PDF text layer by word coordinates, pass 2 re-read the page images; all 190 cells agreed.

Truth columns (rule adopted 2026-11-22):
  t_value_ipsos   the figure exactly as printed in the report ("35%", "0%", "<1%", "No data available"; the
                  2020 deck prints one-decimal numbers without a percent sign, e.g. "31.5", "0.0")
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
                  who_ghe2023_y2019     ipsos_2020 items, the 31 countries WHO covers (decision 2026-11-22):
                                        t_value is the WHO Global Health Estimates 2023 release share of all
                                        deaths by cause for 2019 (closest pre-COVID year to the fieldwork),
                                        read from data/validation/truth_crosscheck_2020.csv (WHO_DEFN gives
                                        the cause codes); the printed GBD 2017 figure stays in t_value_ipsos
                  ipsos_printed_gbd2017 superseded by who_ghe2023_y2019 (no longer produced): t_value was the "Actual" Ipsos
                                        printed, which its technical note (p53) attributes to the IHME Global
                                        Burden of Disease Study 2017. The planned Our World in Data pull of the
                                        current GBD vintage failed (OWID returns HTTP 403: IHME data is not
                                        redistributable through its API or CSV downloads), so the printed
                                        figure is the fallback; see README follow-ups
                  ipsos_printed_healthyhk
                                        ipsos_2020, Hong Kong only: the technical note says Hong Kong's
                                        "actual" comes from healthyhk.gov.hk, not GBD
                  ..._swap_corrected    ipsos_2020 cardiovascular, Saudi Arabia and Germany: the printed actuals
                                        of these two adjacent rows are swapped relative to Ipsos's own printed
                                        difference column (and to Destatis for Germany); t_value is the other
                                        row's printed figure, t_value_ipsos stays as printed (SWAPPED_2020)
                  national_vr_2017      now Hong Kong only (the other five moved to who_ghe2023_y2019); was: ipsos_2020 HIV/STI rows printed as "0.0" (Hong Kong, Hungary, Japan,
                                        Netherlands, Poland, Sweden): t_value is the 2017 national vital-
                                        registration share read from data/validation/truth_crosscheck_2020.csv
                                        (Eurostat hlth_cd_aro, Japan MHLW, Hong Kong Department of Health);
                                        HIV deaths only, STI deaths not separately reported (decision 2026-11-22)
                  source_unrounded_pending
                                        no longer produced: a rounded-zero row without a national override
                                        would stop the build
                  as_printed / missing  no longer produced by any item; kept as the fallback for items
                                        without a primary-source rule
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

# ---------------------------------------------------------------------------------------------------
# Wave ipsos_2020: Perils of Perception 2020, causes of death (fieldwork 22 Nov - 6 Dec 2019, published Feb 2020).
WAVE_2020 = "ipsos_2020"
SOURCE_ID_2020 = "ipsos_perils_2020_causes_of_death_deck"
FIELDWORK_2020 = ("2019-11-22", "2019-12-06")
H_STAT_2020 = "mean (Ipsos 'Avg. guess')"
T_SOURCE_2020 = "IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk)"

# Wordings are verbatim from the cause pages: the deck prints "about many" (without "how") on every page and
# keeps Ipsos's "[COUNTRY]" placeholder; both are retained here and noted in items.yaml.
STEM_2020 = "Out of every 100 deaths in [COUNTRY] – about many are a result of "
ITEMS_2020 = {
    "deaths_cancer": dict(wording=STEM_2020 + "cancer?", gbd_cause="Neoplasms", definition_match="yes",
        definition_note="question says cancer; Ipsos's actual is the GBD 2017 'Neoplasms' share of all deaths (includes a small number of deaths from non-malignant neoplasms); printed figure used as T (decision 2026-11-22)"),
    "deaths_cardiovascular": dict(wording=STEM_2020 + "cardiovascular diseases such as heart disease, strokes or heart failure?", gbd_cause="Cardiovascular diseases", definition_match="yes",
        definition_note="question and GBD 2017 'Cardiovascular diseases' cause group match; printed figure used as T (decision 2026-11-22)"),
    "deaths_neurological": dict(wording=STEM_2020 + "neurological disorders such as dementia or Parkinson’s disease?", gbd_cause="Neurological disorders", definition_match="yes",
        definition_note="question gives dementia and Parkinson's as examples; GBD 2017 'Neurological disorders' cause group also includes epilepsy, multiple sclerosis, motor neuron disease and others; printed figure used as T (decision 2026-11-22)"),
    "deaths_hiv_sti": dict(wording=STEM_2020 + "HIV/AIDS or sexually transmitted infections (STIs)?", gbd_cause="HIV/AIDS and sexually transmitted infections", definition_match="yes",
        definition_note="question and GBD 2017 'HIV/AIDS and sexually transmitted infections' cause group match; printed figure used as T (decision 2026-11-22)"),
    "deaths_violence": dict(wording=STEM_2020 + "interpersonal violence such as homicide/murder?", gbd_cause="Interpersonal violence", definition_match="yes",
        definition_note="question and GBD 2017 'Interpersonal violence' (assault) cause match; printed figure used as T (decision 2026-11-22)"),
    "deaths_suicide": dict(wording=STEM_2020 + "suicide?", gbd_cause="Self-harm", definition_match="yes",
        definition_note="question says suicide; GBD 2017 'Self-harm' is deaths from intentional self-harm; printed figure used as T (decision 2026-11-22)"),
}

# Printed actuals that are demonstrably mis-attributed: on p14 the "Actual" column prints 37.6 for Saudi Arabia and
# 33.4 for Germany, but Ipsos's own printed differences (-23 and -24) and bars require 33.4 for Saudi Arabia
# (10.1 - 33.4 = -23.3) and 37.6 for Germany (14.1 - 37.6 = -23.5), and Destatis gives 37.0% for Germany in 2017.
# t_value takes the other row's printed figure; t_value_ipsos stays as printed. Decision 2026-11-22.
SWAPPED_2020 = {("deaths_cardiovascular", "Saudi Arabia"): "33.4", ("deaths_cardiovascular", "Germany"): "37.6"}
SWAP_NOTE = "printed actual (t_value_ipsos) is swapped with the adjacent row on p14 according to Ipsos's own printed difference column; t_value is the figure the difference implies (decision 2026-11-22)"
HIV_NOTE = "HIV deaths only; STI deaths not separately reported in the national tables (Hong Kong includes STI)"
HK_NOTE = "Ipsos's technical note (p53) sources Hong Kong's actual from healthyhk.gov.hk rather than GBD 2017, so the cause definition is the Hong Kong government's, not GBD's"

# Country metadata from the technical note (p53), names as printed in the 2020 tables. Lists quoted in data/README.md.
# n: "approximately 1000 ... 16-74" (13 countries) / "approximately 1000 ... 18-74" (USA, Canada) / "approximately
# 500 ... 16-74" (18 countries). Argentina and Belgium appear in both the 1000 and the 500 list and the Philippines
# in neither, so their n is not_stated (decision 2026-11-22); the Philippines' age range is also not stated.
# representative: the note names 18 nationally representative samples and 14 "more urban & educated, and with
# higher incomes" samples, which together cover all 32 countries (no Ireland/New Zealand-style gap).
COUNTRIES_2020 = {
    "Argentina": ("ARG", "not_stated", "16-74", "yes"), "Australia": ("AUS", 1000, "16-74", "yes"),
    "Belgium": ("BEL", "not_stated", "16-74", "yes"), "Brazil": ("BRA", 1000, "16-74", "no_urban_educated_affluent"),
    "Canada": ("CAN", 1000, "18-74", "yes"), "Chile": ("CHL", 1000, "16-74", "no_urban_educated_affluent"),
    "China": ("CHN", 1000, "16-74", "no_urban_educated_affluent"), "Colombia": ("COL", 500, "16-74", "no_urban_educated_affluent"),
    "France": ("FRA", 1000, "16-74", "yes"), "Germany": ("DEU", 1000, "16-74", "yes"),
    "Hong Kong SAR China": ("HKG", 500, "16-74", "yes"), "Hungary": ("HUN", 500, "16-74", "yes"),
    "India": ("IND", 500, "16-74", "no_urban_educated_affluent"), "Italy": ("ITA", 1000, "16-74", "yes"),
    "Japan": ("JPN", 1000, "16-74", "yes"), "Malaysia": ("MYS", 500, "16-74", "no_urban_educated_affluent"),
    "Mexico": ("MEX", 1000, "16-74", "no_urban_educated_affluent"), "Netherlands": ("NLD", 500, "16-74", "yes"),
    "Peru": ("PER", 500, "16-74", "no_urban_educated_affluent"), "Philippines": ("PHL", "not_stated", "not_stated", "no_urban_educated_affluent"),
    "Poland": ("POL", 500, "16-74", "yes"), "Romania": ("ROU", 500, "16-74", "no_urban_educated_affluent"),
    "Russia": ("RUS", 500, "16-74", "no_urban_educated_affluent"), "Saudi Arabia": ("SAU", 500, "16-74", "no_urban_educated_affluent"),
    "Singapore": ("SGP", 500, "16-74", "yes"), "South Africa": ("ZAF", 500, "16-74", "no_urban_educated_affluent"),
    "South Korea": ("KOR", 500, "16-74", "yes"), "Spain": ("ESP", 1000, "16-74", "yes"),
    "Sweden": ("SWE", 500, "16-74", "yes"), "Turkey": ("TUR", 500, "16-74", "no_urban_educated_affluent"),
    "United Kingdom": ("GBR", 1000, "16-74", "yes"), "United States": ("USA", 1000, "18-74", "yes"),
}
# Countries absent from a 2020 page (Saudi Arabia was not shown for HIV/STIs and interpersonal violence).
EXPECTED_2020 = {"deaths_cancer": 32, "deaths_cardiovascular": 32, "deaths_neurological": 32,
                 "deaths_hiv_sti": 31, "deaths_violence": 31, "deaths_suicide": 32}

FIELDS = ["wave", "source_id", "country_name_ipsos", "country_iso3", "item_id", "h_mean", "h_stat", "t_value_ipsos",
          "t_value", "t_flag", "t_unrounded_source", "t_unrounded_url", "t_unrounded_year", "t_source",
          "t_reference_year", "definition_match", "definition_note", "question_wording", "source_page",
          "fieldwork_start", "fieldwork_end", "n_country_approx", "age_range", "representative_sample"]


def read(name):
    with open(os.path.join(D, "transcription", name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def printed(raw):
    """Reconstruct the cell exactly as printed: '35' -> '35%', '<1' -> '<1%', text unchanged."""
    raw = raw.strip()
    return raw if raw.lower() in ("no data available", "n/a") or raw.endswith("%") else raw + "%"


def truth(item, country, raw, pew, wdi, wid):
    """Return a dict of the truth columns for one 2024 pair (see module docstring)."""
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


WHO_T_SOURCE = "WHO Global Health Estimates 2023 release, deaths by cause, 2019, share of all deaths"
WHO_FLAG = "who_ghe2023_y2019"
# definition_match and definition_note per item for the WHO truth (decision 2026-11-22)
WHO_DEFN = {'deaths_cancer': ('approximate', "question says cancer; T is WHO 'Malignant neoplasms' (GHE code 610) over all causes, while the GBD 'Neoplasms' group behind Ipsos's printed figure also counts non-malignant neoplasms, so WHO is slightly lower"), 'deaths_cardiovascular': ('yes', "WHO 'Cardiovascular diseases' (GHE code 1100) over all causes; same scope as the question and the GBD group Ipsos printed"), 'deaths_neurological': ('approximate', "WHO 'Neurological conditions' (GHE code 940) over all causes; WHO and GBD assign dementia deaths differently, so the WHO share is much lower than the printed GBD 2017 figure in ageing countries (Japan 6.3 vs 16.0)"), 'deaths_hiv_sti': ('yes', "WHO 'HIV/AIDS' (GHE code 100) plus 'STDs excluding HIV' (code 40) over all causes; same scope as the question; for Hungary, Japan, Netherlands, Poland and Sweden this supersedes the 2017 national HIV-only figure, retained in validation/truth_crosscheck_2020.csv"), 'deaths_violence': ('yes', "WHO 'Interpersonal violence' (GHE code 1620) over all causes; same scope as the question and GBD"), 'deaths_suicide': ('yes', "WHO 'Self-harm' (GHE code 1610) over all causes; same scope as the question and GBD")}
WHO_GHE_2019 = None


def who_ghe_2019():
    """WHO Global Health Estimates 2023 release, year 2019, share of all deaths by cause, for the 31 ipsos_2020 countries
    WHO covers (Hong Kong SAR China is not a WHO reporting entity), read from data/validation/truth_crosscheck_2020.csv:
    rows whose source_name starts with 'WHO Global Health Estimates' and source_year is 2019. For deaths_cancer the
    file holds two candidates (code 610 alone, and 610 + 790 'Other neoplasms'); the one used is malignant neoplasms
    alone, identified by the prefix of its definition_note.
    Decision 2026-11-22."""
    global WHO_GHE_2019
    if WHO_GHE_2019 is None:
        path = os.path.join(D, "validation", "truth_crosscheck_2020.csv")
        table = {}
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r["source_name"].startswith("WHO Global Health Estimates") or r["source_year"] != "2019":
                    continue
                if r["item_id"] == "deaths_cancer" and r["definition_note"].startswith("WHO GHE 'Malignant neoplasms' (code 610) + 'Other neoplasms'"):
                    continue
                key = (r["item_id"], r["country_iso3"])
                if key in table:
                    sys.exit(f"truth_crosscheck_2020.csv: duplicate WHO 2019 candidate for {key}")
                table[key] = r
        n_items = {i for i, _ in table}; n_c = {c for _, c in table}
        if n_items != set(WHO_DEFN) or len(n_c) != 31 or "HKG" in n_c or len(table) != 186:
            sys.exit(f"truth_crosscheck_2020.csv: WHO 2019 candidates: {len(table)} cells, {len(n_c)} countries, items {sorted(n_items)}")
        WHO_GHE_2019 = table
    return WHO_GHE_2019


HOMICIDE_TRUTH = None


def homicide_truth():
    """homicide_trend truth per country from data/validation/truth_crosscheck_homicide.csv: UNODC intentional-homicide
    victims per 100,000, 2000 baseline from the World Bank WDI copy (VC.IHR.PSRC.P5; nearest later year where 2000 is
    missing) and the latest year from the UNODC 2026 release. Direction with a 10 percent tolerance: lower if the latest
    rate is at least 10 percent below the baseline, higher if at least 10 percent above, else same. Decision 2026-11-22."""
    global HOMICIDE_TRUTH
    if HOMICIDE_TRUTH is None:
        path = os.path.join(D, "validation", "truth_crosscheck_homicide.csv")
        table = {}
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["item_id"] != "homicide_trend":
                    continue
                change = float(r["change_pct"])
                rule = "lower" if change <= -10 else ("higher" if change >= 10 else "same")
                if rule != r["direction_10pct"]:
                    sys.exit(f"homicide {r['country_iso3']}: 10% rule gives {rule}, file says {r['direction_10pct']}")
                caveats = [p.strip() for p in r["note"].split(";")
                           if p.strip() and not p.strip().startswith(("thresholds:", "agrees_with_ipsos", "UNODC xlsx sha256"))]
                table[r["country_iso3"]] = {**r, "direction": rule, "caveats": "; ".join(caveats)}
        if len(table) != 30:
            sys.exit(f"truth_crosscheck_homicide.csv: {len(table)} countries, expected 30")
        HOMICIDE_TRUTH = table
    return HOMICIDE_TRUTH


NATIONAL_VR_2017 = None


def national_vr_2017():
    """2017 national vital-registration HIV death shares for the six ipsos_2020 HIV/STI rows printed as 0.0, read from
    data/validation/truth_crosscheck_2020.csv: the deaths_hiv_sti candidates with source_year 2017 that are not WHO
    Global Health Estimates (Eurostat hlth_cd_aro for Hungary, Netherlands, Poland and Sweden; Japan MHLW vital
    statistics; Hong Kong Department of Health registered deaths). Decision 2026-11-22."""
    global NATIONAL_VR_2017
    if NATIONAL_VR_2017 is None:
        path = os.path.join(D, "validation", "truth_crosscheck_2020.csv")
        with open(path, encoding="utf-8") as f:
            cands = [r for r in csv.DictReader(f)
                     if r["item_id"] == "deaths_hiv_sti" and r["source_year"] == "2017"
                     and not r["source_name"].startswith("WHO Global Health Estimates")]
        table = {}
        for r in cands:
            if r["country_iso3"] in table:
                sys.exit(f"truth_crosscheck_2020.csv: more than one 2017 national candidate for {r['country_iso3']}")
            table[r["country_iso3"]] = r
        expected = {"HKG", "HUN", "JPN", "NLD", "POL", "SWE"}
        if set(table) != expected:
            sys.exit(f"truth_crosscheck_2020.csv: national 2017 candidates found for {sorted(table)}, expected {sorted(expected)}")
        NATIONAL_VR_2017 = table
    return NATIONAL_VR_2017


def truth_2020(item, country, iso3, raw):
    """Truth columns for one 2020 pair: the printed GBD 2017 figure, blank where it is a rounded zero."""
    raw = raw.strip()
    base = {"t_value_ipsos": raw, "t_unrounded_source": "", "t_unrounded_url": "", "t_unrounded_year": "",
            "t_reference_year": "" if country == "Hong Kong SAR China" else "2017"}
    flag = "ipsos_printed_healthyhk" if country == "Hong Kong SAR China" else "ipsos_printed_gbd2017"
    if (item, iso3) in who_ghe_2019():  # every country WHO covers; Hong Kong falls through to the printed figure
        c = who_ghe_2019()[(item, iso3)]
        return {**base, "t_value": float(c["candidate_value"]), "t_flag": WHO_FLAG,
                "t_unrounded_source": c["source_name"], "t_unrounded_url": c["source_url"],
                "t_unrounded_year": c["source_year"], "t_reference_year": "2019"}
    if (item, country) in SWAPPED_2020:  # unreachable for Saudi Arabia and Germany now (WHO); kept to document the deck error
        return {**base, "t_value": float(SWAPPED_2020[(item, country)]), "t_flag": flag + "_swap_corrected"}
    if raw.endswith("*") or float(raw) == 0:  # "0.0" or "0.0*" (= more than 0 but less than 0.05): no placeholder
        if item == "deaths_hiv_sti" and iso3 in national_vr_2017():
            c = national_vr_2017()[iso3]
            return {**base, "t_value": float(c["candidate_value"]), "t_flag": "national_vr_2017",
                    "t_unrounded_source": c["source_name"], "t_unrounded_url": c["source_url"],
                    "t_unrounded_year": c["source_year"], "t_reference_year": "2017"}
        sys.exit(f"{item} / {country}: printed rounded zero and no national override (rule: no row without a truth value)")
    return {**base, "t_value": float(raw), "t_flag": flag}


def rows_2024(wdi):
    p1 = {(r["item_id"], r["country"]): r for r in read("ipsos_2024_estimates.csv")}
    if set(c for _, c in p1) != set(COUNTRIES):
        sys.exit(f"country set mismatch: {set(c for _, c in p1) ^ set(COUNTRIES)}")
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
    return rows


def rows_2020(wdi):
    p1 = {(r["item_id"], r["country"]): r for r in read("ipsos_2020_estimates.csv")}
    if set(c for _, c in p1) != set(COUNTRIES_2020):
        sys.exit(f"2020 country set mismatch: {set(c for _, c in p1) ^ set(COUNTRIES_2020)}")
    if set(i for i, _ in p1) != set(ITEMS_2020):
        sys.exit(f"2020 item set mismatch: {set(i for i, _ in p1) ^ set(ITEMS_2020)}")
    for item, n in EXPECTED_2020.items():
        got = sum(1 for i, _ in p1 if i == item)
        if got != n:
            sys.exit(f"2020 {item}: expected {n} countries, found {got}")
    rows = []
    for (item, country), r in sorted(p1.items()):
        iso3, n, age, rep = COUNTRIES_2020[country]
        if wdi[iso3]["country_name_ipsos"] not in (country, {"United Kingdom": "Great Britain", "Turkey": "Türkiye"}.get(country)):
            sys.exit(f"2020 {country}: countries.csv row for {iso3} is named {wdi[iso3]['country_name_ipsos']}")
        meta = ITEMS_2020[item]
        t = truth_2020(item, country, iso3, r["t_raw"])
        defn_match, defn_note = meta["definition_match"], meta["definition_note"]
        if (item, country) in SWAPPED_2020:
            defn_note = defn_note + "; " + SWAP_NOTE
        if country == "Hong Kong SAR China":
            defn_match, defn_note = "approximate", HK_NOTE
        t_source = T_SOURCE_2020
        if t["t_flag"] == WHO_FLAG:
            t_source = WHO_T_SOURCE
            defn_match, defn_note = WHO_DEFN[item]
        if t["t_flag"] == "national_vr_2017":
            t_source = t["t_unrounded_source"]
            defn_match, defn_note = "approximate", HIV_NOTE
        rows.append({
            "wave": WAVE_2020, "source_id": SOURCE_ID_2020,
            "country_name_ipsos": country, "country_iso3": iso3, "item_id": item,
            "h_mean": float(r["h_mean"]), "h_stat": H_STAT_2020,
            "t_value_ipsos": t["t_value_ipsos"], "t_value": t["t_value"], "t_flag": t["t_flag"],
            "t_unrounded_source": t["t_unrounded_source"], "t_unrounded_url": t["t_unrounded_url"],
            "t_unrounded_year": t["t_unrounded_year"],
            "t_source": t_source, "t_reference_year": t["t_reference_year"],
            "definition_match": defn_match, "definition_note": defn_note,
            "question_wording": meta["wording"],
            "source_page": r["page"],
            "fieldwork_start": FIELDWORK_2020[0], "fieldwork_end": FIELDWORK_2020[1],
            "n_country_approx": n, "age_range": age, "representative_sample": rep,
        })
    return rows


def main():
    with open(os.path.join(D, "countries.csv"), encoding="utf-8") as f:
        wdi = {r["country_iso3"]: r for r in csv.DictReader(f)}
    r24 = rows_2024(wdi)
    rows = r24 + rows_2020(wdi)
    out = os.path.join(D, "pairs.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print("wrote", out, len(rows), "rows", {wv: sum(1 for r in rows if r["wave"] == wv) for wv in (WAVE, WAVE_2020)})

    # Categorical side table: homicide trend (2024 wave). actual_direction comes from the UNODC series with a 10%
    # tolerance (homicide_truth); Ipsos's coarse direction from p11 is kept as ipsos_actual_direction.
    actual = {r["country"]: r for r in read("homicide_actual_p23_24.csv")}
    crow = []
    for r in read("homicide_p22.csv"):
        c = r["country"]; iso3, n, age, rep = COUNTRIES[c]
        hi, sa, lo = int(r["pct_higher"]), int(r["pct_same"]), int(r["pct_lower"])
        majority = "higher" if hi > 50 else ("lower" if lo > 50 else ("same" if sa > 50 else "no_majority"))
        plural = max((hi, "higher"), (sa, "same"), (lo, "lower"))[1]
        a = actual[c]; h = homicide_truth()[iso3]
        crow.append({
            "wave": WAVE, "source_id": SOURCE_ID, "country_name_ipsos": c, "country_iso3": iso3,
            "item_id": "homicide_trend",
            "question_wording": "Do you think the homicide rate in your country is higher, lower, or about the same as in 2000?",
            "pct_higher": hi, "pct_same": sa, "pct_lower": lo,
            "public_majority": majority, "public_plurality": plural,
            "actual_direction": h["direction"],
            "rate_2000": h["rate_2000"], "year_2000_used": h["year_2000_used"],
            "rate_latest": h["rate_latest"], "year_latest": h["year_latest"], "change_pct": h["change_pct"],
            "truth_rule": "lower if latest rate <= 0.9 x baseline, higher if >= 1.1 x baseline, else same",
            "truth_source": h["source_name"] + " | " + h["source_url"], "truth_note": h["caveats"],
            "ipsos_actual_direction": a["actual_direction"],
            "ipsos_actual_direction_source": "Ipsos text p11 ('about the same or lower in all countries except Mexico'); scatter p23-24; underlying source UN Office on Drugs and Crime",
            "approx_change_per_100k_from_chart": a["approx_change_per_100k_from_chart"],
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
