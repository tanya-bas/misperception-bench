"""Fetch the web-presence covariate for each Ipsos country (2024 wave plus the six added by the 2020 wave; network step; resumable).

Two measures, both written to data/raw/web_presence.json with the fetch date:
  1. wikidata_p17_count : number of Wikidata items whose 'country' (P17) is this country.
     COUNT queries scan every item and time out (60 s server limit) for large countries,
     so this column may be missing for some; it is recorded when it succeeds.
  2. enwiki_mentions    : total hits for an exact-phrase search of the country name in
     English Wikipedia (MediaWiki search API, srinfo=totalhits). Cheap, complete for all
     countries, and closest in spirit to "documents mentioning the entity" (Kandpal et al.
     2023). This is the column build_countries.py uses as the primary web-presence covariate.
Run: python3 -I scripts/fetch_web_presence.py
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "web_presence.json")
UA = "misperception-bench/0.1 (research dataset build; contact: repo owner)"

# Ipsos country -> (ISO3, Wikidata QID, English search phrase)
COUNTRIES = {
    "Argentina": ("ARG", "Q414", "Argentina"), "Australia": ("AUS", "Q408", "Australia"),
    "Belgium": ("BEL", "Q31", "Belgium"), "Brazil": ("BRA", "Q155", "Brazil"),
    "Canada": ("CAN", "Q16", "Canada"), "Chile": ("CHL", "Q298", "Chile"),
    "Colombia": ("COL", "Q739", "Colombia"), "France": ("FRA", "Q142", "France"),
    "Germany": ("DEU", "Q183", "Germany"), "Great Britain": ("GBR", "Q145", "United Kingdom"),
    "Hungary": ("HUN", "Q28", "Hungary"), "India": ("IND", "Q668", "India"),
    "Indonesia": ("IDN", "Q252", "Indonesia"), "Ireland": ("IRL", "Q27", "Ireland"),
    "Italy": ("ITA", "Q38", "Italy"), "Japan": ("JPN", "Q17", "Japan"),
    "Malaysia": ("MYS", "Q833", "Malaysia"), "Mexico": ("MEX", "Q96", "Mexico"),
    "Netherlands": ("NLD", "Q55", "Netherlands"), "New Zealand": ("NZL", "Q664", "New Zealand"),
    "Peru": ("PER", "Q419", "Peru"), "Poland": ("POL", "Q36", "Poland"),
    "Singapore": ("SGP", "Q334", "Singapore"), "South Africa": ("ZAF", "Q258", "South Africa"),
    "South Korea": ("KOR", "Q884", "South Korea"), "Spain": ("ESP", "Q29", "Spain"),
    "Sweden": ("SWE", "Q34", "Sweden"), "Thailand": ("THA", "Q869", "Thailand"),
    "Türkiye": ("TUR", "Q43", "Turkey"), "United States": ("USA", "Q30", "United States"),
    # added for the Ipsos Perils of Perception 2020 (causes of death) wave, 2026-11-22
    "China": ("CHN", "Q148", "China"), "Hong Kong": ("HKG", "Q8646", "Hong Kong"),
    "Philippines": ("PHL", "Q928", "Philippines"), "Romania": ("ROU", "Q218", "Romania"),
    "Russia": ("RUS", "Q159", "Russia"), "Saudi Arabia": ("SAU", "Q851", "Saudi Arabia"),
}


def get(url, timeout, retries=4):
    """GET JSON; on HTTP 429 wait and retry (Wikimedia rate limits unauthenticated clients)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(30 * (attempt + 1))
                continue
            raise


def enwiki_hits(phrase):
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": f'"{phrase}"',
                                "srinfo": "totalhits", "srlimit": 1, "format": "json"})
    return get("https://en.wikipedia.org/w/api.php?" + q, 30)["query"]["searchinfo"]["totalhits"]


def wikidata_count(qid):
    sparql = f"SELECT (COUNT(?item) AS ?c) WHERE {{ ?item wdt:P17 wd:{qid} . }}"
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": sparql, "format": "json"})
    try:
        d = get(url, 35, retries=1)
        return int(d["results"]["bindings"][0]["c"]["value"])
    except Exception:  # timeouts (HTTP 500/504) are expected for big countries
        return None


def main():
    out = {"fetched_on": date.today().isoformat(),
           "enwiki_query": 'en.wikipedia.org/w/api.php?action=query&list=search&srsearch="<name>"&srinfo=totalhits',
           "wikidata_query": "SELECT (COUNT(?item) AS ?c) WHERE { ?item wdt:P17 wd:<QID> . }",
           "countries": {}}
    if os.path.exists(OUT):  # resume: keep countries already fetched
        out["countries"] = json.load(open(OUT)).get("countries", {})
    for name, (iso3, qid, phrase) in COUNTRIES.items():
        done = out["countries"].get(iso3)
        if done and done.get("enwiki_mentions") is not None:
            print(f"{iso3} already fetched, skipping", flush=True)
            continue
        hits = enwiki_hits(phrase)
        wd = wikidata_count(qid)
        out["countries"][iso3] = {"name": name, "qid": qid, "search_phrase": phrase,
                                  "enwiki_mentions": hits, "wikidata_p17_count": wd}
        print(f"{iso3} {name:15s} enwiki={hits:>9} wikidata={wd}", flush=True)
        with open(OUT, "w") as f:
            json.dump(out, f, indent=1)
        time.sleep(5)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
