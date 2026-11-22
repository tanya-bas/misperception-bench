# misperception-bench data, v0

Human estimates (H), truth values (T) and country covariates for the paper
*Lost in Average: How LLMs Erase Differences in What the World Believes*.
Scope of v0: the Ipsos Perils of Perception 2024 wave only (30 countries, fieldwork
20 September to 4 October 2024). Every value carries the document and page it came from.

## Files

| File | One row per | Rows | Built by |
|---|---|---|---|
| `items.yaml` | item | 4 | hand-written |
| `sources.csv` | document, dataset or API dump | 10 | hand-written |
| `pairs.csv` | country x percent item | 90 | `scripts/build_pairs.py` |
| `pairs_categorical.csv` | country x homicide-trend item | 30 | `scripts/build_pairs.py` |
| `countries.csv` | country | 30 | `scripts/build_countries.py` |
| `transcription/pass1.csv`, `pass2.csv` | transcribed cell, two independent readings | 90 each | hand-transcribed |
| `transcription/homicide_p22.csv`, `homicide_actual_p23_24.csv` | country | 30 each | hand-transcribed |
| `transcription/t_unrounded_sources.csv` | pair where the report prints 0% or <1% | 12 | hand-entered from the cited source |
| `validation/ipsos_comparator_immigrant_share_p19.csv` | country, comparator wave | 13 | hand-transcribed; validation only |
| `raw/` | downloads, gitignored | | see Re-fetching below |

## Provenance

**Ipsos Perils of Perception 2024** (`ipsos_perils_2024_report` in `sources.csv`). Public PDF,
sha256 in `sources.csv`. H is Ipsos's "Average % mentioned" (a mean, don't-knows excluded).
T is the "Actual" column Ipsos prints next to it, with the source Ipsos cites:

| item | report page | T source cited by Ipsos | definition match |
|---|---|---|---|
| wealth_top1 | 13 (14 re-read) | World Inequality Database | approximate (households vs adults) |
| immigrant_share | 16 (17 re-read) | UN International Migrant Stock | yes (foreign-born) |
| muslim_share | 20 (re-read) | Pew Research | yes |
| homicide_trend | 22, direction from p11 and p23-24 | UN Office on Drugs and Crime | categorical |

**Two-pass transcription.** Every H and T cell was transcribed twice. Pass 1 read p13, p16
and p20. Pass 2 read p14 and p17, where the report restates average guess and actual for
wealth and immigrants in a different order, and re-read p20 independently for Muslim share
(the only page that prints it). `pairs.csv` carries `source_page` (the pass-1 page);
`build_pairs.py` aborts if the two passes differ on any cell. The outcome of the comparison,
including any disagreement with both readings and the resolved value, is reported in the
Validation results section below rather than per row. Both passes were done by the same
model session on 2026-11-22. A human spot-check is listed under follow-ups.

**Truth columns.** `t_value_ipsos` is the figure exactly as printed. `t_value` is the number
used in analysis, with `t_flag`:

| t_flag | meaning | rows |
|---|---|---|
| as_printed | report prints a normal number; `t_value` equals it | 77 |
| source_unrounded | report prints 0% or <1%; `t_value` is the unrounded value from the source Ipsos cites, recorded in `t_unrounded_source`, `t_unrounded_url`, `t_unrounded_year` | 12 |
| source_unrounded_pending | same case, value not yet fetched; `t_value` blank | 0 |
| missing | report prints "No data available" (Peru, wealth) | 1 |

Unrounded sources used: immigrant share for India and Indonesia from the World Bank migrant
stock over population for 2024 (the UN DESA 2024-revision Excel linked from the UN DESA page
returned 404 on 2026-11-22; WDI carries the same UN DESA series). Muslim share for the ten
"<1%" countries from the country table embedded in Pew's Religious Composition by Country
2010-2020 interactive page, 2020 column, which gives shares to five decimals; Pew's Appendix B
PDF prints the same rows as "<0.1" or "0.9" and was used as a cross-check.

Sample sizes, age ranges and the representative-sample flag are from the methodology page (p38).
Ipsos states that samples in Brazil, Chile, Colombia, Indonesia, Israel, Malaysia, Mexico, Peru,
Singapore, South Africa, Thailand and Türkiye are more urban, educated and affluent than the
general population, and that India's sample is an urban SEC A/B/C subset. Ireland and New
Zealand are named in neither list and are flagged `not_stated`. Israel appears on p38 but in
none of the item tables, so it is not in the dataset.

**World Bank** (`countries.csv`): income group and region from the country endpoint;
GDP per capita PPP (`NY.GDP.PCAP.PP.CD`, latest year <= 2024); international migrant stock
% (`SM.POP.TOTL.ZS`, UN DESA, latest year) as an independent check on the Ipsos immigrant T.

**Web presence** (`countries.csv`): `enwiki_mentions` = English Wikipedia exact-phrase search
total hits for the country name; `wikidata_p17_count` = number of Wikidata items whose country
is this country, where the SPARQL count finished before the 60 s server limit. Query strings and
fetch date are in `raw/web_presence.json` and `scripts/fetch_web_presence.py`.

## Special values

* No `t_value` is 0 or 0.5. The twelve rows the report prints as 0% or "<1%" carry the
  source's unrounded value (`t_flag = source_unrounded`), so the log-odds transform is defined
  for every pair except Peru wealth (`t_flag = missing`).
* `approx_change_per_100k_from_chart` in `pairs_categorical.csv` is read off a scatter plot and
  is approximate; `actual_direction` is the analysable field.

## Licences

Ipsos reports are public; aggregate figures are transcribed for research with citation.
World Bank Open Data is CC BY 4.0. Wikipedia/Wikidata counts are derived counts only.
Nothing in `raw/` is redistributed; see Re-fetching.

## Re-fetching raw inputs

```
curl -L -o data/raw/ipsos-perils-of-perception-2024.pdf \
  https://www.ipsos.com/sites/default/files/ct/publication/documents/2025-01/ipsos-the-perils-of-perception-2024.pdf
mkdir -p data/raw/worldbank
curl -sL "https://api.worldbank.org/v2/country?format=json&per_page=400" -o data/raw/worldbank/countries.json
curl -sL "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.CD?format=json&per_page=20000&mrv=12" -o data/raw/worldbank/NY.GDP.PCAP.PP.CD.json
curl -sL "https://api.worldbank.org/v2/country/all/indicator/SM.POP.TOTL.ZS?format=json&per_page=20000&mrv=12" -o data/raw/worldbank/SM.POP.TOTL.ZS.json
python3 -I scripts/fetch_web_presence.py      # network; resumable
```

Then rebuild: `python3 -I scripts/build_pairs.py && python3 -I scripts/build_countries.py && python3 -I scripts/validate.py`.

## Decisions log

* 2026-11-22: truth rule. Keep the printed figure as text (`t_value_ipsos`) and a numeric `t_value`; where the report prints 0% or "<1%", `t_value` is the unrounded figure from the source Ipsos cites with provenance columns, never 0.5; if a source cannot be fetched the row is `source_unrounded_pending` with a blank `t_value`. Peru wealth stays `missing`.
* 2026-11-22: per-row `entered_by`, `checked_by`, `second_pass_page` and `transcription_flag` columns dropped; the two-pass procedure is described once above, each row keeps `source_page`, and the comparison outcome is in the validation section.

* 2026-11-22: paper restricted to data from 2020 onward; H1b (group-level flattening) removed because no 2020+ group-level human estimates were found. No group-level tables, scripts or party map are included.
* 2026-11-22: v0 uses the Ipsos 2024 wave only. Older waves (2014 to 2018) are not transcribed; the p19 comparator figures are kept only as a validation artifact.
* 2026-11-22: T is the value Ipsos prints with the source it cites (international databases), not national statistics offices. WDI migrant stock is recorded as an independent check, not as T.
* 2026-11-22: web-presence covariate is English Wikipedia mention counts because the Wikidata P17 count times out for most large countries; Wikidata counts are kept where they completed.
* 2026-11-22: GDP per capita PPP uses the latest available year <= 2024 per country; income group is the current World Bank classification at retrieval, not the FY2025 classification by year.
* 2026-11-22: the two transcription passes were both done by the same model session reading different pages; a human spot-check of a sample of rows against the PDF is still recommended before publication.

## Follow-ups

* Human spot-check of a sample of `pairs.csv` rows against the PDF before publication.
* Pew vintage: Ipsos's printed Muslim share for Türkiye (98) matches Pew's 2010 figure (98.6) better than Pew's 2020 figure (97.1), so Ipsos may have used an earlier Pew release for its "Actual" column. The ten unrounded values use Pew 2020. Decide whether to re-source all muslim_share T from one Pew vintage.
* UN DESA 2024 revision: replace the World Bank ratio for India and Indonesia with the UN DESA 2024 Table 3 value once the Excel link on the UN DESA page works again.
* `wikidata_p17_count` completed for 2 of 30 countries before the SPARQL time limit; `enwiki_mentions` is the covariate to use.
* Ireland and New Zealand have `representative_sample = not_stated` because the methodology page names them in neither list.

## Validation results

Generated by `scripts/validate.py`.

<!-- validation:start -->
```
1. Range check: 90 rows, 0 outside [0,100].
   t_flag counts: {('immigrant_share', 'as_printed'): 28, ('immigrant_share', 'source_unrounded'): 2, ('muslim_share', 'source_unrounded'): 10, ('muslim_share', 'as_printed'): 20, ('wealth_top1', 'as_printed'): 29, ('wealth_top1', 'missing'): 1}
   T zero or blank (logit undefined): [('wealth_top1', 'Peru')]; source_unrounded_pending: none
   printed vs unrounded for source_unrounded rows: [('immigrant_share', 'India', '0%', '0.3306'), ('immigrant_share', 'Indonesia', '0%', '0.1572'), ('muslim_share', 'Argentina', '<1%', '0.9292'), ('muslim_share', 'Brazil', '<1%', '0.0177'), ('muslim_share', 'Chile', '<1%', '0.06699'), ('muslim_share', 'Colombia', '<1%', '0.00393'), ('muslim_share', 'Hungary', '<1%', '0.13922'), ('muslim_share', 'Japan', '<1%', '0.16997'), ('muslim_share', 'Mexico', '<1%', '0.00629'), ('muslim_share', 'Peru', '<1%', '0.02159'), ('muslim_share', 'Poland', '<1%', '0.00732'), ('muslim_share', 'South Korea', '<1%', '0.31')]
2. Countries per item: {'immigrant_share': 30, 'muslim_share': 30, 'wealth_top1': 30}. Missing T: [('wealth_top1', 'Peru', 'No data available')]
3. Two-pass transcription: 90 cells in pass 1, 90 in pass 2; rows where both passes agreed on H and T: 90 of 90.
   No disagreements; nothing to resolve. Pass-1 pages: wealth p13, immigrants p16, Muslim p20. Pass-2 pages: p14, p17, p20 re-read.
4. Question wording present verbatim in items.yaml for all items: yes.
5. Ipsos immigrant-share T vs World Bank WDI SM.POP.TOTL.ZS (both UN DESA):
   | country | Ipsos T | WDI % (year) | diff |
   |---|---|---|---|
   | Argentina | 5 | 4.3 (2024) | +0.7 |
   | Australia | 30 | 30.4 (2024) | -0.4 |
   | Belgium | 17 | 20.0 (2024) | -3.0 **>2pp** |
   | Brazil | 1 | 0.7 (2024) | +0.3 |
   | Canada | 21 | 22.2 (2024) | -1.2 |
   | Chile | 9 | 7.8 (2024) | +1.2 |
   | Colombia | 4 | 5.8 (2024) | -1.8 |
   | Germany | 19 | 19.8 (2024) | -0.8 |
   | Spain | 15 | 18.5 (2024) | -3.5 **>2pp** |
   | France | 13 | 13.8 (2024) | -0.8 |
   | Great Britain | 14 | 17.1 (2024) | -3.1 **>2pp** |
   | Hungary | 6 | 7.1 (2024) | -1.1 |
   | Indonesia | 0 | 0.2 (2024) | -0.0 |
   | India | 0 | 0.3 (2024) | +0.0 |
   | Ireland | 18 | 23.1 (2024) | -5.1 **>2pp** |
   | Italy | 11 | 11.0 (2024) | +0.0 |
   | Japan | 2 | 2.8 (2024) | -0.8 |
   | South Korea | 3 | 3.5 (2024) | -0.5 |
   | Mexico | 1 | 1.3 (2024) | -0.3 |
   | Malaysia | 11 | 10.7 (2024) | +0.3 |
   | Netherlands | 14 | 16.2 (2024) | -2.2 **>2pp** |
   | New Zealand | 29 | 28.2 (2024) | +0.8 |
   | Peru | 4 | 5.4 (2024) | -1.4 |
   | Poland | 2 | 4.5 (2024) | -2.5 **>2pp** |
   | Singapore | 43 | 48.7 (2024) | -5.7 **>2pp** |
   | Sweden | 20 | 21.4 (2024) | -1.4 |
   | Thailand | 5 | 4.4 (2024) | +0.6 |
   | Türkiye | 7 | 8.1 (2024) | -1.1 |
   | United States | 15 | 15.2 (2024) | -0.2 |
   | South Africa | 5 | 4.1 (2024) | +0.9 |
   Countries where |Ipsos T - WDI| > 2 points: 7. Differences reflect the WDI vintage vs the UN DESA release Ipsos used; Ipsos rounds to whole percents.
6. definition_match per item: {('immigrant_share', 'yes'): 30, ('muslim_share', 'yes'): 30, ('wealth_top1', 'approximate'): 30}. 'approximate' = wealth_top1 (households in question, adults in WID).
7. 2024 vs comparator wave (report p19) immigrant-share average guess, 13 countries: [('Canada', 4), ('Australia', 3), ('United States', -2), ('Belgium', 0), ('Germany', 6), ('Great Britain', 2), ('France', -3), ('Sweden', 1), ('Spain', 1), ('Italy', -9), ('Hungary', -3), ('Poland', -1), ('Japan', -1)].
   Caveat: the p19 legend says 2018 but the base note describes the 2014 wave (14 countries, Aug 2014). Stored under data/validation/, not used in pairs.csv.
8. Sum of Ipsos 'approximately' per-country samples: 22000 vs 22,989 interviews stated on p38 (Ipsos rounds per-country n).
9. countries.csv: 30 rows; web_presence missing for: none; income groups: {'Upper middle income': 10, 'High income': 19, 'Lower middle income': 1}.
```
<!-- validation:end -->
