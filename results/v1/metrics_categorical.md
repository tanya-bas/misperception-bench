# Categorical track metrics

Source: `results/v1/results.jsonl`. Option cells = modal parsed option across samples; number cells = median. Log-odds clip = 0.0005. Inheritance counts only rows where more than half of the public chose a wrong option.

## Summary

| model | plain accuracy | official accuracy | majority-wrong rows | sides with public | sides with truth | flatten slope pooled | abs(M_public - share correct) | memory within 5 | mean entropy plain (bits) |
|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | 92% | 93% | 146 | 18% | 79% | 0.07 | 19.7 | 17% | n/a |
| qwen3.5-9b | 94% | 93% | 146 | 20% | 77% | 0.09 | 24.3 | 17% | n/a |
| qwen3.8-27b | 96% | 91% | 146 | 3% | 95% | 0.07 | 25.6 | 19% | n/a |

## gpt-oss-20b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 4860 | 98% | 0% | 1% | 0% | 1% |
| official | 4860 | 97% | 0% | 1% | 0% | 2% |
| public_guess | 4860 | 99% | 0% | 0% | 0% | 1% |
| memory_check | 4860 | 94% | 5% | 1% | 0% | 0% |

### Accuracy of the model's own answer (modal option in the truth set)

| scope | cells | plain accuracy | official accuracy |
|---|---|---|---|
| pooled | 971 | 92% | 93% |
| climate_attitudes_nber30265 | 280 | 98% | 100% |
| eb104_volume_a | 110 | 85% | 85% |
| eb516_volume_a | 380 | 100% | 100% |
| eb522_volume_a | 108 | 100% | 100% |
| gapminder_refugee_2023_report | 63 | 27% | 27% |
| ipsos_homicide_2024 | 30 | 80% | 83% |

### Inheritance where a public majority (> 50%) is wrong, plain prompt

| scope | rows | sides with public majority | sides with truth | other |
|---|---|---|---|---|
| pooled | 146 | 18% | 79% | 3% |
| climate_attitudes_nber30265 | 51 | 0% | 100% | 0% |
| eb104_volume_a | 3 | 67% | 33% | 0% |
| eb516_volume_a | 31 | 0% | 100% | 0% |
| eb522_volume_a | 5 | 0% | 100% | 0% |
| gapminder_refugee_2023_report | 36 | 67% | 25% | 8% |
| ipsos_homicide_2024 | 20 | 0% | 90% | 10% |

### Flattening: logit(M_public) on logit(share correct) across countries

| item | countries | slope | 95% CI | corr | mean abs(M_public - share correct) |
|---|---|---|---|---|---|
| clim_cc_real_anthropogenic | 20 | -0.03 | [-0.29, 0.24] | -0.04 | 8.6 |
| clim_droughts_likely | 20 | -0.03 | [-0.34, 0.43] | -0.03 | 20.1 |
| clim_gas_co2_ghg | 20 | 0.14 | [-0.11, 0.43] | 0.25 | 9.9 |
| clim_gas_hydrogen_not_ghg | 20 | -0.04 | [-0.85, 0.69] | -0.03 | 14.7 |
| clim_gas_methane_ghg | 20 | 0.08 | [-0.17, 0.36] | 0.12 | 32.1 |
| clim_gas_particulate_not_ghg | 20 | 0.49 | [0.10, 1.15] | 0.40 | 10.8 |
| clim_halving_insufficient | 20 | -0.10 | [-0.37, 0.21] | -0.14 | 20.9 |
| clim_rank_food_beef_highest | 20 | 0.12 | [-0.15, 0.46] | 0.22 | 10.9 |
| clim_rank_power_nuclear_lowest | 20 | 0.29 | [-0.16, 0.98] | 0.26 | 26.0 |
| clim_rank_region_percapita_us_highest | 20 | 0.30 | [-0.37, 0.92] | 0.19 | 15.5 |
| clim_rank_region_total_china_highest | 20 | 0.14 | [-0.17, 0.66] | 0.14 | 13.6 |
| clim_rank_transport_plane_highest | 20 | -0.50 | [-0.75, -0.21] | -0.60 | 27.1 |
| clim_sea_level_likely | 20 | -0.55 | [-1.21, 0.28] | -0.36 | 24.4 |
| clim_volcanic_unlikely | 20 | -0.03 | [-0.51, 0.56] | -0.03 | 18.4 |
| eb104_sd20a1_euro_area_20_members | 37 | 0.45 | [-0.43, 1.23] | 0.19 | 25.5 |
| eb104_sd20a2_meps_directly_elected | 37 | 0.31 | [0.01, 0.56] | 0.31 | 18.0 |
| eb104_sd20a3_switzerland_member | 37 | -0.01 | [-0.31, 0.26] | -0.01 | 17.9 |
| eb516_q01_humans_dinosaurs | 38 | 0.09 | [-0.17, 0.30] | 0.12 | 24.1 |
| eb516_q02_continents_move | 38 | 0.09 | [-0.04, 0.25] | 0.18 | 12.4 |
| eb516_q03_antibiotics_kill_viruses | 38 | -0.06 | [-0.35, 0.23] | -0.06 | 27.4 |
| eb516_q04_oxygen_from_plants | 38 | 0.20 | [-0.08, 0.62] | 0.20 | 6.6 |
| eb516_q05_lasers_sound_waves | 38 | 0.19 | [-0.31, 0.73] | 0.13 | 26.5 |
| eb516_q06_population_over_10bn | 38 | -0.10 | [-0.49, 0.36] | -0.06 | 37.6 |
| eb516_q08_humans_evolved | 38 | 0.03 | [-0.17, 0.17] | 0.05 | 19.7 |
| eb516_q09_climate_natural_cycles | 38 | -0.19 | [-0.64, 0.17] | -0.13 | 19.5 |
| eb516_q10_cancer_cure_hidden | 38 | -0.05 | [-0.27, 0.19] | -0.06 | 22.1 |
| eb516_q11_viruses_made_in_labs | 38 | 0.23 | [-0.06, 0.50] | 0.27 | 19.0 |
| eb522_q1_antibiotics_kill_viruses | 27 | 0.37 | [0.02, 0.85] | 0.31 | 22.0 |
| eb522_q2_antibiotics_colds | 27 | 0.29 | [-0.15, 0.87] | 0.21 | 19.6 |
| eb522_q3_unnecessary_use_ineffective | 27 | 0.25 | [0.05, 0.40] | 0.45 | 23.5 |
| eb522_q4_side_effects | 27 | 0.13 | [-0.49, 0.68] | 0.10 | 7.7 |
| gm_q1_largest_refugee_share_country | 7 | 0.24 | [-0.82, 1.59] | 0.19 | 14.4 |
| gm_q2_share_fled_to_high_income_2021 | 7 | 0.01 | [-1.66, 0.65] | 0.01 | 13.4 |
| gm_q3_refugees_four_middle_income_hosts_2022 | 7 | 0.49 | [-1.86, 2.04] | 0.31 | 10.3 |
| gm_q4_unhcr_funding_change | 7 | 0.66 | [-0.54, 3.43] | 0.43 | 8.4 |
| gm_q5_share_in_exile_over_four_years | 7 | 0.16 | [-4.94, 3.14] | 0.05 | 16.0 |
| gm_q6_refugees_world_total_2022 | 7 | -0.13 | [-1.62, 1.51] | -0.08 | 29.4 |
| gm_q7_west_europe_refugee_spending | 7 | 0.04 | [-1.16, 1.50] | 0.02 | 10.6 |
| gm_q8_syrian_refugees_cannot_afford_basics | 7 | -0.88 | [-2.26, 2.09] | -0.38 | 33.1 |
| gm_q9_un_spending_per_refugee_per_day | 7 | -0.44 | [-2.72, 1.29] | -0.24 | 15.1 |
| homicide_trend | 30 | 0.02 | [-0.23, 0.24] | 0.03 | 20.1 |
| pooled (item FE) | 972 | 0.07 | [0.01, 0.14] | | |

### Memorization check (memory_check vs real share correct)

| scope | cells | within 2 pts | within 5 pts | corr |
|---|---|---|---|---|
| pooled | 972 | 7% | 17% | 0.35 |
| climate_attitudes_nber30265 | 280 | 8% | 15% | 0.33 |
| eb104_volume_a | 111 | 4% | 13% | -0.37 |
| eb516_volume_a | 380 | 6% | 16% | 0.33 |
| eb522_volume_a | 108 | 9% | 21% | 0.25 |
| gapminder_refugee_2023_report | 63 | 10% | 19% | -0.38 |
| ipsos_homicide_2024 | 30 | 20% | 27% | 0.14 |

## qwen3.5-9b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 4860 | 100% | 0% | 0% | 0% | 0% |
| official | 4860 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 4860 | 100% | 0% | 0% | 0% | 0% |
| memory_check | 4860 | 100% | 0% | 0% | 0% | 0% |

### Accuracy of the model's own answer (modal option in the truth set)

| scope | cells | plain accuracy | official accuracy |
|---|---|---|---|
| pooled | 972 | 94% | 93% |
| climate_attitudes_nber30265 | 280 | 100% | 100% |
| eb104_volume_a | 111 | 100% | 100% |
| eb516_volume_a | 380 | 97% | 90% |
| eb522_volume_a | 108 | 100% | 100% |
| gapminder_refugee_2023_report | 63 | 63% | 68% |
| ipsos_homicide_2024 | 30 | 30% | 60% |

### Inheritance where a public majority (> 50%) is wrong, plain prompt

| scope | rows | sides with public majority | sides with truth | other |
|---|---|---|---|---|
| pooled | 146 | 20% | 77% | 3% |
| climate_attitudes_nber30265 | 51 | 0% | 100% | 0% |
| eb104_volume_a | 3 | 0% | 100% | 0% |
| eb516_volume_a | 31 | 0% | 100% | 0% |
| eb522_volume_a | 5 | 0% | 100% | 0% |
| gapminder_refugee_2023_report | 36 | 33% | 56% | 11% |
| ipsos_homicide_2024 | 20 | 85% | 15% | 0% |

### Flattening: logit(M_public) on logit(share correct) across countries

| item | countries | slope | 95% CI | corr | mean abs(M_public - share correct) |
|---|---|---|---|---|---|
| clim_cc_real_anthropogenic | 20 | -0.21 | [-0.48, -0.02] | -0.26 | 11.2 |
| clim_droughts_likely | 20 | 0.18 | [-0.25, 0.58] | 0.19 | 16.4 |
| clim_gas_co2_ghg | 20 | 0.23 | [0.02, 0.43] | 0.40 | 10.9 |
| clim_gas_hydrogen_not_ghg | 20 | 0.01 | [-0.73, 0.88] | 0.00 | 26.1 |
| clim_gas_methane_ghg | 20 | 0.29 | [0.03, 0.59] | 0.43 | 33.0 |
| clim_gas_particulate_not_ghg | 20 | 0.45 | [0.00, 0.84] | 0.36 | 18.1 |
| clim_halving_insufficient | 20 | -0.03 | [-0.24, 0.18] | -0.07 | 16.5 |
| clim_rank_food_beef_highest | 20 | 0.32 | [0.04, 0.60] | 0.50 | 8.9 |
| clim_rank_power_nuclear_lowest | 20 | 0.22 | [-0.21, 0.65] | 0.22 | 15.0 |
| clim_rank_region_percapita_us_highest | 20 | -0.40 | [-0.90, 0.07] | -0.33 | 17.1 |
| clim_rank_region_total_china_highest | 20 | -0.44 | [-0.71, -0.12] | -0.66 | 29.4 |
| clim_rank_transport_plane_highest | 20 | -0.01 | [-0.19, 0.13] | -0.02 | 25.1 |
| clim_sea_level_likely | 20 | 0.11 | [-0.40, 0.59] | 0.12 | 8.1 |
| clim_volcanic_unlikely | 20 | 0.15 | [-0.25, 0.59] | 0.16 | 49.7 |
| eb104_sd20a1_euro_area_20_members | 37 | -0.14 | [-0.46, 0.19] | -0.13 | 34.9 |
| eb104_sd20a2_meps_directly_elected | 37 | 0.16 | [0.01, 0.31] | 0.38 | 12.3 |
| eb104_sd20a3_switzerland_member | 37 | -0.09 | [-0.22, 0.02] | -0.23 | 19.7 |
| eb516_q01_humans_dinosaurs | 38 | -0.02 | [-0.22, 0.27] | -0.04 | 20.8 |
| eb516_q02_continents_move | 38 | 0.12 | [-0.01, 0.31] | 0.25 | 9.4 |
| eb516_q03_antibiotics_kill_viruses | 38 | 0.11 | [-0.03, 0.30] | 0.16 | 25.6 |
| eb516_q04_oxygen_from_plants | 38 | 0.32 | [0.07, 0.62] | 0.40 | 5.2 |
| eb516_q05_lasers_sound_waves | 38 | -0.03 | [-0.19, 0.13] | -0.06 | 46.1 |
| eb516_q06_population_over_10bn | 38 | -0.02 | [-0.23, 0.16] | -0.03 | 48.4 |
| eb516_q08_humans_evolved | 38 | 0.12 | [0.01, 0.23] | 0.36 | 25.1 |
| eb516_q09_climate_natural_cycles | 38 | -0.05 | [-0.77, 0.72] | -0.02 | 23.5 |
| eb516_q10_cancer_cure_hidden | 38 | 0.12 | [-0.01, 0.24] | 0.32 | 36.3 |
| eb516_q11_viruses_made_in_labs | 38 | 0.13 | [0.01, 0.24] | 0.31 | 39.7 |
| eb522_q1_antibiotics_kill_viruses | 27 | -0.03 | [-0.35, 0.24] | -0.04 | 32.3 |
| eb522_q2_antibiotics_colds | 27 | 0.05 | [-0.15, 0.19] | 0.11 | 20.9 |
| eb522_q3_unnecessary_use_ineffective | 27 | 0.11 | [0.02, 0.26] | 0.32 | 8.6 |
| eb522_q4_side_effects | 27 | 0.10 | [-0.24, 0.41] | 0.11 | 17.4 |
| gm_q1_largest_refugee_share_country | 7 | -0.75 | [-2.49, 0.52] | -0.52 | 24.4 |
| gm_q2_share_fled_to_high_income_2021 | 7 | -0.45 | [-1.37, 1.12] | -0.47 | 18.6 |
| gm_q3_refugees_four_middle_income_hosts_2022 | 7 | -0.60 | [-1.10, 1.99] | -0.53 | 28.9 |
| gm_q4_unhcr_funding_change | 7 | -0.22 | [-1.61, 5.02] | -0.11 | 24.0 |
| gm_q5_share_in_exile_over_four_years | 7 | 0.17 | [-0.45, 2.31] | 0.19 | 47.4 |
| gm_q6_refugees_world_total_2022 | 7 | -0.05 | [-1.91, 1.79] | -0.03 | 16.0 |
| gm_q7_west_europe_refugee_spending | 7 | 0.79 | [-0.23, 1.95] | 0.61 | 57.0 |
| gm_q8_syrian_refugees_cannot_afford_basics | 7 | -0.64 | [-1.44, 0.85] | -0.46 | 51.1 |
| gm_q9_un_spending_per_refugee_per_day | 7 | -0.05 | [-0.76, 0.97] | -0.07 | 11.4 |
| homicide_trend | 30 | 0.41 | [0.09, 0.74] | 0.40 | 21.8 |
| pooled (item FE) | 972 | 0.09 | [0.04, 0.14] | | |

### Memorization check (memory_check vs real share correct)

| scope | cells | within 2 pts | within 5 pts | corr |
|---|---|---|---|---|
| pooled | 972 | 8% | 17% | 0.13 |
| climate_attitudes_nber30265 | 280 | 5% | 15% | 0.10 |
| eb104_volume_a | 111 | 5% | 11% | 0.19 |
| eb516_volume_a | 380 | 9% | 21% | 0.06 |
| eb522_volume_a | 108 | 15% | 28% | 0.57 |
| gapminder_refugee_2023_report | 63 | 0% | 5% | -0.24 |
| ipsos_homicide_2024 | 30 | 3% | 7% | 0.20 |

## qwen3.8-27b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 4860 | 100% | 0% | 0% | 0% | 0% |
| official | 4860 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 4860 | 99% | 0% | 0% | 0% | 1% |
| memory_check | 4860 | 100% | 0% | 0% | 0% | 0% |

### Accuracy of the model's own answer (modal option in the truth set)

| scope | cells | plain accuracy | official accuracy |
|---|---|---|---|
| pooled | 972 | 96% | 91% |
| climate_attitudes_nber30265 | 280 | 100% | 100% |
| eb104_volume_a | 111 | 75% | 67% |
| eb516_volume_a | 380 | 100% | 90% |
| eb522_volume_a | 108 | 100% | 100% |
| gapminder_refugee_2023_report | 63 | 89% | 86% |
| ipsos_homicide_2024 | 30 | 83% | 83% |

### Inheritance where a public majority (> 50%) is wrong, plain prompt

| scope | rows | sides with public majority | sides with truth | other |
|---|---|---|---|---|
| pooled | 146 | 3% | 95% | 2% |
| climate_attitudes_nber30265 | 51 | 0% | 100% | 0% |
| eb104_volume_a | 3 | 67% | 33% | 0% |
| eb516_volume_a | 31 | 0% | 100% | 0% |
| eb522_volume_a | 5 | 0% | 100% | 0% |
| gapminder_refugee_2023_report | 36 | 6% | 92% | 3% |
| ipsos_homicide_2024 | 20 | 0% | 90% | 10% |

### Flattening: logit(M_public) on logit(share correct) across countries

| item | countries | slope | 95% CI | corr | mean abs(M_public - share correct) |
|---|---|---|---|---|---|
| clim_cc_real_anthropogenic | 20 | 0.13 | [-0.25, 0.49] | 0.14 | 8.6 |
| clim_droughts_likely | 20 | -0.01 | [-0.54, 0.52] | -0.01 | 4.4 |
| clim_gas_co2_ghg | 20 | 0.18 | [-0.14, 0.61] | 0.26 | 13.6 |
| clim_gas_hydrogen_not_ghg | 20 | 0.21 | [-0.23, 0.52] | 0.27 | 9.2 |
| clim_gas_methane_ghg | 20 | 0.12 | [-0.25, 0.42] | 0.16 | 32.5 |
| clim_gas_particulate_not_ghg | 20 | 0.20 | [-0.24, 0.59] | 0.18 | 19.4 |
| clim_halving_insufficient | 20 | -0.09 | [-0.33, 0.11] | -0.16 | 32.5 |
| clim_rank_food_beef_highest | 20 | 0.02 | [-0.16, 0.21] | 0.04 | 14.1 |
| clim_rank_power_nuclear_lowest | 20 | 0.99 | [0.07, 1.77] | 0.44 | 24.3 |
| clim_rank_region_percapita_us_highest | 20 | -0.30 | [-0.98, 0.41] | -0.24 | 25.5 |
| clim_rank_region_total_china_highest | 20 | -0.79 | [-1.48, 0.08] | -0.42 | 23.3 |
| clim_rank_transport_plane_highest | 20 | 0.06 | [-0.28, 0.46] | 0.08 | 45.6 |
| clim_sea_level_likely | 20 | 0.08 | [-0.00, 0.23] | 0.33 | 12.6 |
| clim_volcanic_unlikely | 20 | -0.96 | [-1.99, 0.21] | -0.36 | 34.8 |
| eb104_sd20a1_euro_area_20_members | 37 | 0.07 | [-1.39, 1.89] | 0.01 | 25.8 |
| eb104_sd20a2_meps_directly_elected | 37 | 0.05 | [-0.11, 0.20] | 0.10 | 16.0 |
| eb104_sd20a3_switzerland_member | 37 | 0.34 | [-0.09, 0.83] | 0.32 | 25.8 |
| eb516_q01_humans_dinosaurs | 38 | -0.07 | [-0.25, 0.17] | -0.10 | 32.3 |
| eb516_q02_continents_move | 38 | 0.16 | [-0.03, 0.42] | 0.22 | 9.8 |
| eb516_q03_antibiotics_kill_viruses | 38 | -0.04 | [-0.12, 0.05] | -0.13 | 33.4 |
| eb516_q04_oxygen_from_plants | 38 | 0.08 | [-0.23, 0.70] | 0.08 | 7.2 |
| eb516_q05_lasers_sound_waves | 38 | -0.00 | [-0.00, 0.00] | -0.00 | 58.0 |
| eb516_q06_population_over_10bn | 38 | -0.28 | [-1.60, 1.23] | -0.07 | 52.8 |
| eb516_q08_humans_evolved | 38 | 0.04 | [-0.24, 0.42] | 0.05 | 20.9 |
| eb516_q09_climate_natural_cycles | 38 | 0.26 | [0.06, 0.56] | 0.36 | 23.2 |
| eb516_q10_cancer_cure_hidden | 38 | 0.40 | [0.25, 0.53] | 0.67 | 37.7 |
| eb516_q11_viruses_made_in_labs | 38 | 0.12 | [-0.11, 0.37] | 0.16 | 45.3 |
| eb522_q1_antibiotics_kill_viruses | 27 | 0.01 | [-0.21, 0.24] | 0.01 | 38.6 |
| eb522_q2_antibiotics_colds | 27 | 0.06 | [-0.08, 0.23] | 0.15 | 22.6 |
| eb522_q3_unnecessary_use_ineffective | 27 | 0.07 | [-0.03, 0.14] | 0.21 | 6.3 |
| eb522_q4_side_effects | 27 | 0.02 | [-0.35, 0.35] | 0.02 | 22.9 |
| gm_q1_largest_refugee_share_country | 7 | 0.19 | [-1.54, 1.92] | 0.10 | 20.7 |
| gm_q2_share_fled_to_high_income_2021 | 7 | 0.03 | [-0.42, 0.79] | 0.05 | 3.6 |
| gm_q3_refugees_four_middle_income_hosts_2022 | 7 | 0.11 | [-9.77, 2.27] | 0.03 | 11.2 |
| gm_q4_unhcr_funding_change | 7 | 0.09 | [-0.43, 1.89] | 0.09 | 8.6 |
| gm_q5_share_in_exile_over_four_years | 7 | -0.47 | [-2.58, 1.14] | -0.27 | 9.0 |
| gm_q6_refugees_world_total_2022 | 7 | 0.25 | [-0.66, 1.98] | 0.16 | 25.0 |
| gm_q7_west_europe_refugee_spending | 7 | 0.02 | [-1.61, 0.97] | 0.02 | 6.0 |
| gm_q8_syrian_refugees_cannot_afford_basics | 7 | -0.02 | [-0.50, 0.23] | -0.04 | 10.3 |
| gm_q9_un_spending_per_refugee_per_day | 7 | 0.61 | [-0.13, 1.84] | 0.56 | 7.9 |
| homicide_trend | 30 | -0.01 | [-0.41, 0.41] | -0.01 | 34.8 |
| pooled (item FE) | 972 | 0.07 | [0.00, 0.15] | | |

### Memorization check (memory_check vs real share correct)

| scope | cells | within 2 pts | within 5 pts | corr |
|---|---|---|---|---|
| pooled | 972 | 7% | 19% | 0.48 |
| climate_attitudes_nber30265 | 280 | 7% | 23% | 0.34 |
| eb104_volume_a | 111 | 6% | 13% | 0.61 |
| eb516_volume_a | 380 | 8% | 17% | 0.14 |
| eb522_volume_a | 108 | 8% | 26% | 0.43 |
| gapminder_refugee_2023_report | 63 | 5% | 16% | 0.11 |
| ipsos_homicide_2024 | 30 | 3% | 20% | 0.35 |

