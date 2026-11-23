"""Build the categorical fact-question track (data/categorical/) from three machine-readable
sources published 2020 onward (inclusion rule, decision 2026-11-22; chart-only sources skipped):

  A. Eurobarometer true/false knowledge items, read from the Commission's "Volume A" result
     workbooks on data.europa.eu (one sheet per statement, weighted % of all respondents, n per country):
       Special EB 516 (EB 95.2, 13 Apr - 10 May 2021)   QA20.1-11 science statements, EU27 + 11 others
       Special EB 522 (EB 97.1, 21 Feb - 21 Mar 2022)   QC5.1-4 antibiotics statements, EU27
       Standard EB 104.1 (9 Oct - 5 Nov 2025)           SD20a.1-3 EU statements, EU27 + 10 others
  B. Dechezleprêtre, Fabre, Kruse, Planterose, Sánchez Chico and Stantcheva, "Fighting Climate Change:
     International Attitudes Toward Climate Policies", NBER WP 30265 (July 2024 version): Figure 6 (PDF
     page 16) prints the share of correct answers for 14 knowledge indicators x 20 countries (control
     group); the country-by-country supplement (socialeconomicslab.org, June 2024) prints the full answer
     distribution for 5 of the 14 indicators; wording from online appendix F, truth from appendix K.3.
  C. Gapminder, Refugee Misconception Study 2023 (report PDF, June 2023): 9 three-option fact questions
     x 7 countries, answer distributions on PDF pages 9-17.

Two stages:
  extract  needs the raw downloads in data/raw/categorical/ (gitignored; URLs and sha256 in
           data/categorical/sources_categorical.csv), openpyxl and pdftotext. Reads the workbooks and the
           PDF text layers and writes the committed transcription CSVs in data/categorical/transcription/.
           PDF sources are extracted twice, with `pdftotext -layout` (pass 1) and `pdftotext -raw` (pass 2,
           content-stream order); both passes are written and compared. For Gapminder the second pass is a
           hand transcription from rendered page images (gapminder_pass2_visual.csv, never rewritten here).
  build    needs no raw files. Reads the transcription CSVs and writes
           data/categorical/pairs_categorical_v1.csv, items_categorical.yaml and countries_extra.csv
           (World Bank covariates for countries not in data/countries.csv, from the API dumps in
           data/raw/categorical/worldbank/ when present).

Run:  python3 -I scripts/build_categorical.py                 # extract (if raw files exist) then build
      python3 -I scripts/build_categorical.py extract         # only re-extract the transcription CSVs
      python3 -I scripts/build_categorical.py build           # only rebuild the outputs
      python3 -I scripts/build_categorical.py fetch-web-presence   # network: enwiki mention counts for the
                                                              # extra countries -> data/raw/categorical/web_presence_extra.json
"""
import csv, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
C = os.path.join(D, "categorical")
T = os.path.join(C, "transcription")
RAW = os.path.join(D, "raw", "categorical")

PAIRS_COLS = ["source_id", "wave", "country_iso3", "country_name", "item_id", "question_wording", "options",
              "pct_per_option", "pct_dk", "pct_correct", "public_majority_option", "truth_option", "truth_source",
              "truth_note", "fieldwork_start", "fieldwork_end", "n_country", "source_file", "source_page_or_sheet"]

# ----------------------------------------------------------------------------------------------------------
# A. Eurobarometer
# ----------------------------------------------------------------------------------------------------------
# Eurobarometer country codes -> (ISO3, name). Aggregates and sub-samples are skipped (logged):
# 'EU27', 'D-W'/'DEW' (West Germany), 'D-E'/'DEE' (East Germany), 'CY_TCC' (Turkish Cypriot Community, no ISO3).
EB_CODES = {
    "BE": ("BEL", "Belgium"), "BG": ("BGR", "Bulgaria"), "CZ": ("CZE", "Czechia"), "DK": ("DNK", "Denmark"),
    "DE": ("DEU", "Germany"), "EE": ("EST", "Estonia"), "IE": ("IRL", "Ireland"), "EL": ("GRC", "Greece"),
    "ES": ("ESP", "Spain"), "FR": ("FRA", "France"), "HR": ("HRV", "Croatia"), "IT": ("ITA", "Italy"),
    "CY": ("CYP", "Cyprus"), "LV": ("LVA", "Latvia"), "LT": ("LTU", "Lithuania"), "LU": ("LUX", "Luxembourg"),
    "HU": ("HUN", "Hungary"), "MT": ("MLT", "Malta"), "NL": ("NLD", "Netherlands"), "AT": ("AUT", "Austria"),
    "PL": ("POL", "Poland"), "PT": ("PRT", "Portugal"), "RO": ("ROU", "Romania"), "SI": ("SVN", "Slovenia"),
    "SK": ("SVK", "Slovakia"), "FI": ("FIN", "Finland"), "SE": ("SWE", "Sweden"),
    "UK": ("GBR", "United Kingdom"), "TR": ("TUR", "Türkiye"), "MK": ("MKD", "North Macedonia"),
    "ME": ("MNE", "Montenegro"), "RS": ("SRB", "Serbia"), "AL": ("ALB", "Albania"), "CH": ("CHE", "Switzerland"),
    "NO": ("NOR", "Norway"), "BA": ("BIH", "Bosnia and Herzegovina"), "IS": ("ISL", "Iceland"),
    "XV": ("XKX", "Kosovo"), "XK": ("XKX", "Kosovo"), "MD": ("MDA", "Moldova"), "GE": ("GEO", "Georgia"),
}
EB_SKIP = {"UE27\nEU27", "EU27", "D-W", "D-E", "DEW", "DEE", "CY_TCC"}

EB_SOURCES = {
    "eb516_volume_a": dict(wave="eb95.2_2021", workbook="ebs_516_Volume_A_V3.xlsx",
                           fieldwork=("2021-04-13", "2021-05-10"), summary_sheets=[]),
    "eb522_volume_a": dict(wave="eb97.1_2022", workbook="ebs522_vol_A.xlsx",
                           fieldwork=("2022-02-21", "2022-03-21"), summary_sheets=["QC5_5"]),
    "eb104_volume_a": dict(wave="eb104.1_2025", workbook="Standard_Eurobarometer_104_Autumn_2025_volume_A.xlsx",
                           fieldwork=("2025-10-09", "2025-11-05"), summary_sheets=["SD20aR1"]),
}

WHO_AMR = "WHO fact sheet 'Antimicrobial resistance' (antibiotics act on bacteria, not viruses)"
# One entry per statement sheet. truth_option is 'True'/'False' as the respondent would answer, or '' when no
# truth is assigned. Wording is read verbatim from the workbook (sheet row 3 = stem, row 4 = statement).
EB_ITEMS = [
    # Special EB 516, QA20.1-11. The brief numbered 'equally scientific' as QA20.9; in the workbook it is QA20.7
    # (QA20.9 is the climate statement), so the flag is applied by content (decision 2026-11-22).
    dict(source_id="eb516_volume_a", sheet="QA20_1", item_id="eb516_q01_humans_dinosaurs", truth="False",
         truth_source="Non-avian dinosaurs went extinct about 66 million years ago (Renne et al. 2013, Science 339:684); the genus Homo appears about 2.8 million years ago (Villmoare et al. 2015, Science 347:1352)",
         note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_2", item_id="eb516_q02_continents_move", truth="True",
         truth_source="Plate tectonics (USGS, 'This Dynamic Earth')", note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_3", item_id="eb516_q03_antibiotics_kill_viruses", truth="False",
         truth_source=WHO_AMR, note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_4", item_id="eb516_q04_oxygen_from_plants", truth="True",
         truth_source="Photosynthesis by plants, algae and cyanobacteria; the Commission's EB 516 report scores the statement True",
         note="loose wording: roughly half of the oxygen produced each year comes from marine phytoplankton rather than land plants; kept, scored as the source scores it", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_5", item_id="eb516_q05_lasers_sound_waves", truth="False",
         truth_source="Lasers amplify light by stimulated emission (Maiman 1960, Nature 187:493)", note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_6", item_id="eb516_q06_population_over_10bn", truth="False",
         truth_source="UN DESA World Population Prospects 2022: 7.9 billion people in 2021", note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_7", item_id="eb516_q07_methods_equally_scientific", truth="",
         truth_source="", note="contestable (philosophy of science); no truth assigned; excluded from the main set and kept in the file with include_in_main = false",
         main=False),
    dict(source_id="eb516_volume_a", sheet="QA20_8", item_id="eb516_q08_humans_evolved", truth="True",
         truth_source="National Academies of Sciences (2008), Science, Evolution, and Creationism", note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_9", item_id="eb516_q09_climate_natural_cycles", truth="False",
         truth_source="IPCC AR6 WG1 Summary for Policymakers (2021) A.1: human influence has unequivocally warmed the atmosphere, ocean and land",
         note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_10", item_id="eb516_q10_cancer_cure_hidden", truth="False",
         truth_source="No evidence for the claim; conspiracy statement scored False in the Commission's EB 516 report", note="", main=True),
    dict(source_id="eb516_volume_a", sheet="QA20_11", item_id="eb516_q11_viruses_made_in_labs", truth="False",
         truth_source="No evidence for the claim; conspiracy statement scored False in the Commission's EB 516 report", note="", main=True),
    # Special EB 522, QC5.1-4. The workbook's QC5_5 sheet ('Average of correct answers') reproduces this scoring
    # (validate_categorical.py check 6).
    dict(source_id="eb522_volume_a", sheet="QC5_1", item_id="eb522_q1_antibiotics_kill_viruses", truth="False",
         truth_source=WHO_AMR, note="", main=True),
    dict(source_id="eb522_volume_a", sheet="QC5_2", item_id="eb522_q2_antibiotics_colds", truth="False",
         truth_source="WHO fact sheet 'Antimicrobial resistance'; colds are viral", note="", main=True),
    dict(source_id="eb522_volume_a", sheet="QC5_3", item_id="eb522_q3_unnecessary_use_ineffective", truth="True",
         truth_source="WHO fact sheet 'Antimicrobial resistance': misuse and overuse drive resistance", note="", main=True),
    dict(source_id="eb522_volume_a", sheet="QC5_4", item_id="eb522_q4_side_effects", truth="True",
         truth_source="ECDC patient information on antibiotics (side effects such as diarrhoea); scored True in the Commission's EB 522 report",
         note="", main=True),
    # Standard EB 104.1, SD20a.1-3; truth as of fieldwork (Oct-Nov 2025). SD20aR1 ('Average of correct answers')
    # reproduces this scoring (validate_categorical.py check 6).
    dict(source_id="eb104_volume_a", sheet="SD20a_1", item_id="eb104_sd20a1_euro_area_20_members", truth="True",
         truth_source="ECB / European Commission: 20 euro-area members at fieldwork (Croatia joined 1 Jan 2023; Bulgaria joins 1 Jan 2026)",
         note="the statement's count is updated by the Commission each wave; 20 is correct for fieldwork 9 Oct - 5 Nov 2025", main=True),
    dict(source_id="eb104_volume_a", sheet="SD20a_2", item_id="eb104_sd20a2_meps_directly_elected", truth="True",
         truth_source="Treaty on European Union, Art. 14(3): MEPs elected by direct universal suffrage (since 1979)", note="", main=True),
    dict(source_id="eb104_volume_a", sheet="SD20a_3", item_id="eb104_sd20a3_switzerland_member", truth="False",
         truth_source="Switzerland is not an EU member (European Union, list of member countries)", note="", main=True),
]

# ----------------------------------------------------------------------------------------------------------
# B. Climate (Dechezleprêtre et al.)
# ----------------------------------------------------------------------------------------------------------
CLIM_SOURCE_ID = "climate_attitudes_nber30265"
CLIM_WAVE = "climate_2021_22"
CLIM_FIELDWORK = ("2021-03", "2022-03")   # "between March 2021 and March 2022" (NBER WP p.9); per-country launch dates differ
FIG6_PAGE = 16
# Column order of Figure 6 (verified against the rendered page and, for rows 1-2 and 12-14, against the
# country-by-country supplement; see validate_categorical.py check 7).
FIG6_COLS = ["HIGH_INCOME_AVG", "AUS", "CAN", "DNK", "FRA", "DEU", "ITA", "JPN", "POL", "KOR", "ESP", "GBR", "USA",
             "MIDDLE_INCOME_AVG", "BRA", "CHN", "IND", "IDN", "MEX", "ZAF", "TUR", "UKR"]
CLIM_COUNTRIES = {"AUS": "Australia", "CAN": "Canada", "DNK": "Denmark", "FRA": "France", "DEU": "Germany",
                  "ITA": "Italy", "JPN": "Japan", "POL": "Poland", "KOR": "South Korea", "ESP": "Spain",
                  "GBR": "United Kingdom", "USA": "United States", "BRA": "Brazil", "CHN": "China", "IND": "India",
                  "IDN": "Indonesia", "MEX": "Mexico", "ZAF": "South Africa", "TUR": "Turkey", "UKR": "Ukraine"}
# Supplement page headers name countries as below (Turkey, not Türkiye).
CLIM_SUPP_NAMES = {v: k for k, v in CLIM_COUNTRIES.items()}

Q49 = ("Greenhouse gases are gases that trap heat in the atmosphere and make the Earth warmer, causing climate change. "
       "In particular, the burning of fossil fuels and agricultural production emit greenhouse gases. Which of the "
       "following elements contribute to climate change? (Multiple answers are possible) — CO2; Hydrogen; Methane; Particulate matter")
Q56 = ("If nothing is done to limit climate change, how likely do you think it is that climate change will lead to the "
       "following events? — Severe droughts and heatwaves; More frequent volcanic eruptions; Rising sea levels; Lower agricultural "
       "production; Drop in standards of living; Larger migration flows; More armed conflicts; Extinction of humankind — "
       "Very unlikely; Somewhat unlikely; Somewhat likely; Very likely")
RANK_INTRO = ("For the next three questions we would like you to rank the items according to the greenhouse gas emissions they "
              "emit, to the best of your knowledge (where 1 is the item that emits the most and 3 the item that emits the least). ")
IPCC21 = "IPCC AR6 WG1 (2021)"
# One entry per Figure 6 row, in the figure's row order. 'dist' names the supplement panel that gives the full
# distribution (None = only the share of correct answers is printed; the row is stored as a binary indicator).
CLIM_ITEMS = [
    dict(item_id="clim_cc_real_anthropogenic", fig6="CC exists, is anthropogenic", q="Q45/Q46", dist="A",
         wording="In your opinion, is climate change real? — Yes; No. (If Yes) What part of climate change do you think is due to human activity? — None; A little; Some; A lot; Most",
         options=["None", "A little", "Some", "A lot", "Most"], truth=["A lot", "Most"],
         truth_source=f"{IPCC21}, Figure SPM.1 (appendix K.3: 'Most (if not all)')",
         note="Figure 6 counts 'A lot' or 'Most' as correct (the supplement's 'A lot' + 'Most' shares reproduce the Figure 6 value in all 20 countries, within rounding); appendix K.3 lists the correct answer as 'Most (if not all)'. Respondents answering 'No' to Q45 are in 'None' (Q46 is asked only if Q45 = Yes)."),
    dict(item_id="clim_halving_insufficient", fig6="Cutting emissions by half insufficient to stop global warming", q="Q50", dist="B",
         wording="Do you think that cutting global greenhouse gas emissions by half would be sufficient to eventually stop temperatures from rising? — Yes; No",
         options=["Yes", "No"], truth=["No"], truth_source=f"{IPCC21}, D.1 (net zero CO2 emissions is required)", note=""),
    dict(item_id="clim_rank_food_beef_highest", fig6="GHG footprint of beef/meat is higher than chicken or pasta", q="Q52", dist=None,
         wording=RANK_INTRO + "Which dish emits the most greenhouse gases? We consider that each dish weighs half a pound. Please rank the items from 1 (most) to 3 (least) (by clicking and dragging the items). — A [beef] steak; One serving of [pasta]; Chicken wings",
         options=["Beef/meat ranked 1 (most)", "Beef/meat not ranked 1"], truth=["Beef/meat ranked 1 (most)"],
         truth_source="Poore and Nemecek (2018), Science 360:987 (appendix K.3: Beef [India: Lamb] (1), Chicken wings (2), Pasta [Asia: rice] (3))",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_rank_power_nuclear_lowest", fig6="GHG footprint of nuclear is lower than gas or coal", q="Q53", dist=None,
         wording=RANK_INTRO + "Which source of electric energy emits the most greenhouse gases to provide power for a house? Please rank the items from 1 (most) to 3 (least) (by clicking and dragging the items). — Gas-fired power plant; Nuclear power plant; Coal-fired power station",
         options=["Nuclear ranked 3 (least)", "Nuclear not ranked 3"], truth=["Nuclear ranked 3 (least)"],
         truth_source="Pehl et al. (2017), Nature Energy 2:939 (appendix K.3: Coal (1), Gas (2), Nuclear (3))",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_rank_transport_plane_highest", fig6="GHG footprint of plane is higher than car or train/bus", q="Q51", dist=None,
         wording=RANK_INTRO + "If a [family of 4 or couple or person, depending on the country] travels [500 km from New York City to Toronto (for the U.S.)], with which mode of transportation do they emit the most greenhouse gases? Please rank the items from 1 (most) to 3 (least) (by clicking and dragging the items). — Car (running on diesel or gasoline); [Coach or Train, depending on the country]; Plane",
         options=["Plane ranked 1 (most)", "Plane not ranked 1"], truth=["Plane ranked 1 (most)"],
         truth_source="Ecopassenger; U.S.: National Geographic (appendix K.3: Plane (1), Car (2), Train/Coach (3))",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published; route and party size vary by country (appendix F)"),
    dict(item_id="clim_rank_region_total_china_highest", fig6="Total emissions of China are higher than other regions", q="Q54", dist=None,
         wording="Which region contributes most to global greenhouse gas emissions? Please rank the regions from 1 (most) to 4 (least) and note that multiple regions may have the same rank. — The U.S.; The European Union; China; India",
         options=["China ranked 1 (most)", "China not ranked 1"], truth=["China ranked 1 (most)"],
         truth_source="JRC (2018), Fossil CO2 Emissions of all World Countries (appendix K.3: China (1), U.S. (2), E.U. (3), India (4))",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_rank_region_percapita_us_highest", fig6="Per capita emissions of the US are higher than other regions", q="Q55", dist=None,
         wording="Consider now per capita emissions: in which region does the consumption of an average person contribute most to greenhouse gas emissions? Please rank the regions from 1 (most) to [4 / 5] (least). — The U.S.; The European Union; China; India; [Country, if not above or not in the EU]",
         options=["U.S. ranked 1 (most)", "U.S. not ranked 1"], truth=["U.S. ranked 1 (most)"],
         truth_source="Global Carbon Project (2019) (appendix K.3: U.S. (1), E.U. (2), China (3), India (4))",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_gas_hydrogen_not_ghg", fig6="Hydrogen is not a greenhouse gas", q="Q49", dist=None, wording=Q49,
         options=["Hydrogen not selected", "Hydrogen selected"], truth=["Hydrogen not selected"],
         truth_source=f"{IPCC21}, Figure SPM.5 (appendix K.3: CO2; Methane)",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_gas_co2_ghg", fig6="CO2 is a greenhouse gas", q="Q49", dist=None, wording=Q49,
         options=["CO2 selected", "CO2 not selected"], truth=["CO2 selected"],
         truth_source=f"{IPCC21}, Figure SPM.5 (appendix K.3: CO2; Methane)",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_gas_particulate_not_ghg", fig6="Particulate matter is not a greenhouse gas", q="Q49", dist=None, wording=Q49,
         options=["Particulate matter not selected", "Particulate matter selected"], truth=["Particulate matter not selected"],
         truth_source=f"{IPCC21}, Figure SPM.5 (appendix K.3: CO2; Methane)",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_gas_methane_ghg", fig6="Methane is a greenhouse gas", q="Q49", dist=None, wording=Q49,
         options=["Methane selected", "Methane not selected"], truth=["Methane selected"],
         truth_source=f"{IPCC21}, Figure SPM.5 (appendix K.3: CO2; Methane)",
         note="binary indicator as printed in Figure 6; only the share of correct answers is published"),
    dict(item_id="clim_droughts_likely", fig6="Severe droughts and heatwaves are likely", q="Q56", dist="D_droughts", wording=Q56,
         options=["Very unlikely", "Somewhat unlikely", "Somewhat likely", "Very likely"], truth=["Somewhat likely", "Very likely"],
         truth_source="IPCC AR5 WG2 (2014) (appendix K.3: Likely)", note="item 'Severe droughts and heatwaves' of Q56; Figure 6 counts 'Somewhat likely' or 'Very likely' as correct"),
    dict(item_id="clim_sea_level_likely", fig6="Sea-level rise is likely", q="Q56", dist="D_sea", wording=Q56,
         options=["Very unlikely", "Somewhat unlikely", "Somewhat likely", "Very likely"], truth=["Somewhat likely", "Very likely"],
         truth_source="IPCC AR5 WG2 (2014) (appendix K.3: Likely)", note="item 'Rising sea levels' of Q56; Figure 6 counts 'Somewhat likely' or 'Very likely' as correct"),
    dict(item_id="clim_volcanic_unlikely", fig6="More frequent volcanic eruptions are unlikely", q="Q56", dist="D_volcanic", wording=Q56,
         options=["Very unlikely", "Somewhat unlikely", "Somewhat likely", "Very likely"], truth=["Very unlikely", "Somewhat unlikely"],
         truth_source="Appendix K.3: Unlikely (Aubry et al. 2022, Bulletin of Volcanology 84:58: evidence inconclusive, primary drivers geological)",
         note="item 'More frequent volcanic eruptions' of Q56; Figure 6 counts 'Somewhat unlikely' or 'Very unlikely' as correct; the authors note the evidence is inconclusive"),
]
# Supplement panel -> option labels in the order the chart's text layer lists them (legend order).
SUPP_PANELS = {"A": ["None", "A little", "Some", "A lot", "Most"], "B": ["No", "Yes"],
               "D_droughts": ["Very likely", "Somewhat likely", "Somewhat unlikely", "Very unlikely"],
               "D_sea": ["Very likely", "Somewhat likely", "Somewhat unlikely", "Very unlikely"],
               "D_volcanic": ["Very likely", "Somewhat likely", "Somewhat unlikely", "Very unlikely"]}
# Hand resolutions of text-layer cells that the sum rule cannot settle, read from the rendered page
# (pdftoppm -r 100). Key: (iso3, panel) -> values in SUPP_PANELS order.
SUPP_OVERRIDES = {
    ("IDN", "A"): ((1, 4, 15, 36, 45), "page 141 rendered: the 'None' sliver is labelled 1 and 'A little' 4; the text layer merges them into '14'"),
}

# ----------------------------------------------------------------------------------------------------------
# C. Gapminder
# ----------------------------------------------------------------------------------------------------------
GM_SOURCE_ID = "gapminder_refugee_2023_report"
GM_WAVE = "gapminder_2023"
GM_FIELDWORK = ("2023-06", "2023-06")    # "In June 2023, Gapminder asked ..."; report dated 20 June 2023; exact days not stated
GM_COUNTRIES = {"US": ("USA", "United States"), "UK": ("GBR", "United Kingdom"), "Germany": ("DEU", "Germany"),
                "Colombia": ("COL", "Colombia"), "Pakistan": ("PAK", "Pakistan"), "Kenya": ("KEN", "Kenya"),
                "Türkiye": ("TUR", "Türkiye")}
# Options in questionnaire order (report p2, 'First: Test Your Facts'); truth as the report states it; the report
# page's own 'Data source' line is recorded at extract time and used as truth_source.
GM_ITEMS = [
    dict(item_id="gm_q1_largest_refugee_share_country", page=9, options=["Germany", "Lebanon", "Sweden"], truth="Lebanon"),
    dict(item_id="gm_q2_share_fled_to_high_income_2021", page=10, options=["Around 20%", "Around 30%", "Around 40%"], truth="Around 20%"),
    dict(item_id="gm_q3_refugees_four_middle_income_hosts_2022", page=11, options=["Around 1 million", "Around 5 million", "Around 9 million"], truth="Around 9 million"),
    dict(item_id="gm_q4_unhcr_funding_change", page=12, options=["Slightly less", "2 times more", "5 times more"], truth="5 times more"),
    dict(item_id="gm_q5_share_in_exile_over_four_years", page=13, options=["Less than 30%", "Around 45%", "More than 60%"], truth="More than 60%"),
    dict(item_id="gm_q6_refugees_world_total_2022", page=14, options=["46 million (0.6%)", "480 million (6%)", "720 million (9%)"], truth="46 million (0.6%)"),
    dict(item_id="gm_q7_west_europe_refugee_spending", page=15, options=["Less than $3 billion", "Around $5 billion", "More than $20 billion"], truth="More than $20 billion"),
    dict(item_id="gm_q8_syrian_refugees_cannot_afford_basics", page=16, options=["Around 30%", "Around 60%", "Around 90%"], truth="Around 90%"),
    dict(item_id="gm_q9_un_spending_per_refugee_per_day", page=17, options=["Around $1", "Around $25", "Around $45"], truth="Around $1"),
]

# ----------------------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------------------
def write_csv(path, rows, cols=None):
    cols = cols or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(rows)} rows")


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pdftotext(pdf, first, last, mode):
    """Text layer of pages first..last; mode = 'layout' or 'raw'. Returns a list of page strings."""
    out = subprocess.run(["pdftotext", f"-{mode}", "-f", str(first), "-l", str(last), pdf, "-"],
                         capture_output=True, text=True, check=True).stdout
    pages = out.split("\f")
    if pages and pages[-1] == "":
        pages.pop()
    return pages


def norm(s):
    """Collapse whitespace and ligatures (the Gapminder PDF uses the 'fl' ligature)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def majority(pcts):
    """Option with more than half of all answers (don't-knows included in the base), else 'no_majority'."""
    top = max(pcts.items(), key=lambda kv: kv[1])
    return top[0] if top[1] > 50 else "no_majority"


# ----------------------------------------------------------------------------------------------------------
# extract: Eurobarometer
# ----------------------------------------------------------------------------------------------------------
def extract_eurobarometer():
    import openpyxl
    rows = []
    for source_id, meta in EB_SOURCES.items():
        path = os.path.join(RAW, meta["workbook"])
        wb = openpyxl.load_workbook(path, read_only=True)
        sheets = [it["sheet"] for it in EB_ITEMS if it["source_id"] == source_id] + meta["summary_sheets"]
        for sheet in sheets:
            r = list(wb[sheet].iter_rows(values_only=True))
            cell = lambda i, j: (r[i][j] if len(r) > i and len(r[i]) > j and r[i][j] is not None else "")
            stem, statement, fieldwork = str(cell(2, 7)).strip(), str(cell(3, 7)).strip(), str(cell(1, 7)).strip()
            codes = [str(c).strip() if c is not None else "" for c in r[8]]
            totals = r[9]
            if str(totals[1]).strip() != "Total":
                sys.exit(f"{sheet}: unexpected layout (row 10 is not 'Total')")
            # percentage rows are located by their English label in column B
            labels = {str(r[i][1]).strip(): i for i in range(10, len(r)) if len(r[i]) > 1 and r[i][1] is not None}
            is_summary = sheet in meta["summary_sheets"]
            want = ["Average of correct answers", "Average of wrong answers", "Don't know"] if is_summary else ["True", "False", "Don't know"]
            missing = [w for w in want if w not in labels]
            if missing:
                sys.exit(f"{sheet}: percentage rows not found: {missing}; labels seen {list(labels)}")
            skipped = []
            for j, code in enumerate(codes):
                if j < 2 or code == "":
                    continue
                if code in EB_SKIP:
                    skipped.append(code); continue
                if code not in EB_CODES:
                    sys.exit(f"{sheet}: unknown country code {code!r}")
                iso3, name = EB_CODES[code]
                # the workbooks print '-' for a zero percentage (e.g. 0% don't know)
                vals = {w: (0.0 if r[labels[w]][j] == "-" else r[labels[w]][j]) for w in want}
                if any(v in (None, "") for v in vals.values()):
                    sys.exit(f"{sheet} {code}: blank percentage cell {vals}")
                rows.append({"source_id": source_id, "workbook": meta["workbook"], "sheet": sheet,
                             "row_type": "summary" if is_summary else "item",
                             "question_stem": re.sub(r"^\s*[A-Z0-9a-z.]+\.\s*", "", stem), "statement": statement,
                             "fieldwork_text": fieldwork, "country_code": code, "country_iso3": iso3, "country_name": name,
                             "n_country": int(totals[j]),
                             "pct_true_or_correct": round(float(vals[want[0]]) * 100),
                             "pct_false_or_wrong": round(float(vals[want[1]]) * 100),
                             "pct_dk": round(float(vals["Don't know"]) * 100)})
            print(f"  {source_id} {sheet}: {len([x for x in rows if x['sheet'] == sheet and x['source_id'] == source_id])} countries; skipped columns {skipped}")
    write_csv(os.path.join(T, "eurobarometer_true_false.csv"), rows)


# ----------------------------------------------------------------------------------------------------------
# extract: climate Figure 6 (two passes) and the supplement (two passes)
# ----------------------------------------------------------------------------------------------------------
def parse_fig6(page_text):
    """The 14 data rows of Figure 6 are the lines ending in exactly 22 integers (in -layout mode the row label
    shares the line; in -raw mode the line is numbers only), in figure row order."""
    rows = []
    for line in page_text.splitlines():
        toks = line.split()
        nums = []
        while toks and toks[-1].isdigit():
            nums.insert(0, int(toks.pop()))
        if len(nums) == 22:
            rows.append(nums)
    if len(rows) != 14:
        sys.exit(f"Figure 6: expected 14 data rows, found {len(rows)}")
    return rows


def extract_fig6():
    pdf = os.path.join(RAW, "w30265.pdf")
    for mode, fname in (("layout", "climate_fig6_pass1_layout.csv"), ("raw", "climate_fig6_pass2_raw.csv")):
        page = pdftotext(pdf, FIG6_PAGE, FIG6_PAGE, mode)[0]
        if "Figure 6: Knowledge about climate change across countries" not in page:
            sys.exit(f"Figure 6 not on page {FIG6_PAGE} in {mode} mode")
        data = parse_fig6(page)
        out = []
        for item, vals in zip(CLIM_ITEMS, data):
            for col, v in zip(FIG6_COLS, vals):
                out.append({"item_id": item["item_id"], "fig6_row_label": item["fig6"], "column": col,
                            "pct_correct": v, "pdf_page": FIG6_PAGE, "extraction": f"pdftotext -{mode}"})
        write_csv(os.path.join(T, fname), out)


def resolve(tokens, k, check=None, tol=2):
    """Return (values, how). Stacked-bar labels in the text layer sometimes merge two small adjacent numbers
    ('5 2' -> '52'); try every single split of one token into two when the count is short, keep candidates
    whose sum is 100 +- tol and that pass `check`, and accept only a unique candidate."""
    toks = [int(t) for t in tokens]
    if len(toks) == k and abs(sum(toks) - 100) <= tol and (check is None or check(toks)):
        return toks, "ok"
    cands = []
    if len(toks) == k - 1:
        for i, t in enumerate(toks):
            s = str(t)
            for cut in range(1, len(s)):
                a, b = int(s[:cut]), int(s[cut:])
                cand = toks[:i] + [a, b] + toks[i + 1:]
                if abs(sum(cand) - 100) <= tol and (check is None or check(cand)):
                    cands.append((cand, f"split '{s}' -> {a} {b}"))
    if len(cands) == 1:
        return cands[0]
    return None, ("ambiguous: " + "; ".join(c[1] for c in cands)) if cands else "unresolved"


def supplement_pages(layout_pages):
    """(page_index, iso3, N) for every per-country 'Knowledge about climate change' figure page."""
    found = []
    for i, p in enumerate(layout_pages):
        if "Knowledge about climate change" in p and "Figure" in p:
            ms = []
            for q in layout_pages[i:i + 3]:
                ms = [m for m in re.findall(r"Knowledge index:\s*([A-Za-z .]+?)\s*\(N=\s*([\d,]+)", q) if m[0] != "All countries"]
                if ms:
                    break
            if not ms:
                sys.exit(f"supplement page {i + 1}: country name not found")
            name, n = ms[0]
            if name not in CLIM_SUPP_NAMES:
                sys.exit(f"supplement page {i + 1}: unknown country {name!r}")
            found.append((i, CLIM_SUPP_NAMES[name], int(n.replace(",", ""))))
    if len(found) != 20:
        sys.exit(f"supplement: expected 20 country pages, found {len(found)}")
    return found


SUPP_FIG6_TOL = 2   # the supplement shares reproduce the Figure 6 indicator within 2 points (validate_categorical.py check 7 lists the gaps)


def supp_check(panel, fig6_by_item_iso):
    """Cross-check closure for resolve(): the panel's Figure 6 indicator must be reproduced within SUPP_FIG6_TOL."""
    def chk(iso3):
        if panel == "A":
            return lambda v: abs(v[3] + v[4] - fig6_by_item_iso[("clim_cc_real_anthropogenic", iso3)]) <= SUPP_FIG6_TOL
        if panel == "B":
            return lambda v: abs(v[0] - fig6_by_item_iso[("clim_halving_insufficient", iso3)]) <= SUPP_FIG6_TOL
        item = {"D_droughts": "clim_droughts_likely", "D_sea": "clim_sea_level_likely", "D_volcanic": "clim_volcanic_unlikely"}[panel]
        if panel == "D_volcanic":
            return lambda v: abs(v[2] + v[3] - fig6_by_item_iso[(item, iso3)]) <= SUPP_FIG6_TOL
        return lambda v: abs(v[0] + v[1] - fig6_by_item_iso[(item, iso3)]) <= SUPP_FIG6_TOL
    return chk


def extract_supplement():
    pdf = os.path.join(RAW, "OECD_Climate_Change_Country_by_country.pdf")
    layout_pages = pdftotext(pdf, 1, 400, "layout")
    pages = supplement_pages(layout_pages)
    fig6 = {(r["item_id"], r["column"]): int(r["pct_correct"]) for r in read_csv(os.path.join(T, "climate_fig6_pass1_layout.csv"))}
    out = []
    for i, iso3, n in pages:
        pno = i + 1
        fig_no = re.search(r"Figure (\d+): Knowledge about climate change", layout_pages[i]).group(1)
        # pass 1: layout text. Panel A+B share one line (5 + 2 numbers); panel D rows carry their labels.
        lay = layout_pages[i].splitlines()
        ab = next(l for l in lay if len(re.findall(r"\b\d{1,3}\b", l)) >= 6 and "Figure" not in l)
        ab_tok = re.findall(r"\b\d{1,3}\b", ab)
        lay_tokens = {"A": ab_tok[:-2], "B": ab_tok[-2:]}
        for key, label in (("D_droughts", "Severe droughts and heatwaves"), ("D_sea", "Sea-level rise"), ("D_volcanic", "More frequent volcanic eruptions")):
            line = next(l for l in lay if l.strip().startswith(label))
            lay_tokens[key] = re.findall(r"\b\d{1,3}\b", line.replace(label, ""))
        # pass 2: raw (content-stream) order: A, B, panel C bar labels (with %), axis line, D rows droughts/sea/volcanic.
        raw = pdftotext(pdf, pno, pno, "raw")[0]
        # numbers-only lines with at least two tokens (drops the axis line and the single-token page number)
        numeric = [l.strip() for l in raw.splitlines()
                   if re.fullmatch(r"[\d ]+", l.strip()) and len(l.split()) >= 2 and not l.strip().startswith("0 10 20")]
        if len(numeric) < 5:
            sys.exit(f"supplement p{pno}: raw pass found {len(numeric)} numeric lines")
        raw_tokens = {"A": numeric[0].split(), "B": numeric[1].split(), "D_droughts": numeric[-3].split(),
                      "D_sea": numeric[-2].split(), "D_volcanic": numeric[-1].split()}
        for panel, labels in SUPP_PANELS.items():
            res = {}
            for passname, toks in (("pass1_layout", lay_tokens[panel]), ("pass2_raw", raw_tokens[panel])):
                vals, how = resolve(toks, len(labels), supp_check(panel, fig6)(iso3))
                res[passname] = (vals, how, " ".join(toks))
            if (iso3, panel) in SUPP_OVERRIDES:
                final, how = list(SUPP_OVERRIDES[(iso3, panel)][0]), "override: " + SUPP_OVERRIDES[(iso3, panel)][1]
            else:
                v1, v2 = res["pass1_layout"][0], res["pass2_raw"][0]
                if v1 is not None and v2 is not None and v1 != v2:
                    sys.exit(f"supplement p{pno} {iso3} {panel}: passes disagree {v1} vs {v2}")
                final = v1 if v1 is not None else v2
                if final is None:
                    sys.exit(f"supplement p{pno} {iso3} {panel}: unresolved in both passes ({res})")
                how = "both passes" if (v1 is not None and v2 is not None) else ("pass1 only" if v1 is not None else "pass2 only")
            for lab, v in zip(labels, final):
                out.append({"country_iso3": iso3, "panel": panel, "option": lab, "pct": v, "pdf_page": pno,
                            "figure": f"Figure {fig_no}", "n_country_full_sample": n,
                            "pass1_layout_tokens": res["pass1_layout"][2], "pass1_result": res["pass1_layout"][1],
                            "pass2_raw_tokens": res["pass2_raw"][2], "pass2_result": res["pass2_raw"][1], "resolution": how})
    write_csv(os.path.join(T, "climate_supplement_distributions.csv"), out)


# ----------------------------------------------------------------------------------------------------------
# extract: Gapminder pass 1 (text layer)
# ----------------------------------------------------------------------------------------------------------
def extract_gapminder():
    pdf = os.path.join(RAW, "gapminder_refugee_misconception_2023.pdf")
    pages = pdftotext(pdf, 9, 17, "layout")
    out = []
    for item, page in zip(GM_ITEMS, pages):
        lines = page.splitlines()
        hdr = next(i for i, l in enumerate(lines) if "RESULTS FROM GAPMINDER" in l)
        ca = next(i for i, l in enumerate(lines) if "CORRECT ANSWER" in l and "WRONG ANSWER" in l)
        wording = norm(" ".join(lines[hdr + 1:ca]))
        # the three column labels are the next line with quoted strings (one closing quote is missing on p12)
        lab_line = next(l for l in lines[ca + 1:] if "“" in l)
        labels = [norm(s.replace("”", "")) for s in lab_line.split("“")[1:]]
        if len(labels) != 3 or sorted(labels) != sorted(item["options"]):
            sys.exit(f"gapminder p{item['page']}: column labels {labels} do not match options {item['options']}")
        src = next((norm(l.split(":", 1)[1]) for l in lines if l.strip().startswith("Data source:")), "")
        seen = set()
        for i, l in enumerate(lines[ca + 1:], start=ca + 1):
            m = re.match(r"^\s*(Kenya|US|UK|Colombia|Pakistan|Türkiye|Germany|Average)\b(.*)$", l)
            if not m or m.group(1) in seen:
                continue
            country, rest = m.group(1), m.group(2)
            nums = re.findall(r"(\d+)%", rest)
            flag = ""
            if len(nums) < 3:
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                nn = re.findall(r"(\d+)%", nxt)
                if len(nn) == 3 and not re.match(r"^\s*(Kenya|US|UK|Colombia|Pakistan|Türkiye|Germany|Average)\b", nxt):
                    flag = f"country line carried {nums or 'no'} value(s); the 3 values on the following line were used"
                    nums = nn
            if len(nums) != 3:
                flag = f"unresolved in the text layer: {len(nums)} values found ({' '.join(nums)})"
                nums = ["", "", ""]
            seen.add(country)
            for lab, v in zip(labels, nums):
                out.append({"item_id": item["item_id"], "pdf_page": item["page"], "country": country, "option": lab,
                            "pct": v, "question_wording": wording, "data_source_line": src, "flag": flag})
        if len(seen) != 8:
            sys.exit(f"gapminder p{item['page']}: found rows for {sorted(seen)}")
    write_csv(os.path.join(T, "gapminder_pass1_textlayer.csv"), out)


# ----------------------------------------------------------------------------------------------------------
# build
# ----------------------------------------------------------------------------------------------------------
def build_pairs():
    pairs = []
    # A. Eurobarometer
    eb = [r for r in read_csv(os.path.join(T, "eurobarometer_true_false.csv")) if r["row_type"] == "item"]
    for it in EB_ITEMS:
        meta = EB_SOURCES[it["source_id"]]
        rows = [r for r in eb if r["source_id"] == it["source_id"] and r["sheet"] == it["sheet"]]
        if not rows:
            sys.exit(f"no transcription rows for {it['source_id']} {it['sheet']}")
        for r in rows:
            # pct_per_option holds the substantive options; don't-know is pct_dk (the base for all shares is all
            # respondents, so the shares plus pct_dk sum to 100 and the majority test includes don't-knows)
            p = {"True": int(r["pct_true_or_correct"]), "False": int(r["pct_false_or_wrong"])}
            dk = int(r["pct_dk"])
            pairs.append({"source_id": it["source_id"], "wave": meta["wave"], "country_iso3": r["country_iso3"],
                          "country_name": r["country_name"], "item_id": it["item_id"],
                          "question_wording": f"{r['question_stem']} — \"{r['statement']}\"",
                          "options": json.dumps(["True", "False", "Don't know"]),
                          "pct_per_option": json.dumps(p), "pct_dk": dk,
                          "pct_correct": p[it["truth"]] if it["truth"] else "",
                          "public_majority_option": majority({**p, "Don't know": dk}),
                          "truth_option": it["truth"], "truth_source": it["truth_source"], "truth_note": it["note"],
                          "fieldwork_start": meta["fieldwork"][0], "fieldwork_end": meta["fieldwork"][1],
                          "n_country": r["n_country"], "source_file": r["workbook"], "source_page_or_sheet": f"sheet {r['sheet']}"})
    # B. climate
    fig6 = {(r["item_id"], r["column"]): int(r["pct_correct"]) for r in read_csv(os.path.join(T, "climate_fig6_pass1_layout.csv"))}
    supp = read_csv(os.path.join(T, "climate_supplement_distributions.csv"))
    dist, supp_meta = {}, {}
    for r in supp:
        dist.setdefault((r["country_iso3"], r["panel"]), {})[r["option"]] = int(r["pct"])
        supp_meta[r["country_iso3"]] = (r["pdf_page"], r["figure"], r["n_country_full_sample"])
    for it in CLIM_ITEMS:
        for iso3, name in CLIM_COUNTRIES.items():
            pc = fig6[(it["item_id"], iso3)]
            page, fig, n = supp_meta[iso3]
            if it["dist"]:
                p = {o: dist[(iso3, it["dist"])][o] for o in it["options"]}
                src_page = f"w30265.pdf p{FIG6_PAGE} Figure 6 (pct_correct); supplement p{page} {fig} panel {it['dist'][0]} (distribution)"
            else:
                p = {it["options"][0]: pc, it["options"][1]: 100 - pc}
                src_page = f"w30265.pdf p{FIG6_PAGE} Figure 6"
            pairs.append({"source_id": CLIM_SOURCE_ID, "wave": CLIM_WAVE, "country_iso3": iso3, "country_name": name,
                          "item_id": it["item_id"], "question_wording": it["wording"], "options": json.dumps(it["options"]),
                          "pct_per_option": json.dumps(p), "pct_dk": "", "pct_correct": pc,
                          "public_majority_option": majority(p), "truth_option": " | ".join(it["truth"]),
                          "truth_source": it["truth_source"],
                          "truth_note": (it["note"] + "; " if it["note"] else "") + "control group only (respondents who saw no pedagogical video); n_country is the full country sample from the supplement, the control-group n is not printed",
                          "fieldwork_start": CLIM_FIELDWORK[0], "fieldwork_end": CLIM_FIELDWORK[1], "n_country": n,
                          "source_file": "w30265.pdf; OECD_Climate_Change_Country_by_country.pdf", "source_page_or_sheet": src_page})
    # C. Gapminder: pass 1 (text layer) with pass 2 (visual) filling cells the text layer left unresolved
    p1 = read_csv(os.path.join(T, "gapminder_pass1_textlayer.csv"))
    p2 = {(r["item_id"], r["country"], r["option"]): int(r["pct"]) for r in read_csv(os.path.join(T, "gapminder_pass2_visual.csv"))}
    meta = {r["item_id"]: (r["question_wording"], r["data_source_line"]) for r in p1}
    vals = {}
    for r in p1:
        key = (r["item_id"], r["country"], r["option"])
        vals[key] = int(r["pct"]) if r["pct"] != "" else p2[key]
    for it in GM_ITEMS:
        wording, src = meta[it["item_id"]]
        for cname, (iso3, name) in GM_COUNTRIES.items():
            p = {o: vals[(it["item_id"], cname, o)] for o in it["options"]}
            pairs.append({"source_id": GM_SOURCE_ID, "wave": GM_WAVE, "country_iso3": iso3, "country_name": name,
                          "item_id": it["item_id"], "question_wording": wording, "options": json.dumps(it["options"]),
                          "pct_per_option": json.dumps(p), "pct_dk": "", "pct_correct": p[it["truth"]],
                          "public_majority_option": majority(p), "truth_option": it["truth"],
                          "truth_source": f"{src} (as stated on the report page)",
                          "truth_note": "online SurveyMonkey panel; the report gives only the total n = 1,632 over 7 countries (about 230 per country), so per-country n is small and not stated",
                          "fieldwork_start": GM_FIELDWORK[0], "fieldwork_end": GM_FIELDWORK[1], "n_country": "",
                          "source_file": "gapminder_refugee_misconception_2023.pdf", "source_page_or_sheet": f"p{it['page']}"})
    write_csv(os.path.join(C, "pairs_categorical_v1.csv"), pairs, PAIRS_COLS)
    return pairs


def yaml_scalar(v):
    return json.dumps(v, ensure_ascii=False)


def build_items_yaml(pairs):
    """items_categorical.yaml, one entry per item, generated from the item tables above so that wording,
    options and truth cannot drift from pairs_categorical_v1.csv (validate_categorical.py checks this)."""
    first = {}
    for r in pairs:
        first.setdefault(r["item_id"], r)
    lines = ["# Item dictionary for the categorical fact-question track (generated by scripts/build_categorical.py",
             "# from the item tables in that script; do not edit by hand).",
             "# include_in_main: false = kept in pairs_categorical_v1.csv for completeness but excluded from the main analysis set.",
             "items:"]
    eb_main = {it["item_id"]: it for it in EB_ITEMS}
    for item_id, r in first.items():
        main, reason = True, ""
        if item_id in eb_main and not eb_main[item_id]["main"]:
            main, reason = False, eb_main[item_id]["note"]
        lines += [f"  - item_id: {item_id}",
                  f"    source: {r['source_id']}",
                  f"    wave: {r['wave']}",
                  f"    wording: {yaml_scalar(r['question_wording'])}",
                  f"    options: {yaml_scalar(json.loads(r['options']))}",
                  f"    truth_option: {yaml_scalar(r['truth_option'])}",
                  f"    truth_source: {yaml_scalar(r['truth_source'])}",
                  f"    truth_note: {yaml_scalar(r['truth_note'])}",
                  f"    include_in_main: {'true' if main else 'false'}"]
        if reason:
            lines.append(f"    exclusion_reason: {yaml_scalar(reason)}")
    path = os.path.join(C, "items_categorical.yaml")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(first)} items")


# ----------------------------------------------------------------------------------------------------------
# countries_extra.csv (same columns as data/countries.csv)
# ----------------------------------------------------------------------------------------------------------
EXTRA_LANGUAGE = {
    "AUT": "German", "BGR": "Bulgarian", "CZE": "Czech", "DNK": "Danish", "EST": "Estonian", "GRC": "Greek", "HRV": "Croatian",
    "CYP": "Greek", "LVA": "Latvian", "LTU": "Lithuanian", "LUX": "Luxembourgish/French/German", "MLT": "Maltese/English",
    "PRT": "Portuguese", "ROU": "Romanian", "SVN": "Slovene", "SVK": "Slovak", "FIN": "Finnish", "MKD": "Macedonian",
    "MNE": "Montenegrin", "SRB": "Serbian", "ALB": "Albanian", "CHE": "German/French/Italian", "NOR": "Norwegian",
    "BIH": "Bosnian/Croatian/Serbian", "ISL": "Icelandic", "XKX": "Albanian/Serbian", "MDA": "Romanian", "GEO": "Georgian",
    "CHN": "Mandarin", "UKR": "Ukrainian", "PAK": "Urdu/English", "KEN": "Swahili/English",
}
# English Wikipedia search phrase where it differs from the source name (same convention as scripts/fetch_web_presence.py).
EXTRA_SEARCH_PHRASE = {"CZE": "Czech Republic", "XKX": "Kosovo", "MKD": "North Macedonia"}
UA = "misperception-bench/0.1 (research dataset build; contact: repo owner)"


def wb_latest(path, iso3, max_year=2024):
    d = json.load(open(path))
    best = None
    for r in d[1]:
        if r["countryiso3code"] == iso3 and r["value"] is not None and int(r["date"]) <= max_year:
            if best is None or int(r["date"]) > best[1]:
                best = (r["value"], int(r["date"]))
    return best or ("", "")


def extra_countries(pairs):
    have = {r["country_iso3"] for r in read_csv(os.path.join(D, "countries.csv"))}
    names = {}
    for r in pairs:
        names.setdefault(r["country_iso3"], r["country_name"])
    return {iso3: names[iso3] for iso3 in sorted(names) if iso3 not in have}


def build_countries_extra(pairs):
    extra = extra_countries(pairs)
    wbdir = os.path.join(RAW, "worldbank")
    if not os.path.exists(os.path.join(wbdir, "countries.json")):
        print("World Bank dumps not in data/raw/categorical/worldbank/; countries_extra.csv left as is")
        return
    meta = {c["id"]: c for c in json.load(open(os.path.join(wbdir, "countries.json")))[1]}
    wp_path = os.path.join(RAW, "web_presence_extra.json")
    wp = json.load(open(wp_path)) if os.path.exists(wp_path) else {"countries": {}, "fetched_on": ""}
    rows = []
    for iso3, name in extra.items():
        if iso3 not in meta:
            sys.exit(f"{iso3} not in the World Bank country list")
        if iso3 not in EXTRA_LANGUAGE:
            sys.exit(f"no main_language entry for {iso3}")
        gdp, gdp_year = wb_latest(os.path.join(wbdir, "NY.GDP.PCAP.PP.CD.json"), iso3)
        mig, mig_year = wb_latest(os.path.join(wbdir, "SM.POP.TOTL.ZS.json"), iso3)
        w = wp["countries"].get(iso3, {})
        rows.append({"country_iso3": iso3, "country_name_ipsos": name, "country_name_worldbank": meta[iso3]["name"],
                     "main_language": EXTRA_LANGUAGE[iso3],
                     "wb_income_group": meta[iso3]["incomeLevel"]["value"], "wb_region": meta[iso3]["region"]["value"],
                     "gdp_pcap_ppp": round(gdp, 0) if gdp != "" else "", "gdp_pcap_ppp_year": gdp_year,
                     "migrant_stock_pct_wdi": round(mig, 2) if mig != "" else "", "migrant_stock_pct_year": mig_year,
                     "enwiki_mentions": w.get("enwiki_mentions", ""), "wikidata_p17_count": "",
                     "web_presence_fetched_on": wp.get("fetched_on", "") if w else "",
                     "ipsos_representative_sample": ""})
    write_csv(os.path.join(C, "countries_extra.csv"), rows)
    missing = [r["country_iso3"] for r in rows if r["enwiki_mentions"] == ""]
    print("extra countries without web presence:", missing or "none")


def fetch_web_presence(pairs):
    """enwiki exact-phrase total hits for the extra countries (same query as scripts/fetch_web_presence.py);
    the Wikidata P17 count is not attempted (it times out for most countries, see data/README.md)."""
    extra = extra_countries(pairs)
    out_path = os.path.join(RAW, "web_presence_extra.json")
    out = {"fetched_on": date.today().isoformat(),
           "enwiki_query": 'en.wikipedia.org/w/api.php?action=query&list=search&srsearch="<name>"&srinfo=totalhits',
           "countries": {}}
    if os.path.exists(out_path):
        out["countries"] = json.load(open(out_path)).get("countries", {})
    for iso3, name in extra.items():
        if out["countries"].get(iso3, {}).get("enwiki_mentions") is not None:
            continue
        phrase = EXTRA_SEARCH_PHRASE.get(iso3, name)
        q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": f'"{phrase}"', "srinfo": "totalhits",
                                    "srlimit": 1, "format": "json"})
        req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + q, headers={"User-Agent": UA, "Accept": "application/json"})
        hits = None
        for attempt in range(4):  # Wikimedia rate-limits unauthenticated clients (HTTP 429): wait and retry
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    hits = json.load(r)["query"]["searchinfo"]["totalhits"]
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(30 * (attempt + 1)); continue
                print(f"{iso3} {name}: fetch failed ({e})", flush=True); break
            except Exception as e:
                print(f"{iso3} {name}: fetch failed ({e})", flush=True); break
        if hits is None:  # leave blank; countries_extra.csv keeps web presence empty for this country
            continue
        out["countries"][iso3] = {"name": name, "search_phrase": phrase, "enwiki_mentions": hits}
        print(f"{iso3} {name:25s} enwiki={hits}", flush=True)
        json.dump(out, open(out_path, "w"), indent=1)
        time.sleep(5)
    print("wrote", os.path.relpath(out_path, ROOT))


def main():
    args = sys.argv[1:] or (["extract", "build"] if os.path.exists(os.path.join(RAW, "w30265.pdf")) else ["build"])
    os.makedirs(T, exist_ok=True)
    if "extract" in args:
        extract_eurobarometer()
        extract_fig6()
        extract_supplement()
        extract_gapminder()
    pairs = None
    if "build" in args:
        pairs = build_pairs()
        build_items_yaml(pairs)
        build_countries_extra(pairs)
    if "fetch-web-presence" in args:
        pairs = pairs or read_csv(os.path.join(C, "pairs_categorical_v1.csv"))
        fetch_web_presence(pairs)
        build_countries_extra(pairs)


if __name__ == "__main__":
    main()
