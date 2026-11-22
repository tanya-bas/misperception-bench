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
| `transcription/t_unrounded_sources.csv` | muslim_share pair where the report prints <1% | 10 | hand-entered from the cited source |
| `raw/` | downloads, gitignored | | see Re-fetching below |

## Provenance

**Ipsos Perils of Perception 2024** (`ipsos_perils_2024_report` in `sources.csv`). Public PDF,
sha256 in `sources.csv`. H is Ipsos's "Average % mentioned" (a mean, don't-knows excluded).
For wealth_top1 and muslim_share, T is the "Actual" column Ipsos prints next to it, with the
source Ipsos cites. For immigrant_share, T is the World Bank WDI copy of the UN DESA migrant-stock
series (unrounded, 2024) and the printed figure is kept in `t_value_ipsos` (decision 2026-11-22):

| item | report page | T source cited by Ipsos | definition match |
|---|---|---|---|
| wealth_top1 | 13 (14 re-read) | World Inequality Database | approximate (households vs adults) |
| immigrant_share | 16 (17 re-read) | UN International Migrant Stock (cited); T used = World Bank WDI SM.POP.TOTL.ZS 2024 | yes (foreign-born) |
| muslim_share | 20 (re-read) | Pew Research | yes |
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
| as_printed | wealth_top1 and muslim_share: report prints a normal number; `t_value` equals it | 49 |
| world_bank | immigrant_share, all 30 countries: `t_value` is World Bank WDI SM.POP.TOTL.ZS (UN DESA series), year in `t_reference_year`; printed figure in `t_value_ipsos` | 30 |
| source_unrounded | muslim_share: report prints <1%; `t_value` is the unrounded value from the source Ipsos cites, recorded in `t_unrounded_source`, `t_unrounded_url`, `t_unrounded_year` | 10 |
| source_unrounded_pending | same case, value not yet fetched; `t_value` blank | 0 |
| missing | report prints "No data available" (Peru, wealth) | 1 |

Unrounded sources used: Muslim share for the ten "<1%" countries from the country table
embedded in Pew's Religious Composition by Country 2010-2020 interactive page, 2020 column,
which gives shares to five decimals; Pew's Appendix B PDF prints the same rows as "<0.1" or
"0.9" and was used as a cross-check. Immigrant share no longer uses this mechanism: the World
Bank series covers all 30 countries, including India and Indonesia, which Ipsos printed as 0%.

Sample sizes, age ranges and the representative-sample flag are from the methodology page (p38).
Ipsos states that samples in Brazil, Chile, Colombia, Indonesia, Israel, Malaysia, Mexico, Peru,
Singapore, South Africa, Thailand and Türkiye are more urban, educated and affluent than the
general population, and that India's sample is an urban SEC A/B/C subset. Ireland and New
Zealand are named in neither list and are treated as representative (`yes`) by author decision
2026-11-22, recorded in the decisions log. Israel appears on p38 but in
none of the item tables, so it is not in the dataset.

**World Bank** (`countries.csv`): income group and region from the country endpoint;
GDP per capita PPP (`NY.GDP.PCAP.PP.CD`, latest year <= 2024); international migrant stock
% (`SM.POP.TOTL.ZS`, UN DESA, 2024), which is T for immigrant_share in `pairs.csv` (decision
2026-11-22); the Ipsos printed figure is retained in `t_value_ipsos` for comparison.

**Web presence** (`countries.csv`): `enwiki_mentions` = English Wikipedia exact-phrase search
total hits for the country name; `wikidata_p17_count` = number of Wikidata items whose country
is this country, where the SPARQL count finished before the 60 s server limit. Query strings and
fetch date are in `raw/web_presence.json` and `scripts/fetch_web_presence.py`.

## Special values

* No `t_value` is 0 or 0.5. The ten muslim_share rows the report prints as "<1%" carry Pew's
  unrounded value (`t_flag = source_unrounded`); the two immigrant_share rows printed as 0%
  (India, Indonesia) carry the World Bank value like every other country (`t_flag = world_bank`).
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

* 2026-11-22: truth rule. Keep the printed figure as text (`t_value_ipsos`) and a numeric `t_value`; where the report prints 0% or "<1%", `t_value` is the unrounded figure from the source Ipsos cites with provenance columns, never 0.5; if a source cannot be fetched the row is `source_unrounded_pending` with a blank `t_value`. Peru wealth stays `missing`.
* 2026-11-22: per-row `entered_by`, `checked_by`, `second_pass_page` and `transcription_flag` columns dropped; the two-pass procedure is described once above, each row keeps `source_page`, and the comparison outcome is in the validation section.
* 2026-11-22: after both readings agreed on all 90 cells, the second reading was deleted and the first renamed to `transcription/ipsos_2024_estimates.csv`; the agreement check is recorded here and no longer recomputed by `validate.py`.

* 2026-11-22: paper restricted to data from 2020 onward; H1b (group-level flattening) removed because no 2020+ group-level human estimates were found. No group-level tables, scripts or party map are included.
* 2026-11-22: v0 uses the Ipsos 2024 wave only. Older waves (2014 to 2018) are not transcribed.
* 2026-11-22: the p19 comparator chart (legend says 2018, base note says 2014) is dropped entirely under the 2020+ rule.
* 2026-11-22: Ireland and New Zealand are not named on Ipsos's methodology page; treated as representative by author decision 2026-11-22.
* 2026-11-22: for wealth_top1 and muslim_share, T is the value Ipsos prints with the source it cites (international databases), not national statistics offices.
* 2026-11-22: immigrant_share T switched from the Ipsos printed figure to the World Bank WDI 2024 migrant-stock series (same UN DESA origin, unrounded); the printed figure is retained in t_value_ipsos.
* 2026-11-22: web-presence covariate is English Wikipedia mention counts because the Wikidata P17 count times out for most large countries; Wikidata counts are kept where they completed.
* 2026-11-22: GDP per capita PPP uses the latest available year <= 2024 per country; income group is the current World Bank classification at retrieval, not the FY2025 classification by year.
* 2026-11-22: the two transcription passes were both done by the same model session reading different pages.
* 2026-11-22: human spot-check of pairs.csv against the PDF completed by the author.

## Follow-ups

* Pew vintage: Ipsos's printed Muslim share for Türkiye (98) matches Pew's 2010 figure (98.6) better than Pew's 2020 figure (97.1), so Ipsos may have used an earlier Pew release for its "Actual" column. The ten unrounded values use Pew 2020. Decide whether to re-source all muslim_share T from one Pew vintage.
* UN DESA direct values (2024 revision), if later sourced, go in `data/validation/truth_crosscheck.csv` only; they do not replace T, which is the World Bank series.
* `wikidata_p17_count` completed for 2 of 30 countries before the SPARQL time limit; `enwiki_mentions` is the covariate to use.

## Validation results

Generated by `scripts/validate.py`.

<!-- validation:start -->
```
1. Range check: 90 rows, 0 outside [0,100].
   t_flag counts: {('immigrant_share', 'world_bank'): 30, ('muslim_share', 'source_unrounded'): 10, ('muslim_share', 'as_printed'): 20, ('wealth_top1', 'as_printed'): 29, ('wealth_top1', 'missing'): 1}
   T zero or blank (logit undefined): [('wealth_top1', 'Peru')]; source_unrounded_pending: none
   printed vs unrounded for source_unrounded rows: [('muslim_share', 'Argentina', '<1%', '0.9292'), ('muslim_share', 'Brazil', '<1%', '0.0177'), ('muslim_share', 'Chile', '<1%', '0.06699'), ('muslim_share', 'Colombia', '<1%', '0.00393'), ('muslim_share', 'Hungary', '<1%', '0.13922'), ('muslim_share', 'Japan', '<1%', '0.16997'), ('muslim_share', 'Mexico', '<1%', '0.00629'), ('muslim_share', 'Peru', '<1%', '0.02159'), ('muslim_share', 'Poland', '<1%', '0.00732'), ('muslim_share', 'South Korea', '<1%', '0.31')]
2. Countries per item: {'immigrant_share': 30, 'muslim_share': 30, 'wealth_top1': 30}. Missing T: [('wealth_top1', 'Peru', 'No data available')]
3. Question wording present verbatim in items.yaml for all items: yes.
4. immigrant_share: Ipsos printed figure (t_value_ipsos) vs World Bank WDI T used (t_value):
   | country | Ipsos printed | WDI T (year) | printed - T |
   |---|---|---|---|
   | Argentina | 5% | 4.3 (2024) | +0.7 |
   | Australia | 30% | 30.4 (2024) | -0.4 |
   | Belgium | 17% | 20.0 (2024) | -3.0 **>2pp** |
   | Brazil | 1% | 0.7 (2024) | +0.3 |
   | Canada | 21% | 22.2 (2024) | -1.2 |
   | Chile | 9% | 7.8 (2024) | +1.2 |
   | Colombia | 4% | 5.8 (2024) | -1.8 |
   | Germany | 19% | 19.8 (2024) | -0.8 |
   | Spain | 15% | 18.5 (2024) | -3.5 **>2pp** |
   | France | 13% | 13.8 (2024) | -0.8 |
   | Great Britain | 14% | 17.1 (2024) | -3.1 **>2pp** |
   | Hungary | 6% | 7.1 (2024) | -1.1 |
   | Indonesia | 0% | 0.2 (2024) | -0.2 |
   | India | 0% | 0.3 (2024) | -0.3 |
   | Ireland | 18% | 23.1 (2024) | -5.1 **>2pp** |
   | Italy | 11% | 11.0 (2024) | +0.0 |
   | Japan | 2% | 2.8 (2024) | -0.8 |
   | South Korea | 3% | 3.5 (2024) | -0.5 |
   | Mexico | 1% | 1.3 (2024) | -0.3 |
   | Malaysia | 11% | 10.7 (2024) | +0.3 |
   | Netherlands | 14% | 16.2 (2024) | -2.2 **>2pp** |
   | New Zealand | 29% | 28.2 (2024) | +0.8 |
   | Peru | 4% | 5.4 (2024) | -1.4 |
   | Poland | 2% | 4.5 (2024) | -2.5 **>2pp** |
   | Singapore | 43% | 48.7 (2024) | -5.7 **>2pp** |
   | Sweden | 20% | 21.4 (2024) | -1.4 |
   | Thailand | 5% | 4.4 (2024) | +0.6 |
   | Türkiye | 7% | 8.1 (2024) | -1.1 |
   | United States | 15% | 15.2 (2024) | -0.2 |
   | South Africa | 5% | 4.1 (2024) | +0.9 |
   Countries where |printed - T| > 2 points: 7. T is the World Bank series (decision 2026-11-22); differences reflect the UN DESA release Ipsos used and Ipsos rounding to whole percents.
5. definition_match per item: {('immigrant_share', 'yes'): 30, ('muslim_share', 'yes'): 30, ('wealth_top1', 'approximate'): 30}. 'approximate' = wealth_top1 (households in question, adults in WID).
6. Sum of Ipsos 'approximately' per-country samples: 22000 vs 22,989 interviews stated on p38 (Ipsos rounds per-country n).
7. countries.csv: 30 rows; web_presence missing for: none; income groups: {'Upper middle income': 10, 'High income': 19, 'Lower middle income': 1}.
```
<!-- validation:end -->
