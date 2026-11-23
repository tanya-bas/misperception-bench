# misperception-bench data, v1

Human estimates (H), truth values (T) and country covariates for the paper
*Lost in Average: How LLMs Erase Differences in What the World Believes*.
Scope: four Ipsos waves. `ipsos_2024` (Perils of Perception 2024, 30 countries, fieldwork 20
September to 4 October 2024; the v0 dataset, unchanged), `ipsos_2020` (Perils of Perception 2020,
causes of death, 32 countries, fieldwork 22 November to 6 December 2019, published February 2020),
`ipsos_royaumont_2023` (Ipsos for the Entretiens de Royaumont, December 2023, 10 countries,
fieldwork 22 to 25 November 2023; the 2024 items asked a year earlier, a replication of H that
reuses the 2024 T) and `ipsos_earthday_2022` (Ipsos Global Advisor Earth Day 2022, 31 countries,
fieldwork 18 February to 4 March 2022; one banded degrees-Celsius item in its own table). Every
value carries the document and page it came from. Inclusion rule: surveys published from 2020 onward.

## Files

| File | One row per | Rows | Built by |
|---|---|---|---|
| `items.yaml` | item | 11 (4 from 2024, 6 from 2020, 1 from Earth Day 2022) | hand-written |
| `sources.csv` | document, dataset or API dump | 13 | hand-written |
| `pairs.csv` | country x percent item | 309 (90 `ipsos_2024` + 190 `ipsos_2020` + 29 `ipsos_royaumont_2023`) | `scripts/build_pairs.py` |
| `pairs_categorical.csv` | country x homicide-trend item | 40 (30 `ipsos_2024` + 10 `ipsos_royaumont_2023`) | `scripts/build_pairs.py` |
| `pairs_banded.csv` | country x banded degrees-Celsius item (Earth Day 2022) | 31 | `scripts/build_pairs.py` |
| `countries.csv` | country | 38 (30 from 2024 + 6 only in 2020 + 2 only in Earth Day 2022) | `scripts/build_countries.py` |
| `transcription/ipsos_2024_estimates.csv` | transcribed cell | 90 | hand-transcribed |
| `transcription/homicide_p22.csv`, `homicide_actual_p23_24.csv` | country | 30 each | hand-transcribed |
| `transcription/ipsos_2020_estimates.csv` | transcribed cell (six usable cause pages) | 190 | transcribed from the PDF text layer, checked against page images |
| `transcription/ipsos_2020_defective_pages.csv` | printed row of the three unusable cause pages (p19, p21, p25) | 95 | record only, not built into `pairs.csv` |
| `transcription/ipsos_royaumont_2023_estimates.csv` | bar-chart label pair (incl. the "Global Average" bars, which are not built) | 32 | transcribed from the PDF text layer, checked against page images |
| `transcription/ipsos_royaumont_2023_homicide_p6.csv` | country (incl. "Global Average") | 11 | same |
| `transcription/ipsos_earthday_2022_p21.csv` | country column of the p21 band table (incl. the all-country column, not built) | 32 | two text-layer extractions, checked against the page image |
| `validation/truth_crosscheck.csv` | candidate truth value per (item, country, source) | 227 | sourced from primary databases; feeds the muslim_share T and documents alternatives |
| `raw/` | downloads, gitignored | | see Re-fetching below |

## Provenance

**Ipsos Perils of Perception 2024** (`ipsos_perils_2024_report` in `sources.csv`). Public PDF,
sha256 in `sources.csv`. H is Ipsos's "Average % mentioned" (a mean, don't-knows excluded).
T for every item is taken from the primary source Ipsos cites, at one current vintage, for all
30 countries: the World Bank WDI copy of the UN DESA migrant-stock series (2024) for
immigrant_share, Pew's 2020 estimate from the June 2025 release for muslim_share, and the World
Inequality Database 2024 top-1% net personal wealth share for wealth_top1. The figure Ipsos
printed is kept in `t_value_ipsos` in every row (decisions 2026-11-22):

| item | report page | T source cited by Ipsos | definition match |
|---|---|---|---|
| wealth_top1 | 13 (14 re-read) | World Inequality Database (cited); T used = WID 2024 top-1% net personal wealth share, via the Our World in Data mirror | approximate (households vs adults) |
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
| world_bank | immigrant_share, all 30 countries: `t_value` is World Bank WDI SM.POP.TOTL.ZS (UN DESA series), year in `t_reference_year`; printed figure in `t_value_ipsos` | 30 |
| pew_2020 | muslim_share, all 30 countries: `t_value` is Pew's 2020 estimate (June 2025 release, five decimals), `t_reference_year` = 2020; printed figure in `t_value_ipsos` | 30 |
| wid_2024 | wealth_top1, all 30 countries: `t_value` is the WID 2024 top-1% share of net personal wealth (WID 2026 release via the Our World in Data mirror), `t_reference_year` = 2024; printed figure in `t_value_ipsos`; fills Peru | 30 |
| ipsos_printed_gbd2017 | ipsos_2020 items: `t_value` is the printed actual, which Ipsos sources from IHME GBD 2017; `t_reference_year` = 2017 | 177 |
| ipsos_printed_gbd2017_swap_corrected | ipsos_2020 cardiovascular, Saudi Arabia and Germany: `t_value` is the other row's printed figure (see Truth, 2020) | 2 |
| ipsos_printed_healthyhk | ipsos_2020 Hong Kong: printed actual sourced by Ipsos from healthyhk.gov.hk; reference year not stated | 5 |
| source_unrounded_pending | ipsos_2020 HIV/STI rows printed as "0.0": `t_value` blank | 6 |

The `as_printed` and `missing` flags are no longer produced by any item.

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

**Wealth vintage.** Ipsos's printed wealth figures match no current WID year for 13 countries,
so Ipsos used an older WID vintage. The dataset uses the current WID 2024 value for all 30
countries from the Our World in Data mirror of the WID 2026 release (interpolations and
extrapolations excluded). This also fills Peru, printed as "No data available" by Ipsos; WID
marks Peru as modeled, recorded in that row's `definition_note`.

**Ipsos Perils of Perception 2020, causes of death** (`ipsos_perils_2020_causes_of_death_deck` in
`sources.csv`, wave `ipsos_2020`). Public 54-page PDF, sha256 in `sources.csv`; downloaded 2026-11-22.
Question stem on every cause page: "Out of every 100 deaths in [COUNTRY] – about many are a result
of ...?" (the deck omits "how" on every page and keeps its "[COUNTRY]" placeholder; both are kept
verbatim in `question_wording`, noted in `items.yaml`). H is Ipsos's "Avg. guess" (a mean). T is
Ipsos's printed "Actual", which the technical note (p53) sources from the IHME Global Burden of
Disease Study 2017 (Hong Kong: healthyhk.gov.hk). Of the 14 causes in the deck, nine have a
per-country page and five (lower respiratory infections, chronic respiratory diseases, diabetes and
kidney diseases, digestive diseases, accidental deaths such as drowning) have only all-country
averages (p5-6) and are not included. Of the nine, six are transcribed:

| item | deck page | GBD cause group behind Ipsos's actual | definition match | countries |
|---|---|---|---|---|
| deaths_cancer | 13 | Neoplasms | yes | 32 |
| deaths_cardiovascular | 14 | Cardiovascular diseases | yes | 32 |
| deaths_neurological | 15 | Neurological disorders | yes | 32 |
| deaths_hiv_sti | 16 | HIV/AIDS and sexually transmitted infections | yes | 31 (no Saudi Arabia) |
| deaths_violence | 18 | Interpersonal violence | yes | 31 (no Saudi Arabia) |
| deaths_suicide | 23 | Self-harm | yes | 32 |

Hong Kong rows carry `definition_match = approximate` because their actual is the Hong Kong
government's figure, not GBD's. Country names are as printed in the 2020 deck ("United Kingdom",
"Turkey", "Hong Kong SAR China"); the join key is `country_iso3`.

**Three 2020 pages are defective and are not built into `pairs.csv`** (decision 2026-11-22; the
printed rows are kept in `transcription/ipsos_2020_defective_pages.csv`):

* p19 (terrorism and conflict) prints 32 country labels and 32 difference bars but only 30
  guess/actual rows, in a column whose line spacing differs from the label column (12.9 vs 13.75 pt
  in the text layer). The 30 values cannot be attributed to countries: the printed differences
  show that Mexico's values are absent, and the second absent row is one of Romania, Argentina,
  Netherlands, South Korea or Canada.
* p21 (substance use disorders) prints 31 labels and bars but 30 guess/actual rows; the absent row
  is one of Belgium, China, Poland, Japan, the Philippines or the United Kingdom.
* p25 (transport injuries) prints the suicide guess/actual values of p23 for 30 of its 32 rows (only
  Hong Kong and the Philippines differ), and its column mean (7.5 guess, 1.5 actual) does not match
  the deck's own all-country transport average on p6 (10.0, 2.0), whereas the six transcribed pages
  reproduce their p6 averages to one decimal. The page is treated as corrupted.

**Transcription check, 2020.** Pass 1 parsed the PDF text layer word by word (`pdftotext -tsv`),
pairing country labels with guess/actual values by vertical rank within each page and requiring
equal counts (this is how the p19/p21 defects surfaced). Pass 2 re-read the rendered page images
(`pdftoppm`, 130 dpi) independently. All 190 cells of the six usable pages agreed on both H and T;
nothing had to be resolved. Two further consistency checks passed: the per-page means of the
transcribed columns match the all-country averages Ipsos prints on p6 for all six items (e.g.
cancer 14.7 / 23.6, cardiovascular 10.7 / 32.0, suicide 7.3 / 1.6), and Ipsos's printed
difference column equals guess minus actual to within rounding for every row except the two
swapped cardiovascular actuals described below (and two HIV/STI rows, France and Belgium, that are
within 0.1 of a rounding boundary). Both passes were done by the same model session;
`transcription/ipsos_2020_estimates.csv` is the single committed transcription, and `pairs.csv`
carries `source_page`.

**Truth, 2020.** The plan was to take T for every country from Our World in Data's GBD-based
share-of-deaths-by-cause dataset at the latest GBD vintage, mapping cancer to Neoplasms,
substance use to alcohol plus drug use disorders, suicide to Self-harm, and so on. OWID now refuses
to serve IHME data: the chart CSV
(`https://ourworldindata.org/grapher/share-of-deaths-by-cause.csv`) and the indicator endpoints
(`https://api.ourworldindata.org/v1/indicators/<id>.data.json`) both return HTTP 403 with the
message that the data "comes from a source that doesn't allow us to redistribute it" (checked
2026-11-22; the current OWID vintage is GBD 2023, catalog `ihme_gbd/2026-02-07`, indicator IDs
1162665 neoplasms, 1162356 cardiovascular, 1162676 neurological, 1162521 HIV/AIDS and STIs,
1162554 interpersonal violence, 1162841 self-harm, 1162864 substance use, 1162899 transport,
1162411 conflict and terrorism). The fallback adopted the same day is Ipsos's printed GBD 2017
actual, `t_flag = ipsos_printed_gbd2017` (`ipsos_printed_healthyhk` for Hong Kong), with
`t_reference_year = 2017`; the pull from a GBD source stays a follow-up. Two adjustments:

* On p14 the printed actuals of Saudi Arabia (37.6) and Germany (33.4), adjacent rows, are swapped:
  Ipsos's own printed differences (-23, -24) and bars require 33.4 for Saudi Arabia (10.1 - 33.4)
  and 37.6 for Germany (14.1 - 37.6), and Destatis gives 37.0% of German deaths from cardiovascular
  disease in 2017. `t_value` takes the figure the difference implies, `t_value_ipsos` stays as
  printed, `t_flag = ipsos_printed_gbd2017_swap_corrected`.
* Six HIV/STI rows are printed as "0.0" (Hong Kong, Hungary, Japan, Netherlands, Poland, Sweden).
  `t_value` is blank with `t_flag = source_unrounded_pending`, never 0 or 0.5; these six pairs have
  no log-odds transform until an unrounded figure is sourced.

**Sample metadata, 2020** (technical note, p53). "16,000 interviews were conducted between 22
November and 6 December 2019." Representative: "18 of the 32 countries surveyed online generate
nationally representative samples in their countries (Argentina, Australia, Belgium, Canada,
France, Germany, Great Britain, Hong Kong SAR China, Hungary, Italy, Japan, Netherlands, Poland,
Singapore, South Korea, Spain, Sweden and United States)." Not representative: "Brazil, Chile,
Colombia, China, India, Malaysia, Mexico, Peru, Philippines, Romania, Russia, Saudi Arabia, South
Africa, and Turkey produce a national sample that is more urban & educated, and with higher
incomes than their fellow citizens." The two lists cover all 32 countries, so the Ireland/New
Zealand precedent was not needed. Singapore is representative here but urban/affluent in 2024;
`countries.csv` keeps the 2024 flag and `pairs.csv` carries the per-wave flag. Sample sizes:
"Approximately 1000 individuals aged 16-74 were surveyed Argentina, Australia, Belgium, Brazil,
Chile, China, France, Germany, Great Britain, Italy, Japan, Mexico and Spain. Approximately 1000
individuals aged 18-74 were surveyed in the USA and Canada. Approximately 500 individuals aged
16-74 were surveyed in Argentina, Belgium, Colombia, Hong Kong SAR China, Hungary, India,
Malaysia, Netherlands, Peru, Poland, Romania, Russia, Saudi Arabia, Singapore, South Africa,
South Korea, Sweden and Turkey." Argentina and Belgium are in both lists and the Philippines in
neither, so `n_country_approx` is `not_stated` for those three (and `age_range` for the
Philippines); the stated n sum to 21,000 against 16,000 interviews, which equals 32 x 500, so
the lists may be boilerplate. Recorded as printed, not corrected.

**Ipsos for the Entretiens de Royaumont, December 2023** (`ipsos_royaumont_2023_deck` in
`sources.csv`, wave `ipsos_royaumont_2023`). "Perils of perception, prejudice and conspiracy
theories", an 18-page public deck; "Survey conducted among 10,000 people on the Ipsos Digital
platform from 22 to 25 November 2023" (p1), 10 countries (Australia, United Kingdom, Germany,
Poland, France, Japan, Argentina, Italy, Turkey, United States), so about 1,000 per country. The
deck does not state age ranges or describe the samples as nationally representative, so
`age_range` and `representative_sample` are `not_stated` (decision 2026-11-22). Pages 3 to 5
chart "Actual Data" against "Respondents' Perception" for the three 2024 percent items with
identical wording (wealth_top1 p3, immigrant_share p4, muslim_share p5, which omits Turkey: 9
countries), and p6 charts the share answering "higher" to the 2024 homicide question. The "Global
Average" bars are transcribed but not built. H is the perception bar label (a mean, whole percents;
the Muslim-share actuals carry a decimal comma, kept as printed in `t_value_ipsos`, e.g. "0,0%").

**Truth, Royaumont 2023.** T, `t_flag`, `t_source`, `t_reference_year` and the definition columns
are copied from the `ipsos_2024` row of the same country and item (World Bank 2024, Pew 2020, WID
2024), so each item has one truth vintage across waves; the deck's own printed actuals (World
Inequality Database, IOM World Migration Report 2022, World Population Review) stay in
`t_value_ipsos`. The wave therefore serves as a replication of H one year earlier, not as an
independent truth point (decision 2026-11-22). `validate.py` check 9 enforces the identity. The
deck's printed wealth actuals (10% to 21%) are far below any WID top-1% wealth share (21% to 35%
for these countries) and look like WID top-1% income shares printed against the wealth question,
one more reason not to use them as T; all ten wealth rows are therefore flagged in validation
check 4. For the homicide item only the "higher" share is printed; `pct_same` and `pct_lower` are blank,
`public_majority` is "higher" where that share exceeds 50 and blank otherwise (Poland and Japan,
43%), and `actual_direction` follows the p6 footnote "Homicide rates have gone down significantly
in all these countries – except the United States" (source: World Bank): `lower` for nine
countries, `same_or_higher` for the United States.

**Transcription check, Royaumont 2023.** Pass 1 clustered the text layer's percent labels to the
nearest country label by x-position (`pdftotext -tsv`); pass 2 read the rendered page images. All
43 label groups (75 values, including the Global Average bars) agreed.

**Ipsos Global Advisor, Earth Day 2022** (`ipsos_earthday_2022_release2` in `sources.csv`, wave
`ipsos_earthday_2022`, table `pairs_banded.csv`). Release 2 of the April 2022 report, 32 pages.
"Q. How much do you think the climate of the Earth has warmed since 1850, if at all?" with the
answer bands 0-0.75, 1-1.75, 2-2.75 and 3-4 degrees Celsius plus "Don't know", one column per
country on p21 (31 countries and an all-country column). This is not a share, so it is stored in
`pairs_banded.csv` with `scale = degrees_c`, `transform = none`, the bands and percentages as JSON,
`pct_dk`, and `h_mean_midpoint` = the percentage-weighted mean of the band midpoints 0.375,
1.375, 2.375 and 3.5 over the four bands with don't-know excluded (midpoints listed in
`items.yaml`). Applied to the all-country column (7 / 17 / 15 / 15) the rule gives 2.11, which
reproduces the "Mean: 2.1 degrees Celsius" Ipsos prints on p20. Norway has no don't-know option
(printed "-"; p29 notes its data is not comparable for some questions). The bands plus don't-know
sum to 90-101 per country (90 in Peru, 92 India, 93 Russia and Turkey); the deck prints no further
category. **The item sits outside the log-odds analyses**: it is compared with T in degrees and as
a band distribution only.

**Truth, Earth Day 2022.** The deck states "True value: 1 degree Celsius" citing IPCC SR15
chapter 1 (p20); that is kept in `t_value_ipsos`. `t_value` = 1.1 from IPCC AR6 WG1 SPM A.1.2
(global surface temperature in 2011-2020 was 1.09 [0.95 to 1.20] degrees C above 1850-1900),
`t_flag = ipcc_ar6_wg1_spm`, `definition_match = approximate`: the question asks about warming up
to the time of asking (February to March 2022), while T is the 2011-2020 decade average, and the
deck's 1 degree is SR15's 2017 figure (decision 2026-11-22).

**Sample metadata, Earth Day 2022** (technical note, p27). 23,577 adults, 18 February to 4 March
2022, 31 countries; "Approximately 1000+ individuals participated on a country-by-country basis
... with the exception of Argentina, Belgium, Chile, Colombia, Hungary, India, Ireland, Malaysia,
Mexico, the Netherlands, Peru, Poland, Russia, Saudi Arabia, South Africa, South Korea, Sweden,
Switzerland and Turkey, where each have a sample of approximately 500+"; "aged 18-74 in the US,
Canada, Hong Kong, Malaysia, South Africa, and Turkey, aged 16-99 in Norway and age 16-74 in all
other countries". Representative: "18 of the 31 countries surveyed online generate nationally
representative samples in their countries (Argentina, Australia, Belgium, Canada, France,
Germany, Great Britain, Hungary, Italy, Japan, the Netherlands, Norway Poland, South Korea, Spain,
Sweden, Switzerland and United States)"; "The samples in Brazil, Chile, mainland China, Colombia,
India, Ireland Malaysia, Mexico, Peru, Russia, Saudi Arabia, South Africa and Turkey are more urban
& educated, and/or more affluent than the general population." Both lists cover all 31 countries
(Ireland is not representative in this wave; the 2024 Ireland decision applies to 2024 only).
Switzerland and Norway are added to `countries.csv` from the cached World Bank dumps and a
web-presence fetch of the same day.

**Transcription check, Earth Day 2022.** Pass 1 parsed the p21 layout text line by line (five
band rows of 32 values); pass 2 re-derived the table from word coordinates (`pdftotext -tsv`,
nearest column header by x and nearest band label by y). All 160 cells agreed, and the page image
was checked for the values that drive the sums. The all-country column reproduces the deck's
printed mean as described above.

**World Bank** (`countries.csv`): income group and region from the country endpoint;
GDP per capita PPP (`NY.GDP.PCAP.PP.CD`, latest year <= 2024); international migrant stock
% (`SM.POP.TOTL.ZS`, UN DESA, 2024), which is T for immigrant_share in `pairs.csv` (decision
2026-11-22); the Ipsos printed figure is retained in `t_value_ipsos` for comparison.

**Web presence** (`countries.csv`): `enwiki_mentions` = English Wikipedia exact-phrase search
total hits for the country name; `wikidata_p17_count` = number of Wikidata items whose country
is this country, where the SPARQL count finished before the 60 s server limit. Query strings and
fetch date are in `raw/web_presence.json` and `scripts/fetch_web_presence.py`.

## Special values

* No `t_value` is 0 or 0.5. The only blank `t_value`s are the six ipsos_2020 HIV/STI rows printed as
  "0.0" (`t_flag = source_unrounded_pending`); analysis code skips rows with blank T. In the 2024
  wave no `t_value` is blank: every muslim_share row carries Pew's unrounded 2020 estimate
  (`t_flag = pew_2020`), so the ten countries the report prints as "<1%" have real small numbers;
  every immigrant_share row carries the World Bank value (`t_flag = world_bank`), including India
  and Indonesia, which the report prints as 0%; every wealth_top1 row carries the WID 2024 value
  (`t_flag = wid_2024`), including Peru, which the report prints as "No data available".
  The log-odds transform is defined for all 90 pairs of 2024 and 184 of the 190 pairs of 2020.
* `t_value_ipsos` in the 2020 wave is the one-decimal figure as printed, without a percent sign
  (the deck's column header is "% actual causes of death"); "0.0" is a rounded zero.
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
curl -L -o data/raw/ipsos-perils-of-perception-2020-causes-of-death.pdf \
  https://www.ipsos.com/sites/default/files/ct/news/documents/2020-02/ipsos-perils-of-perception-2020-causes-of-death.pdf
curl -L -o data/raw/ipsos-perils-perception-prejudice-conspiracy-theories-december-2023.pdf \
  https://www.ipsos.com/sites/default/files/ct/news/documents/2023-12/ipsos-perils-perception-prejudice-conspiracy-theories-december-2023.pdf
curl -L -o data/raw/ipsos-global-advisor-earth-day-2022-release-2.pdf \
  "https://www.ipsos.com/sites/default/files/ct/news/documents/2022-04/Ipsos%20-%20Global%20Advisor%20-%20Earth%20Day%202022%20-%20Release%202.pdf"
mkdir -p data/raw/worldbank
curl -sL "https://api.worldbank.org/v2/country?format=json&per_page=400" -o data/raw/worldbank/countries.json
curl -sL "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.CD?format=json&per_page=20000&mrv=12" -o data/raw/worldbank/NY.GDP.PCAP.PP.CD.json
curl -sL "https://api.worldbank.org/v2/country/all/indicator/SM.POP.TOTL.ZS?format=json&per_page=20000&mrv=12" -o data/raw/worldbank/SM.POP.TOTL.ZS.json
python3 -I scripts/fetch_web_presence.py      # network; resumable
```

Then rebuild: `python3 -I scripts/build_pairs.py && python3 -I scripts/build_countries.py && python3 -I scripts/validate.py`.

## Decisions log

* 2026-11-22: truth rule. Keep the printed figure as text (`t_value_ipsos`) and a numeric `t_value`; where the report prints 0% or "<1%", `t_value` is the unrounded figure from the source Ipsos cites with provenance columns, never 0.5; if a source cannot be fetched the row is `source_unrounded_pending` with a blank `t_value`. Peru wealth stays `missing`. (Superseded the same day for all three items by the World Bank, Pew and WID decisions below; `t_unrounded_sources.csv` and the `source_unrounded` flag were removed, and Peru wealth is now filled.)
* 2026-11-22: per-row `entered_by`, `checked_by`, `second_pass_page` and `transcription_flag` columns dropped; the two-pass procedure is described once above, each row keeps `source_page`, and the comparison outcome is in the validation section.
* 2026-11-22: after both readings agreed on all 90 cells, the second reading was deleted and the first renamed to `transcription/ipsos_2024_estimates.csv`; the agreement check is recorded here and no longer recomputed by `validate.py`.

* 2026-11-22: paper restricted to data from 2020 onward; H1b (group-level flattening) removed because no 2020+ group-level human estimates were found. No group-level tables, scripts or party map are included.
* 2026-11-22: v0 uses the Ipsos 2024 wave only. Older waves (2014 to 2018) are not transcribed.
* 2026-11-22: the p19 comparator chart (legend says 2018, base note says 2014) is dropped entirely under the 2020+ rule.
* 2026-11-22: Ireland and New Zealand are not named on Ipsos's methodology page; treated as representative by author decision 2026-11-22.
* 2026-11-22: for wealth_top1, T is the value Ipsos prints with the source it cites (international databases), not national statistics offices. (Superseded the same day by the WID decision below.)
* 2026-11-22: immigrant_share T switched from the Ipsos printed figure to the World Bank WDI 2024 migrant-stock series (same UN DESA origin, unrounded); the printed figure is retained in t_value_ipsos.
* 2026-11-22: muslim_share T switched to Pew's 2020 estimates (June 2025 release) for all 30 countries; no single Pew vintage reproduces Ipsos's printed figures (8 match 2020, 10 match a 2010 column), so one vintage is used throughout and the printed figure is kept in t_value_ipsos.
* 2026-11-22: wealth_top1 T switched to WID 2024 values for all 30 countries (fills Peru; replaces 13 printed values that match no current WID year because Ipsos used an older WID vintage).
* 2026-11-22: web-presence covariate is English Wikipedia mention counts because the Wikidata P17 count times out for most large countries; Wikidata counts are kept where they completed.
* 2026-11-22: GDP per capita PPP uses the latest available year <= 2024 per country; income group is the current World Bank classification at retrieval, not the FY2025 classification by year.
* 2026-11-22: the two transcription passes were both done by the same model session reading different pages.
* 2026-11-22: human spot-check of pairs.csv against the PDF completed by the author.
* 2026-11-22: inclusion rule stated as publication date 2020 onward; Ipsos Perils of Perception 2020 (causes of death) admitted on that basis.
* 2026-11-22: of the nine 2020 causes with a per-country page, three (terrorism and conflict p19, substance use disorders p21, transport injuries p25) are not built into pairs.csv because the printed pages are defective (p19 and p21 have fewer value rows than country labels; p25 repeats the p23 suicide values); their printed rows are kept in `transcription/ipsos_2020_defective_pages.csv`. The five causes with only all-country averages are not included.
* 2026-11-22: 2020 T rule. Planned: Our World in Data's GBD-based share-of-deaths dataset at the latest vintage, one vintage for all countries, Ipsos's printed value kept in t_value_ipsos. OWID refuses to serve IHME data (HTTP 403, non-redistributable), so T is Ipsos's printed GBD 2017 actual (`ipsos_printed_gbd2017`; `ipsos_printed_healthyhk` for Hong Kong) and the GBD pull is a follow-up. Printed "0.0" rows get a blank t_value (`source_unrounded_pending`), never 0 or 0.5.
* 2026-11-22: p14 cardiovascular actuals for Saudi Arabia and Germany are swapped in the deck (Ipsos's own difference column and Destatis agree); t_value takes the implied figure with `t_flag = ipsos_printed_gbd2017_swap_corrected`, t_value_ipsos stays as printed.
* 2026-11-22: 2020 question wording kept verbatim as printed, including the missing "how" ("about many are a result of") and the "[COUNTRY]" placeholder; the typo is noted in items.yaml rather than corrected in the data.
* 2026-11-22: 2020 sample sizes recorded as the technical note states them; Argentina and Belgium (listed under both ~1000 and ~500) and the Philippines (listed under neither) get `n_country_approx = not_stated`. All 32 countries are named in the representative or urban/affluent list, so no Ireland/New Zealand-style decision was needed.
* 2026-11-22: the six countries only in the 2020 wave (China, Hong Kong, Philippines, Romania, Russia, Saudi Arabia) are appended to countries.csv from the cached World Bank dumps (which cover all economies) and a web-presence fetch run the same day; the 30 existing rows are unchanged. Their `ipsos_representative_sample` comes from the 2020 technical note.
* 2026-11-22: 2020 country names in pairs.csv are as printed in that deck (United Kingdom, Turkey, Hong Kong SAR China); countries.csv keeps the 2024 names for the shared countries.
* 2026-11-22: Ipsos Royaumont December 2023 wave admitted (published December 2023) with the same item_ids as 2024. T is reused from the 2024 rows (one vintage per item across waves); the wave is a replication of H one year earlier, not an independent truth point. The deck does not describe its samples as representative: representative_sample = not_stated, age_range = not_stated, n approximately 1,000 (10,000 respondents, 10 countries).
* 2026-11-22: Royaumont homicide item stored in pairs_categorical.csv from the "% higher" chart alone; the p6 footnote gives the actual direction (down everywhere except the United States, which is recorded as same_or_higher).
* 2026-11-22: Ipsos Earth Day 2022 warming item admitted (published April 2022) as a banded degrees-Celsius item in its own table, pairs_banded.csv, outside the log-odds analyses; midpoints 0.375 / 1.375 / 2.375 / 3.5 (reproduce the deck's printed all-country mean); T = 1.1 from IPCC AR6 WG1 SPM A.1.2 with the deck's 1 in t_value_ipsos. Switzerland and Norway added to countries.csv.
* 2026-11-22: skip list. ISSP 2019 occupational-earnings items are excluded (truth normalisation cost: earnings questions need country- and occupation-specific wage truths on a common scale). The Fabre, Douenne and Mattauch 2023 foreign-aid item is excluded (figure-only publication: the per-country estimates are printed only as a chart).

## Follow-ups

* UN DESA direct values (2024 revision), if later sourced, go in `data/validation/truth_crosscheck.csv` only; they do not replace T, which is the World Bank series.
* `wikidata_p17_count` completed for 3 of 38 countries (Argentina, Hungary, China) before the SPARQL time limit; `enwiki_mentions` is the covariate to use.
* ipsos_2020 T from a current GBD vintage: OWID's API and CSV downloads refuse IHME data (indicator IDs listed under Truth, 2020). Options are the IHME GBD Results Tool (login, non-commercial licence) or the WHO Global Health Estimates (open CSV, different cause taxonomy). Whichever is used, keep one vintage for all 32 countries, record it in t_flag as `owid_gbd_<year>` or equivalent, and fill the six `source_unrounded_pending` HIV/STI rows; Hong Kong is not a GBD location.
* ipsos_2020 terrorism, substance use and transport items: per-country figures may exist in Ipsos's data tables or at perils.ipsos.com (the deck's stated source page); if found, the printed rows in `transcription/ipsos_2020_defective_pages.csv` can be attributed and the items built.
* ipsos_earthday_2022: the bands plus don't-know fall short of 100 by up to 10 points in some countries; if Ipsos's data tables name the missing category (e.g. "not warmed at all" or "prefer not to say"), add it to the transcription and the note column.
* ipsos_royaumont_2023: `t_value_ipsos` carries the deck's printed actuals (e.g. IOM 2022 immigrant shares); they are not cross-checked against the 2024 printed figures beyond the validation table.
* ipsos_2020 question wording: `run.py` builds plain/official prompts from `PLAIN_QUESTIONS[item]`, which has no entries for the six new items, and the verbatim wording keeps the deck's "[COUNTRY]" placeholder and missing "how"; the prompt layer needs per-item questions before the 2020 wave is run.

## Validation results

Generated by `scripts/validate.py`.

<!-- validation:start -->
```
1. Range check: 309 rows (ipsos_2024: 90, ipsos_2020: 190, ipsos_royaumont_2023: 29).
   ipsos_2024: 0 outside [0,100].
   t_flag counts: {('immigrant_share', 'world_bank'): 30, ('muslim_share', 'pew_2020'): 30, ('wealth_top1', 'wid_2024'): 30}
   T zero or blank (logit undefined): none
   T below 1 percent (printed figure, T used): [('immigrant_share', 'Brazil', '1%', '0.7'), ('immigrant_share', 'India', '0%', '0.3'), ('immigrant_share', 'Indonesia', '0%', '0.2'), ('muslim_share', 'Argentina', '<1%', '0.9292'), ('muslim_share', 'Brazil', '<1%', '0.0177'), ('muslim_share', 'Chile', '<1%', '0.06699'), ('muslim_share', 'Colombia', '<1%', '0.00393'), ('muslim_share', 'Hungary', '<1%', '0.13922'), ('muslim_share', 'Japan', '<1%', '0.16997'), ('muslim_share', 'Mexico', '<1%', '0.00629'), ('muslim_share', 'Peru', '<1%', '0.02159'), ('muslim_share', 'Poland', '<1%', '0.00732'), ('muslim_share', 'South Korea', '<1%', '0.31')]
   ipsos_2020: 0 outside [0,100].
   t_flag counts: {('deaths_cancer', 'ipsos_printed_gbd2017'): 31, ('deaths_cancer', 'ipsos_printed_healthyhk'): 1, ('deaths_cardiovascular', 'ipsos_printed_gbd2017'): 29, ('deaths_cardiovascular', 'ipsos_printed_gbd2017_swap_corrected'): 2, ('deaths_cardiovascular', 'ipsos_printed_healthyhk'): 1, ('deaths_hiv_sti', 'ipsos_printed_gbd2017'): 25, ('deaths_hiv_sti', 'source_unrounded_pending'): 6, ('deaths_neurological', 'ipsos_printed_gbd2017'): 31, ('deaths_neurological', 'ipsos_printed_healthyhk'): 1, ('deaths_suicide', 'ipsos_printed_gbd2017'): 31, ('deaths_suicide', 'ipsos_printed_healthyhk'): 1, ('deaths_violence', 'ipsos_printed_gbd2017'): 30, ('deaths_violence', 'ipsos_printed_healthyhk'): 1}
   T zero or blank (logit undefined): [('deaths_hiv_sti', 'Hong Kong SAR China', '0.0'), ('deaths_hiv_sti', 'Hungary', '0.0'), ('deaths_hiv_sti', 'Japan', '0.0'), ('deaths_hiv_sti', 'Netherlands', '0.0'), ('deaths_hiv_sti', 'Poland', '0.0'), ('deaths_hiv_sti', 'Sweden', '0.0')]
   T below 1 percent (printed figure, T used): [('deaths_hiv_sti', 'Argentina', '0.6', '0.6'), ('deaths_hiv_sti', 'Australia', '0.1', '0.1'), ('deaths_hiv_sti', 'Belgium', '0.1', '0.1'), ('deaths_hiv_sti', 'Canada', '0.1', '0.1'), ('deaths_hiv_sti', 'Chile', '0.5', '0.5'), ('deaths_hiv_sti', 'China', '0.4', '0.4'), ('deaths_hiv_sti', 'France', '0.1', '0.1'), ('deaths_hiv_sti', 'Germany', '0.1', '0.1'), ('deaths_hiv_sti', 'India', '0.7', '0.7'), ('deaths_hiv_sti', 'Italy', '0.1', '0.1'), ('deaths_hiv_sti', 'Mexico', '0.9', '0.9'), ('deaths_hiv_sti', 'Philippines', '0.9', '0.9'), ('deaths_hiv_sti', 'Romania', '0.1', '0.1'), ('deaths_hiv_sti', 'Singapore', '0.2', '0.2'), ('deaths_hiv_sti', 'South Korea', '0.1', '0.1'), ('deaths_hiv_sti', 'Spain', '0.2', '0.2'), ('deaths_hiv_sti', 'Turkey', '0.1', '0.1'), ('deaths_hiv_sti', 'United Kingdom', '0.1', '0.1'), ('deaths_hiv_sti', 'United States', '0.3', '0.3'), ('deaths_suicide', 'Italy', '0.7', '0.7'), ('deaths_suicide', 'Peru', '0.7', '0.7'), ('deaths_suicide', 'Philippines', '0.8', '0.8'), ('deaths_suicide', 'Romania', '0.9', '0.9'), ('deaths_suicide', 'Spain', '0.9', '0.9'), ('deaths_suicide', 'Turkey', '0.7', '0.7'), ('deaths_violence', 'Argentina', '0.8', '0.8'), ('deaths_violence', 'Australia', '0.2', '0.2'), ('deaths_violence', 'Belgium', '0.1', '0.1'), ('deaths_violence', 'Canada', '0.2', '0.2'), ('deaths_violence', 'Chile', '0.7', '0.7'), ('deaths_violence', 'China', '0.1', '0.1'), ('deaths_violence', 'France', '0.1', '0.1'), ('deaths_violence', 'Germany', '0.1', '0.1'), ('deaths_violence', 'Hong Kong SAR China', '0.1', '0.1'), ('deaths_violence', 'Hungary', '0.1', '0.1'), ('deaths_violence', 'India', '0.4', '0.4'), ('deaths_violence', 'Italy', '0.1', '0.1'), ('deaths_violence', 'Japan', '0.1', '0.1'), ('deaths_violence', 'Malaysia', '0.4', '0.4'), ('deaths_violence', 'Netherlands', '0.1', '0.1'), ('deaths_violence', 'Peru', '0.8', '0.8'), ('deaths_violence', 'Poland', '0.2', '0.2'), ('deaths_violence', 'Romania', '0.2', '0.2'), ('deaths_violence', 'Singapore', '0.1', '0.1'), ('deaths_violence', 'South Korea', '0.2', '0.2'), ('deaths_violence', 'Spain', '0.1', '0.1'), ('deaths_violence', 'Sweden', '0.1', '0.1'), ('deaths_violence', 'Turkey', '0.4', '0.4'), ('deaths_violence', 'United Kingdom', '0.1', '0.1'), ('deaths_violence', 'United States', '0.7', '0.7')]
   ipsos_royaumont_2023: 0 outside [0,100].
   t_flag counts: {('immigrant_share', 'world_bank'): 10, ('muslim_share', 'pew_2020'): 9, ('wealth_top1', 'wid_2024'): 10}
   T zero or blank (logit undefined): none
   T below 1 percent (printed figure, T used): [('muslim_share', 'Argentina', '0,9%', '0.9292'), ('muslim_share', 'Japan', '0,2%', '0.16997'), ('muslim_share', 'Poland', '0,0%', '0.00732')]
2. Countries per item:
   ipsos_2024: {'immigrant_share': 30, 'muslim_share': 30, 'wealth_top1': 30}. Rows without usable T: none
   ipsos_2020: {'deaths_cancer': 32, 'deaths_cardiovascular': 32, 'deaths_hiv_sti': 31, 'deaths_neurological': 32, 'deaths_suicide': 32, 'deaths_violence': 31}. Rows without usable T: [('deaths_hiv_sti', 'Hong Kong SAR China', '0.0'), ('deaths_hiv_sti', 'Hungary', '0.0'), ('deaths_hiv_sti', 'Japan', '0.0'), ('deaths_hiv_sti', 'Netherlands', '0.0'), ('deaths_hiv_sti', 'Poland', '0.0'), ('deaths_hiv_sti', 'Sweden', '0.0')]
   ipsos_royaumont_2023: {'immigrant_share': 10, 'muslim_share': 9, 'wealth_top1': 10}. Rows without usable T: none
3. Question wording present verbatim in items.yaml for all 9 items: yes.
4. Ipsos printed figure (t_value_ipsos) vs T used (t_value), per item; rows where |printed - T| > 2 points are flagged:
   wave ipsos_2024
   wealth_top1 (T source: World Inequality Database, top 1% share of net personal wealth, 2024 (WID 2026 release via Our World in Data mirror))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 26% | 25.78 (2024) | +0.22 |
   | Australia | 24% | 23.67 (2024) | +0.33 |
   | Belgium | 15% | 15.53 (2024) | -0.53 |
   | Brazil | 49% | 39.46 (2024) | +9.54 **>2pp** |
   | Canada | 25% | 28.58 (2024) | -3.58 **>2pp** |
   | Chile | 50% | 39.56 (2024) | +10.44 **>2pp** |
   | Colombia | 33% | 39.23 (2024) | -6.23 **>2pp** |
   | Germany | 26% | 27.85 (2024) | -1.85 |
   | Spain | 23% | 24.15 (2024) | -1.15 |
   | France | 24% | 27.68 (2024) | -3.68 **>2pp** |
   | Great Britain | 21% | 21.30 (2024) | -0.30 |
   | Hungary | 33% | 33.36 (2024) | -0.36 |
   | Indonesia | 30% | 21.32 (2024) | +8.68 **>2pp** |
   | India | 33% | 40.14 (2024) | -7.14 **>2pp** |
   | Ireland | 23% | 23.33 (2024) | -0.33 |
   | Italy | 22% | 22.03 (2024) | -0.03 |
   | Japan | 25% | 24.62 (2024) | +0.38 |
   | South Korea | 26% | 26.10 (2024) | -0.10 |
   | Mexico | 48% | 39.80 (2024) | +8.20 **>2pp** |
   | Malaysia | 31% | 27.19 (2024) | +3.81 **>2pp** |
   | Netherlands | 13% | 13.98 (2024) | -0.98 |
   | New Zealand | 23% | 22.66 (2024) | +0.34 |
   | Peru | No data available | 38.55 (2024) | n/a |
   | Poland | 30% | 29.92 (2024) | +0.08 |
   | Singapore | 31% | 28.35 (2024) | +2.65 **>2pp** |
   | Sweden | 28% | 27.49 (2024) | +0.51 |
   | Thailand | 48% | 33.33 (2024) | +14.67 **>2pp** |
   | Türkiye | 37% | 31.74 (2024) | +5.26 **>2pp** |
   | United States | 35% | 34.78 (2024) | +0.22 |
   | South Africa | 55% | 54.91 (2024) | +0.09 |
   wealth_top1: countries where |printed - T| > 2 points: 12 ['Brazil', 'Canada', 'Chile', 'Colombia', 'France', 'Indonesia', 'India', 'Mexico', 'Malaysia', 'Singapore', 'Thailand', 'Türkiye']
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
   T is the World Bank WDI 2024 series (immigrant_share), Pew's 2020 estimate (muslim_share) and WID 2024 (wealth_top1), decisions 2026-11-22; differences reflect the older source vintages Ipsos used and Ipsos rounding to whole percents.
   wave ipsos_2020
   deaths_cancer (T source: IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 30.8 | 30.80 (2017) | +0.00 |
   | Australia | 26.8 | 26.80 (2017) | +0.00 |
   | Belgium | 28.3 | 28.30 (2017) | +0.00 |
   | Brazil | 18.2 | 18.20 (2017) | +0.00 |
   | Canada | 29.4 | 29.40 (2017) | +0.00 |
   | Chile | 22.3 | 22.30 (2017) | +0.00 |
   | China | 24.9 | 24.90 (2017) | +0.00 |
   | Colombia | 19.9 | 19.90 (2017) | +0.00 |
   | Germany | 26.7 | 26.70 (2017) | +0.00 |
   | Spain | 27.8 | 27.80 (2017) | +0.00 |
   | France | 30.9 | 30.90 (2017) | +0.00 |
   | United Kingdom | 29.6 | 29.60 (2017) | +0.00 |
   | Hong Kong SAR China | 31.5 | 31.50 () | +0.00 |
   | Hungary | 26.3 | 26.30 (2017) | +0.00 |
   | India | 9.4 | 9.40 (2017) | +0.00 |
   | Italy | 29.0 | 29.00 (2017) | +0.00 |
   | Japan | 30.2 | 30.20 (2017) | +0.00 |
   | South Korea | 34.1 | 34.10 (2017) | +0.00 |
   | Mexico | 13.7 | 13.70 (2017) | +0.00 |
   | Malaysia | 16.4 | 16.40 (2017) | +0.00 |
   | Netherlands | 30.9 | 30.90 (2017) | +0.00 |
   | Peru | 20.1 | 20.10 (2017) | +0.00 |
   | Philippines | 11.9 | 11.90 (2017) | +0.00 |
   | Poland | 27.7 | 27.70 (2017) | +0.00 |
   | Romania | 19.6 | 19.60 (2017) | +0.00 |
   | Russia | 15.9 | 15.90 (2017) | +0.00 |
   | Saudi Arabia | 12.5 | 12.50 (2017) | +0.00 |
   | Singapore | 27.5 | 27.50 (2017) | +0.00 |
   | Sweden | 26.2 | 26.20 (2017) | +0.00 |
   | Turkey | 23.1 | 23.10 (2017) | +0.00 |
   | United States | 24.5 | 24.50 (2017) | +0.00 |
   | South Africa | 10.2 | 10.20 (2017) | +0.00 |
   deaths_cancer: countries where |printed - T| > 2 points: 0 
   deaths_cardiovascular (T source: IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 31.8 | 31.80 (2017) | +0.00 |
   | Australia | 30.5 | 30.50 (2017) | +0.00 |
   | Belgium | 29.6 | 29.60 (2017) | +0.00 |
   | Brazil | 28.8 | 28.80 (2017) | +0.00 |
   | Canada | 28.9 | 28.90 (2017) | +0.00 |
   | Chile | 26.6 | 26.60 (2017) | +0.00 |
   | China | 41.9 | 41.90 (2017) | +0.00 |
   | Colombia | 29.0 | 29.00 (2017) | +0.00 |
   | Germany | 33.4 | 37.60 (2017) | -4.20 **>2pp** |
   | Spain | 29.7 | 29.70 (2017) | +0.00 |
   | France | 26.9 | 26.90 (2017) | +0.00 |
   | United Kingdom | 29.0 | 29.00 (2017) | +0.00 |
   | Hong Kong SAR China | 20.6 | 20.60 () | +0.00 |
   | Hungary | 46.9 | 46.90 (2017) | +0.00 |
   | India | 26.6 | 26.60 (2017) | +0.00 |
   | Italy | 34.8 | 34.80 (2017) | +0.00 |
   | Japan | 26.8 | 26.80 (2017) | +0.00 |
   | South Korea | 22.3 | 22.30 (2017) | +0.00 |
   | Mexico | 22.7 | 22.70 (2017) | +0.00 |
   | Malaysia | 34.7 | 34.70 (2017) | +0.00 |
   | Netherlands | 26.7 | 26.70 (2017) | +0.00 |
   | Peru | 19.6 | 19.60 (2017) | +0.00 |
   | Philippines | 32.6 | 32.60 (2017) | +0.00 |
   | Poland | 42.8 | 42.80 (2017) | +0.00 |
   | Romania | 55.5 | 55.50 (2017) | +0.00 |
   | Russia | 54.5 | 54.50 (2017) | +0.00 |
   | Saudi Arabia | 37.6 | 33.40 (2017) | +4.20 **>2pp** |
   | Singapore | 31.1 | 31.10 (2017) | +0.00 |
   | Sweden | 37.2 | 37.20 (2017) | +0.00 |
   | Turkey | 36.4 | 36.40 (2017) | +0.00 |
   | United States | 31.6 | 31.60 (2017) | +0.00 |
   | South Africa | 16.1 | 16.10 (2017) | +0.00 |
   deaths_cardiovascular: countries where |printed - T| > 2 points: 2 ['Germany', 'Saudi Arabia']
   deaths_hiv_sti (T source: IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 0.6 | 0.60 (2017) | +0.00 |
   | Australia | 0.1 | 0.10 (2017) | +0.00 |
   | Belgium | 0.1 | 0.10 (2017) | +0.00 |
   | Brazil | 1.3 | 1.30 (2017) | +0.00 |
   | Canada | 0.1 | 0.10 (2017) | +0.00 |
   | Chile | 0.5 | 0.50 (2017) | +0.00 |
   | China | 0.4 | 0.40 (2017) | +0.00 |
   | Colombia | 1.2 | 1.20 (2017) | +0.00 |
   | Germany | 0.1 | 0.10 (2017) | +0.00 |
   | Spain | 0.2 | 0.20 (2017) | +0.00 |
   | France | 0.1 | 0.10 (2017) | +0.00 |
   | United Kingdom | 0.1 | 0.10 (2017) | +0.00 |
   | Hong Kong SAR China | 0.0 | missing () | n/a |
   | Hungary | 0.0 | missing () | n/a |
   | India | 0.7 | 0.70 (2017) | +0.00 |
   | Italy | 0.1 | 0.10 (2017) | +0.00 |
   | Japan | 0.0 | missing () | n/a |
   | South Korea | 0.1 | 0.10 (2017) | +0.00 |
   | Mexico | 0.9 | 0.90 (2017) | +0.00 |
   | Malaysia | 1.0 | 1.00 (2017) | +0.00 |
   | Netherlands | 0.0 | missing () | n/a |
   | Peru | 1.9 | 1.90 (2017) | +0.00 |
   | Philippines | 0.9 | 0.90 (2017) | +0.00 |
   | Poland | 0.0 | missing () | n/a |
   | Romania | 0.1 | 0.10 (2017) | +0.00 |
   | Russia | 1.1 | 1.10 (2017) | +0.00 |
   | Singapore | 0.2 | 0.20 (2017) | +0.00 |
   | Sweden | 0.0 | missing () | n/a |
   | Turkey | 0.1 | 0.10 (2017) | +0.00 |
   | United States | 0.3 | 0.30 (2017) | +0.00 |
   | South Africa | 28.8 | 28.80 (2017) | +0.00 |
   deaths_hiv_sti: countries where |printed - T| > 2 points: 0 
   deaths_neurological (T source: IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 6.8 | 6.80 (2017) | +0.00 |
   | Australia | 12.4 | 12.40 (2017) | +0.00 |
   | Belgium | 11.7 | 11.70 (2017) | +0.00 |
   | Brazil | 6.8 | 6.80 (2017) | +0.00 |
   | Canada | 11.4 | 11.40 (2017) | +0.00 |
   | Chile | 9.2 | 9.20 (2017) | +0.00 |
   | China | 5.6 | 5.60 (2017) | +0.00 |
   | Colombia | 7.7 | 7.70 (2017) | +0.00 |
   | Germany | 11.0 | 11.00 (2017) | +0.00 |
   | Spain | 14.5 | 14.50 (2017) | +0.00 |
   | France | 14.5 | 14.50 (2017) | +0.00 |
   | United Kingdom | 12.7 | 12.70 (2017) | +0.00 |
   | Hong Kong SAR China | 3.8 | 3.80 () | +0.00 |
   | Hungary | 6.8 | 6.80 (2017) | +0.00 |
   | India | 2.7 | 2.70 (2017) | +0.00 |
   | Italy | 13.7 | 13.70 (2017) | +0.00 |
   | Japan | 16.0 | 16.00 (2017) | +0.00 |
   | South Korea | 12.2 | 12.20 (2017) | +0.00 |
   | Mexico | 5.8 | 5.80 (2017) | +0.00 |
   | Malaysia | 4.4 | 4.40 (2017) | +0.00 |
   | Netherlands | 12.0 | 12.00 (2017) | +0.00 |
   | Peru | 8.4 | 8.40 (2017) | +0.00 |
   | Philippines | 2.9 | 2.90 (2017) | +0.00 |
   | Poland | 8.7 | 8.70 (2017) | +0.00 |
   | Romania | 6.6 | 6.60 (2017) | +0.00 |
   | Russia | 5.3 | 5.30 (2017) | +0.00 |
   | Saudi Arabia | 4.7 | 4.70 (2017) | +0.00 |
   | Singapore | 9.4 | 9.40 (2017) | +0.00 |
   | Sweden | 12.7 | 12.70 (2017) | +0.00 |
   | Turkey | 7.8 | 7.80 (2017) | +0.00 |
   | United States | 10.8 | 10.80 (2017) | +0.00 |
   | South Africa | 3.0 | 3.00 (2017) | +0.00 |
   deaths_neurological: countries where |printed - T| > 2 points: 0 
   deaths_suicide (T source: IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 1.5 | 1.50 (2017) | +0.00 |
   | Australia | 1.8 | 1.80 (2017) | +0.00 |
   | Belgium | 2.0 | 2.00 (2017) | +0.00 |
   | Brazil | 1.1 | 1.10 (2017) | +0.00 |
   | Canada | 1.7 | 1.70 (2017) | +0.00 |
   | Chile | 1.8 | 1.80 (2017) | +0.00 |
   | China | 1.2 | 1.20 (2017) | +0.00 |
   | Colombia | 1.2 | 1.20 (2017) | +0.00 |
   | Germany | 1.3 | 1.30 (2017) | +0.00 |
   | Spain | 0.9 | 0.90 (2017) | +0.00 |
   | France | 1.9 | 1.90 (2017) | +0.00 |
   | United Kingdom | 1.0 | 1.00 (2017) | +0.00 |
   | Hong Kong SAR China | 1.8 | 1.80 () | +0.00 |
   | Hungary | 1.7 | 1.70 (2017) | +0.00 |
   | India | 2.1 | 2.10 (2017) | +0.00 |
   | Italy | 0.7 | 0.70 (2017) | +0.00 |
   | Japan | 2.1 | 2.10 (2017) | +0.00 |
   | South Korea | 5.1 | 5.10 (2017) | +0.00 |
   | Mexico | 1.1 | 1.10 (2017) | +0.00 |
   | Malaysia | 1.4 | 1.40 (2017) | +0.00 |
   | Netherlands | 1.4 | 1.40 (2017) | +0.00 |
   | Peru | 0.7 | 0.70 (2017) | +0.00 |
   | Philippines | 0.8 | 0.80 (2017) | +0.00 |
   | Poland | 1.7 | 1.70 (2017) | +0.00 |
   | Romania | 0.9 | 0.90 (2017) | +0.00 |
   | Russia | 2.4 | 2.40 (2017) | +0.00 |
   | Saudi Arabia | 1.1 | 1.10 (2017) | +0.00 |
   | Singapore | 2.5 | 2.50 (2017) | +0.00 |
   | Sweden | 1.5 | 1.50 (2017) | +0.00 |
   | Turkey | 0.7 | 0.70 (2017) | +0.00 |
   | United States | 1.7 | 1.70 (2017) | +0.00 |
   | South Africa | 1.3 | 1.30 (2017) | +0.00 |
   deaths_suicide: countries where |printed - T| > 2 points: 0 
   deaths_violence (T source: IHME Global Burden of Disease Study 2017, share of all deaths by cause, as printed by Ipsos (technical note p53; Hong Kong from healthyhk.gov.hk))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 0.8 | 0.80 (2017) | +0.00 |
   | Australia | 0.2 | 0.20 (2017) | +0.00 |
   | Belgium | 0.1 | 0.10 (2017) | +0.00 |
   | Brazil | 4.7 | 4.70 (2017) | +0.00 |
   | Canada | 0.2 | 0.20 (2017) | +0.00 |
   | Chile | 0.7 | 0.70 (2017) | +0.00 |
   | China | 0.1 | 0.10 (2017) | +0.00 |
   | Colombia | 6.4 | 6.40 (2017) | +0.00 |
   | Germany | 0.1 | 0.10 (2017) | +0.00 |
   | Spain | 0.1 | 0.10 (2017) | +0.00 |
   | France | 0.1 | 0.10 (2017) | +0.00 |
   | United Kingdom | 0.1 | 0.10 (2017) | +0.00 |
   | Hong Kong SAR China | 0.1 | 0.10 () | +0.00 |
   | Hungary | 0.1 | 0.10 (2017) | +0.00 |
   | India | 0.4 | 0.40 (2017) | +0.00 |
   | Italy | 0.1 | 0.10 (2017) | +0.00 |
   | Japan | 0.1 | 0.10 (2017) | +0.00 |
   | South Korea | 0.2 | 0.20 (2017) | +0.00 |
   | Mexico | 6.1 | 6.10 (2017) | +0.00 |
   | Malaysia | 0.4 | 0.40 (2017) | +0.00 |
   | Netherlands | 0.1 | 0.10 (2017) | +0.00 |
   | Peru | 0.8 | 0.80 (2017) | +0.00 |
   | Philippines | 2.4 | 2.40 (2017) | +0.00 |
   | Poland | 0.2 | 0.20 (2017) | +0.00 |
   | Romania | 0.2 | 0.20 (2017) | +0.00 |
   | Russia | 1.2 | 1.20 (2017) | +0.00 |
   | Singapore | 0.1 | 0.10 (2017) | +0.00 |
   | Sweden | 0.1 | 0.10 (2017) | +0.00 |
   | Turkey | 0.4 | 0.40 (2017) | +0.00 |
   | United States | 0.7 | 0.70 (2017) | +0.00 |
   | South Africa | 3.3 | 3.30 (2017) | +0.00 |
   deaths_violence: countries where |printed - T| > 2 points: 0 
   T is the printed GBD 2017 figure itself (fallback after the Our World in Data pull was refused, decision 2026-11-22), so printed and used differ only where the printed actual is swapped between two adjacent rows (cardiovascular, Saudi Arabia and Germany) or is a rounded 0.0 left blank.
   wave ipsos_royaumont_2023
   wealth_top1 (T source: World Inequality Database, top 1% share of net personal wealth, 2024 (WID 2026 release via Our World in Data mirror))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 13% | 25.78 (2024) | -12.78 **>2pp** |
   | Australia | 10% | 23.67 (2024) | -13.67 **>2pp** |
   | Germany | 10% | 27.85 (2024) | -17.85 **>2pp** |
   | France | 13% | 27.68 (2024) | -14.68 **>2pp** |
   | United Kingdom | 10% | 21.30 (2024) | -11.30 **>2pp** |
   | Italy | 14% | 22.03 (2024) | -8.03 **>2pp** |
   | Japan | 13% | 24.62 (2024) | -11.62 **>2pp** |
   | Poland | 10% | 29.92 (2024) | -19.92 **>2pp** |
   | Turkey | 19% | 31.74 (2024) | -12.74 **>2pp** |
   | United States | 21% | 34.78 (2024) | -13.78 **>2pp** |
   wealth_top1: countries where |printed - T| > 2 points: 10 ['Argentina', 'Australia', 'Germany', 'France', 'United Kingdom', 'Italy', 'Japan', 'Poland', 'Turkey', 'United States']
   immigrant_share (T source: World Bank WDI SM.POP.TOTL.ZS (UN DESA International Migrant Stock))
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 5% | 4.30 (2024) | +0.70 |
   | Australia | 30% | 30.40 (2024) | -0.40 |
   | Germany | 19% | 19.80 (2024) | -0.80 |
   | France | 13% | 13.80 (2024) | -0.80 |
   | United Kingdom | 14% | 17.10 (2024) | -3.10 **>2pp** |
   | Italy | 11% | 11.00 (2024) | +0.00 |
   | Japan | 2% | 2.80 (2024) | -0.80 |
   | Poland | 2% | 4.50 (2024) | -2.50 **>2pp** |
   | Turkey | 7% | 8.10 (2024) | -1.10 |
   | United States | 15% | 15.20 (2024) | -0.20 |
   immigrant_share: countries where |printed - T| > 2 points: 2 ['United Kingdom', 'Poland']
   muslim_share (T source: Pew Research Center, Religious Composition of the World's Population 2010-2020 (June 2025), 2020 estimate)
   | country | Ipsos printed | T used (year) | printed - T |
   |---|---|---|---|
   | Argentina | 0,9% | 0.93 (2020) | -0.03 |
   | Australia | 3,2% | 3.50 (2020) | -0.30 |
   | Germany | 5,5% | 6.55 (2020) | -1.05 |
   | France | 8,5% | 9.10 (2020) | -0.60 |
   | United Kingdom | 3,2% | 6.37 (2020) | -3.17 **>2pp** |
   | Italy | 4,8% | 4.42 (2020) | +0.38 |
   | Japan | 0,2% | 0.17 (2020) | +0.03 |
   | Poland | 0,0% | 0.01 (2020) | -0.01 |
   | United States | 1,0% | 1.19 (2020) | -0.19 |
   muslim_share: countries where |printed - T| > 2 points: 1 ['United Kingdom']
   T is copied from the ipsos_2024 row of the same country (one vintage per item across waves, decision 2026-11-22); the deck's printed actual (WID, IOM World Migration Report 2022, World Population Review) is kept in t_value_ipsos only.
5. definition_match per item: {('immigrant_share', 'yes'): 38, ('immigrant_share', 'approximate'): 2, ('muslim_share', 'yes'): 39, ('wealth_top1', 'approximate'): 40, ('deaths_cancer', 'yes'): 31, ('deaths_cancer', 'approximate'): 1, ('deaths_cardiovascular', 'yes'): 31, ('deaths_cardiovascular', 'approximate'): 1, ('deaths_hiv_sti', 'yes'): 30, ('deaths_hiv_sti', 'approximate'): 1, ('deaths_neurological', 'yes'): 31, ('deaths_neurological', 'approximate'): 1, ('deaths_suicide', 'yes'): 31, ('deaths_suicide', 'approximate'): 1, ('deaths_violence', 'yes'): 30, ('deaths_violence', 'approximate'): 1}. 'approximate' = wealth_top1 (households in question, adults in WID), immigrant_share India/Indonesia (citizenship-based stock), and every Hong Kong row of ipsos_2020 (actual from healthyhk.gov.hk, not GBD).
6. Sum of Ipsos 'approximately' per-country samples (one item per wave; Ipsos rounds per-country n):
   ipsos_2024 (immigrant_share, 30 countries): 22000 from 30 stated n (0 not_stated) vs 22,989 interviews stated on p38.
   ipsos_2020 (deaths_cancer, 32 countries): 21000 from 29 stated n (3 not_stated) vs 16,000 interviews stated on p53.
   ipsos_royaumont_2023 (wealth_top1, 10 countries): 10000 from 10 stated n (0 not_stated) vs 10,000 interviews stated on p1.
7. countries.csv: 38 rows; web_presence missing for: none; income groups: {'Upper middle income': 12, 'High income': 25, 'Lower middle income': 1}; pairs.csv countries without a countries.csv row: none.
8. pairs_categorical.csv: 40 rows; per wave: {'ipsos_2024': 30, 'ipsos_royaumont_2023': 10}; rows with a determinable public majority: 38; actual_direction counts: {'same_or_lower': 6, 'lower': 29, 'higher': 1, 'same': 3, 'same_or_higher': 1}.
9. ipsos_royaumont_2023 T identical to the ipsos_2024 T of the same country for all 29 rows: yes.
10. pairs_banded.csv: 31 rows (31 countries); waves {'ipsos_earthday_2022': 31}; bands + don't-know sum: min 90, max 101; rows outside [95, 103]: {'India': 92, 'Peru': 90, 'Russia': 93, 'Turkey': 93} (the deck prints no further category); don't-know blank for: ['Norway']; h_mean_midpoint range 1.42 to 2.44; all-country column recomputed with the same midpoints = 2.11 vs 2.1 printed on p20; T = {'1.1'} ({'ipcc_ar6_wg1_spm'}), printed {'1'}; countries without a countries.csv row: none.
```
<!-- validation:end -->
