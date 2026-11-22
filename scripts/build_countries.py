"""Build data/countries.csv: one row per Ipsos 2024 country with the covariates used as
moderators in H1a and as an independent check on Ipsos's immigrant-share truth value.

Inputs (cached API dumps in data/raw/, re-fetchable with the curl lines in data/README.md):
  data/raw/worldbank/countries.json          World Bank country metadata (incomeLevel = current classification)
  data/raw/worldbank/NY.GDP.PCAP.PP.CD.json  GDP per capita, PPP, current international $ (latest 12 years)
  data/raw/worldbank/SM.POP.TOTL.ZS.json     international migrant stock, % of population (UN DESA via WDI)
  data/raw/web_presence.json                 from scripts/fetch_web_presence.py

Choices (also logged in README):
  * gdp_pcap_ppp uses the latest non-null year <= 2024 per country; the year is recorded.
  * migrant_stock_pct uses the latest available WDI year (2024 where present, else 2020).
  * web_presence = enwiki_mentions (English Wikipedia exact-phrase search total hits) because the
    Wikidata P17 count query times out for most large countries; the Wikidata count is kept where
    it succeeded. Both fetched on the date in web_presence.json.
Run: python3 -I scripts/build_countries.py
"""
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
WB = os.path.join(D, "raw", "worldbank")

# Ipsos name -> (ISO3, World Bank name variant, main language, Ipsos representative flag from p38;
# Ireland and New Zealand are named on neither p38 list and are treated as representative by author decision 2026-11-22)
COUNTRIES = {
    "Argentina": ("ARG", "Argentina", "Spanish", "yes"), "Australia": ("AUS", "Australia", "English", "yes"),
    "Belgium": ("BEL", "Belgium", "Dutch/French", "yes"), "Brazil": ("BRA", "Brazil", "Portuguese", "no_urban_educated_affluent"),
    "Canada": ("CAN", "Canada", "English/French", "yes"), "Chile": ("CHL", "Chile", "Spanish", "no_urban_educated_affluent"),
    "Colombia": ("COL", "Colombia", "Spanish", "no_urban_educated_affluent"), "France": ("FRA", "France", "French", "yes"),
    "Germany": ("DEU", "Germany", "German", "yes"), "Great Britain": ("GBR", "United Kingdom", "English", "yes"),
    "Hungary": ("HUN", "Hungary", "Hungarian", "yes"), "India": ("IND", "India", "Hindi/English", "no_urban_subset"),
    "Indonesia": ("IDN", "Indonesia", "Indonesian", "no_urban_educated_affluent"), "Ireland": ("IRL", "Ireland", "English", "yes"),
    "Italy": ("ITA", "Italy", "Italian", "yes"), "Japan": ("JPN", "Japan", "Japanese", "yes"),
    "Malaysia": ("MYS", "Malaysia", "Malay", "no_urban_educated_affluent"), "Mexico": ("MEX", "Mexico", "Spanish", "no_urban_educated_affluent"),
    "Netherlands": ("NLD", "Netherlands", "Dutch", "yes"), "New Zealand": ("NZL", "New Zealand", "English", "yes"),
    "Peru": ("PER", "Peru", "Spanish", "no_urban_educated_affluent"), "Poland": ("POL", "Poland", "Polish", "yes"),
    "Singapore": ("SGP", "Singapore", "English/Mandarin/Malay/Tamil", "no_urban_educated_affluent"), "South Africa": ("ZAF", "South Africa", "English (+10 official)", "no_urban_educated_affluent"),
    "South Korea": ("KOR", "Korea, Rep.", "Korean", "yes"), "Spain": ("ESP", "Spain", "Spanish", "yes"),
    "Sweden": ("SWE", "Sweden", "Swedish", "yes"), "Thailand": ("THA", "Thailand", "Thai", "no_urban_educated_affluent"),
    "Türkiye": ("TUR", "Turkiye", "Turkish", "no_urban_educated_affluent"), "United States": ("USA", "United States", "English", "yes"),
}


def latest(indicator_file, iso3, max_year=2024):
    """(value, year) of the latest non-null observation for a country, year <= max_year."""
    d = json.load(open(os.path.join(WB, indicator_file)))
    best = None
    for r in d[1]:
        if r["countryiso3code"] == iso3 and r["value"] is not None and int(r["date"]) <= max_year:
            if best is None or int(r["date"]) > best[1]:
                best = (r["value"], int(r["date"]))
    return best or ("", "")


def main():
    meta = {c["id"]: c for c in json.load(open(os.path.join(WB, "countries.json")))[1]}
    wp_path = os.path.join(D, "raw", "web_presence.json")
    wp = json.load(open(wp_path)) if os.path.exists(wp_path) else {"countries": {}, "fetched_on": ""}

    rows = []
    for name, (iso3, wb_name, lang, rep) in COUNTRIES.items():
        gdp, gdp_year = latest("NY.GDP.PCAP.PP.CD.json", iso3)
        mig, mig_year = latest("SM.POP.TOTL.ZS.json", iso3)
        w = wp["countries"].get(iso3, {})
        rows.append({
            "country_iso3": iso3, "country_name_ipsos": name, "country_name_worldbank": wb_name,
            "main_language": lang,
            "wb_income_group": meta[iso3]["incomeLevel"]["value"],
            "wb_region": meta[iso3]["region"]["value"],
            "gdp_pcap_ppp": round(gdp, 0) if gdp != "" else "", "gdp_pcap_ppp_year": gdp_year,
            "migrant_stock_pct_wdi": round(mig, 2) if mig != "" else "", "migrant_stock_pct_year": mig_year,
            "enwiki_mentions": w.get("enwiki_mentions", ""),
            "wikidata_p17_count": w.get("wikidata_p17_count") if w.get("wikidata_p17_count") is not None else "",
            "web_presence_fetched_on": wp.get("fetched_on", ""),
            "ipsos_representative_sample": rep,
        })
    out = os.path.join(D, "countries.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    print("wrote", out, len(rows), "rows")
    missing = [r["country_iso3"] for r in rows if r["enwiki_mentions"] == ""]
    print("countries without web presence yet:", missing or "none")


if __name__ == "__main__":
    main()
