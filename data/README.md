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
| `transcription/ipsos_2024_estimates.csv` | transcribed cell | 90 | hand-transcribed |
| `transcription/homicide_p22.csv`, `homicide_actual_p23_24.csv` | country | 30 each | hand-transcribed |
| `validation/truth_crosscheck.csv` | candidate truth value per (item, country, source) | 227 | sourced from primary databases; feeds the muslim_share T and documents alternatives |
| `raw/` | downloads, gitignored | | see Re-fetching below |

## Provenance

**Ipsos Perils of Perception 2024** (`ipsos_perils_2024_report` in `sources.csv`). Public PDF,
sha256 in `sources.csv`. H is Ipsos's "Average % mentioned" (a mean, don't-knows excluded).
For wealth_top1, T is the "Actual" column Ipsos prints next to it, with the source Ipsos cites.
For immigrant_share, T is the World Bank WDI copy of the UN DESA migrant-stock series (unrounded,
2024). For muslim_share, T is Pew's 2020 estimate from the June 2025 release (unrounded) for all
30 countries. In both cases the printed figure is kept in `t_value_ipsos` (decisions 2026-11-22):

| item | report page | T source cited by Ipsos | definition match |
|---|---|---|---|
| wealth_top1 | 13 (14 re-read) | World Inequality Database | approximate (households vs adults) |
| immigrant_share | 16 (17 re-read) | UN International Migrant Stock (cited); T used = World Bank WDI SM.POP.TOTL.ZS 2024 | yes (foreign-born) |
| muslim_share | 20 (re-read) | Pew Research (cited); T used = Pew 2020 estimate, June 2025 release | yes |
| homicide_trend | 22, direction from p11 and p23-24 | UN Office on Drugs and Crime | categorical |

**Transcription check.** Every H and T cell was transcribed twice on 2026-11-22. The first
reading used p13, p16 and p20. The second, independent reading used p14 and p17, where the
report restates average guess and actual for wealth and immigrants in a different order, and
re-read p20 for Muslim share (the only page that prints it). All 90 cells agreed on both H and
T, so there was nothing to resolve. The second reading was deleted afterwards and
`transcription/ipsos_2024_estimates.csv` is the single committed transcription; `pairs.csv`
carries `source_page`. Both readings were done by the same model session; the author
spot-checked `pairs.csv` against the PDF on 2026-11-22.

**Truth columns.** `t_value_ipsos` is the figure exactly as printed. `t_value` is the number
used in analysis, with `t_flag`:

| t_flag | meaning | rows |
|---|---|---|
| as_printed | wealth_top1: report prints a normal number; `t_value` equals it | 29 |
| world_bank | immigrant_share, all 30 countries: `t_value` is World Bank WDI SM.POP.TOTL.ZS (UN DESA series), year in `t_reference_year`; printed figure in `t_value_ipsos` | 30 |
| pew_2020 | muslim_share, all 30 countries: `t_value` is Pew's 2020 estimate (June 2025 release, five decimals), `t_reference_year` = 2020; printed figure in `t_value_ipsos` | 30 |
| missing | report prints "No data available" (Peru, wealth) | 1 |

**Pew vintage.** The muslim_share T comes from the 2020 column of the country table embedded in
Pew's Religious Composition by Country 2010-2020 interactive page (June 2025 release), which
gives shares to five decimals; Pew's Appendix B PDF prints the same rows rounded and was used as
a cross-check. No single Pew vintage reproduces Ipsos's printed figures: 8 countries match the
2020 column and 10 match a 2010 column (Türkiye 98 is Pew 2010, Pew 2020 is 97.1), so one
vintage is used throughout. All three Pew columns are in `validation/truth_crosscheck.csv`.

**Immigrant-share vintage.** Ipsos's printed immigrant figures match the UN DESA 2020 revision;
the dataset uses the 2024 revision via the World Bank series. UN DESA derives India's and
Indonesia's migrant stock from foreign-citizen data rather than place of birth, so those two
rows carry `definition_match = approximate` with a `definition_note` saying so. Both UN DESA
revisions are in `validation/truth_crosscheck.csv`.

**World Bank** (`countries.csv`): income group and region from the country endpoint;
GDP per capita PPP (`NY.GDP.PCAP.PP.CD`, latest year <= 2024); international migrant stock
% (`SM.POP.TOTL.ZS`, UN DESA, 2024), which is T for immigrant_share in `pairs.csv` (decision
2026-11-22); the Ipsos printed figure is retained in `t_value_ipsos` for comparison.

**Web presence** (`countries.csv`): `enwiki_mentions` = English Wikipedia exact-phrase search
total hits for the country name; `wikidata_p17_count` = number of Wikidata items whose country
is this country, where the SPARQL count finished before the 60 s server limit. Query strings and
fetch date are in `raw/web_presence.json` and `scripts/fetch_web_presence.py`.

## Special values

* No `t_value` is 0 or 0.5. Every muslim_share row carries Pew's unrounded 2020 estimate
  (`t_flag = pew_2020`), so the ten countries the report prints as "<1%" have real small numbers;
  every immigrant_share row carries the World Bank value (`t_flag = world_bank`), including India
  and Indonesia, which the report prints as 0%.
  The log-odds transform is defined for every pair except Peru wealth (`t_flag = missing`).
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

* 2026-11-22: truth rule. Keep the printed figure as text (`t_value_ipsos`) and a numeric `t_value`; where the report prints 0% or "<1%", `t_value` is the unrounded figure from the source Ipsos cites with provenance columns, never 0.5; if a source cannot be fetched the row is `source_unrounded_pending` with a blank `t_value`. Peru wealth stays `missing`. (Superseded the same day for immigrant_share and muslim_share by the World Bank and Pew decisions below; `t_unrounded_sources.csv` and the `source_unrounded` flag were removed.)
* 2026-11-22: per-row `entered_by`, `checked_by`, `second_pass_page` and `transcription_flag` columns dropped; the two-pass procedure is described once above, each row keeps `source_page`, and the comparison outcome is in the validation section.
* 2026-11-22: after both readings agreed on all 90 cells, the second reading was deleted and the first renamed to `transcription/ipsos_2024_estimates.csv`; the agreement check is recorded here and no longer recomputed by `validate.py`.

* 2026-11-22: paper restricted to data from 2020 onward; H1b (group-level flattening) removed because no 2020+ group-level human estimates were found. No group-level tables, scripts or party map are included.
* 2026-11-22: v0 uses the Ipsos 2024 wave only. Older waves (2014 to 2018) are not transcribed.
* 2026-11-22: the p19 comparator chart (legend says 2018, base note says 2014) is dropped entirely under the 2020+ rule.
* 2026-11-22: Ireland and New Zealand are not named on Ipsos's methodology page; treated as representative by author decision 2026-11-22.
* 2026-11-22: for wealth_top1, T is the value Ipsos prints with the source it cites (international databases), not national statistics offices.
* 2026-11-22: immigrant_share T switched from the Ipsos printed figure to the World Bank WDI 2024 migrant-stock series (same UN DESA origin, unrounded); the printed figure is retained in t_value_ipsos.
* 2026-11-22: muslim_share T switched to Pew's 2020 estimates (June 2025 release) for all 30 countries; no single Pew vintage reproduces Ipsos's printed figures (8 match 2020, 10 match a 2010 column), so one vintage is used throughout and the printed figure is kept in t_value_ipsos.
* 2026-11-22: web-presence covariate is English Wikipedia mention counts because the Wikidata P17 count times out for most large countries; Wikidata counts are kept where they completed.
* 2026-11-22: GDP per capita PPP uses the latest available year <= 2024 per country; income group is the current World Bank classification at retrieval, not the FY2025 classification by year.
* 2026-11-22: the two transcription passes were both done by the same model session reading different pages.
* 2026-11-22: human spot-check of pairs.csv against the PDF completed by the author.

## Follow-ups

* wealth_top1: Ipsos's printed values match no current WID year for 13 countries (older WID vintage); decision pending on switching wealth T to the current WID 2024 values, which would also fill Peru (WID has Peru, 38.55, modeled).
* UN DESA direct values (2024 revision), if later sourced, go in `data/validation/truth_crosscheck.csv` only; they do not replace T, which is the World Bank series.
* `wikidata_p17_count` completed for 2 of 30 countries before the SPARQL time limit; `enwiki_mentions` is the covariate to use.

## Validation results

Generated by `scripts/validate.py`.

<!-- validation:start -->
```
1. Range check: 90 rows, 0 outside [0,100].
   t_flag counts: {('immigrant_share', 'world_bank'): 30, ('muslim_share', 'pew_2020'): 30, ('wealth_top1', 'as_printed'): 29, ('wealth_top1', 'missing'): 1}
   T zero or blank (logit undefined): [('wealth_top1', 'Peru')]
   T below 1 percent (printed figure, T used): [('immigrant_share', 'Brazil', '1%', '0.7'), ('immigrant_share', 'India', '0%', '0.3'), ('immigrant_share', 'Indonesia', '0%', '0.2'), ('muslim_share', 'Argentina', '<1%', '0.9292'), ('muslim_share', 'Brazil', '<1%', '0.0177'), ('muslim_share', 'Chile', '<1%', '0.06699'), ('muslim_share', 'Colombia', '<1%', '0.00393'), ('muslim_share', 'Hungary', '<1%', '0.13922'), ('muslim_share', 'Japan', '<1%', '0.16997'), ('muslim_share', 'Mexico', '<1%', '0.00629'), ('muslim_share', 'Peru', '<1%', '0.02159'), ('muslim_share', 'Poland', '<1%', '0.00732'), ('muslim_share', 'South Korea', '<1%', '0.31')]
2. Countries per item: {'immigrant_share': 30, 'muslim_share': 30, 'wealth_top1': 30}. Missing T: [('wealth_top1', 'Peru', 'No data available')]
3. Question wording present verbatim in items.yaml for all items: yes.
4. Ipsos printed figure (t_value_ipsos) vs T used (t_value), per item; rows where |printed - T| > 2 points are flagged:
   wealth_top1 (T source: World Inequality Database)
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 26% | 26.00 () | +0.00 |
   | Australia | 24% | 24.00 () | +0.00 |
   | Belgium | 15% | 15.00 () | +0.00 |
   | Brazil | 49% | 49.00 () | +0.00 |
   | Canada | 25% | 25.00 () | +0.00 |
   | Chile | 50% | 50.00 () | +0.00 |
   | Colombia | 33% | 33.00 () | +0.00 |
   | Germany | 26% | 26.00 () | +0.00 |
   | Spain | 23% | 23.00 () | +0.00 |
   | France | 24% | 24.00 () | +0.00 |
   | Great Britain | 21% | 21.00 () | +0.00 |
   | Hungary | 33% | 33.00 () | +0.00 |
   | Indonesia | 30% | 30.00 () | +0.00 |
   | India | 33% | 33.00 () | +0.00 |
   | Ireland | 23% | 23.00 () | +0.00 |
   | Italy | 22% | 22.00 () | +0.00 |
   | Japan | 25% | 25.00 () | +0.00 |
   | South Korea | 26% | 26.00 () | +0.00 |
   | Mexico | 48% | 48.00 () | +0.00 |
   | Malaysia | 31% | 31.00 () | +0.00 |
   | Netherlands | 13% | 13.00 () | +0.00 |
   | New Zealand | 23% | 23.00 () | +0.00 |
   | Peru | No data available | missing () | n/a |
   | Poland | 30% | 30.00 () | +0.00 |
   | Singapore | 31% | 31.00 () | +0.00 |
   | Sweden | 28% | 28.00 () | +0.00 |
   | Thailand | 48% | 48.00 () | +0.00 |
   | Türkiye | 37% | 37.00 () | +0.00 |
   | United States | 35% | 35.00 () | +0.00 |
   | South Africa | 55% | 55.00 () | +0.00 |
   wealth_top1: countries where |printed - T| > 2 points: 0 
   immigrant_share (T source: World Bank WDI SM.POP.TOTL.ZS (UN DESA International Migrant Stock))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 5% | 4.30 (2024) | +0.70 |
   | Australia | 30% | 30.40 (2024) | -0.40 |
   | Belgium | 17% | 20.00 (2024) | -3.00 **>2pp** |
   | Brazil | 1% | 0.70 (2024) | +0.30 |
   | Canada | 21% | 22.20 (2024) | -1.20 |
   | Chile | 9% | 7.80 (2024) | +1.20 |
   | Colombia | 4% | 5.80 (2024) | -1.80 |
   | Germany | 19% | 19.80 (2024) | -0.80 |
   | Spain | 15% | 18.50 (2024) | -3.50 **>2pp** |
   | France | 13% | 13.80 (2024) | -0.80 |
   | Great Britain | 14% | 17.10 (2024) | -3.10 **>2pp** |
   | Hungary | 6% | 7.10 (2024) | -1.10 |
   | Indonesia | 0% | 0.20 (2024) | -0.20 |
   | India | 0% | 0.30 (2024) | -0.30 |
   | Ireland | 18% | 23.10 (2024) | -5.10 **>2pp** |
   | Italy | 11% | 11.00 (2024) | +0.00 |
   | Japan | 2% | 2.80 (2024) | -0.80 |
   | South Korea | 3% | 3.50 (2024) | -0.50 |
   | Mexico | 1% | 1.30 (2024) | -0.30 |
   | Malaysia | 11% | 10.70 (2024) | +0.30 |
   | Netherlands | 14% | 16.20 (2024) | -2.20 **>2pp** |
   | New Zealand | 29% | 28.20 (2024) | +0.80 |
   | Peru | 4% | 5.40 (2024) | -1.40 |
   | Poland | 2% | 4.50 (2024) | -2.50 **>2pp** |
   | Singapore | 43% | 48.70 (2024) | -5.70 **>2pp** |
   | Sweden | 20% | 21.40 (2024) | -1.40 |
   | Thailand | 5% | 4.40 (2024) | +0.60 |
   | Türkiye | 7% | 8.10 (2024) | -1.10 |
   | United States | 15% | 15.20 (2024) | -0.20 |
   | South Africa | 5% | 4.10 (2024) | +0.90 |
   immigrant_share: countries where |printed - T| > 2 points: 7 ['Belgium', 'Spain', 'Great Britain', 'Ireland', 'Netherlands', 'Poland', 'Singapore']
   muslim_share (T source: Pew Research Center, Religious Composition of the World's Population 2010-2020 (June 2025), 2020 estimate)
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | <1% | 0.9292 (2020) | n/a |
   | Australia | 3% | 3.50 (2020) | -0.50 |
   | Belgium | 8% | 6.81 (2020) | +1.19 |
   | Brazil | <1% | 0.0177 (2020) | n/a |
   | Canada | 3% | 4.89 (2020) | -1.89 |
   | Chile | <1% | 0.06699 (2020) | n/a |
   | Colombia | <1% | 0.00393 (2020) | n/a |
   | Germany | 7% | 6.55 (2020) | +0.45 |
   | Spain | 3% | 3.58 (2020) | -0.58 |
   | France | 8% | 9.10 (2020) | -1.10 |
   | Great Britain | 6% | 6.37 (2020) | -0.37 |
   | Hungary | <1% | 0.13922 (2020) | n/a |
   | Indonesia | 87% | 86.96 (2020) | +0.04 |
   | India | 15% | 15.19 (2020) | -0.19 |
   | Ireland | 2% | 1.69 (2020) | +0.31 |
   | Italy | 5% | 4.42 (2020) | +0.58 |
   | Japan | <1% | 0.16997 (2020) | n/a |
   | South Korea | <1% | 0.31 (2020) | n/a |
   | Mexico | <1% | 0.00629 (2020) | n/a |
   | Malaysia | 66% | 64.12 (2020) | +1.88 |
   | Netherlands | 7% | 5.50 (2020) | +1.50 |
   | New Zealand | 2% | 1.36 (2020) | +0.64 |
   | Peru | <1% | 0.02159 (2020) | n/a |
   | Poland | <1% | 0.00732 (2020) | n/a |
   | Singapore | 16% | 16.14 (2020) | -0.14 |
   | Sweden | 7% | 8.10 (2020) | -1.10 |
   | Thailand | 6% | 4.51 (2020) | +1.49 |
   | Türkiye | 98% | 97.11 (2020) | +0.89 |
   | United States | 1% | 1.19 (2020) | -0.19 |
   | South Africa | 2% | 1.60 (2020) | +0.40 |
   muslim_share: countries where |printed - T| > 2 points: 0 
   immigrant_share T is the World Bank WDI 2024 series and muslim_share T is Pew's 2020 estimate (decisions 2026-11-22); differences reflect the older source vintages Ipsos used and Ipsos rounding to whole percents. wealth_top1 T is the printed figure, so its differences are zero by construction.
5. definition_match per item: {('immigrant_share', 'yes'): 28, ('immigrant_share', 'approximate'): 2, ('muslim_share', 'yes'): 30, ('wealth_top1', 'approximate'): 30}. 'approximate' = wealth_top1 (households in question, adults in WID).
6. Sum of Ipsos 'approximately' per-country samples: 22000 vs 22,989 interviews stated on p38 (Ipsos rounds per-country n).
7. countries.csv: 30 rows; web_presence missing for: none; income groups: {'Upper middle income': 10, 'High income': 19, 'Lower middle income': 1}.
```
<!-- validation:end -->
