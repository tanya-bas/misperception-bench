# Numeric track metrics

Source: `results/v1/results.jsonl` (280 pairs with truth, items: wealth_top1, immigrant_share, muslim_share, deaths_cancer, deaths_cardiovascular, deaths_hiv_sti, deaths_neurological, deaths_suicide, deaths_violence; public_guess variant v1). Cell value = median of parsed samples. Log-odds clip = 0.0005.

Flattening ("flatten slope" columns): slope of logit(M_public) on logit(H) across countries. A slope below 1 means the model's simulated public varies less across countries than the real public. The H1a variance ratio can exceed 1 even when answers are flat, because the model tracks a truth that varies more across countries than human guesses do; the slope is the direct flattening measure. The pooled slope demeans within item (item fixed effects).

## Summary

| model | VR wealth | VR immigrants | VR Muslim | flatten slope wealth | flatten slope immigrants | flatten slope Muslim | flatten slope pooled | lambda ipsos_2020 | flatten pooled ipsos_2020 | lambda ipsos_2024 | flatten pooled ipsos_2024 | lambda | model slope | human slope | abs(M_official - T) | abs(M_public - H) | s(M_plain) | memory within 2 | entropy plain (bits) | bimodal plain | bimodal public |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | 0.54 | 1.16 | 1.29 | -0.07 | 0.54 | 0.94 | 0.84 | 0.46 | 0.96 | 0.50 | 0.79 | 0.46 | 0.62 | 0.26 | 4.1 | 8.8 | 0.16 | 22% | n/a | n/a | n/a |
| qwen3.5-9b | 0.22 | 1.50 | 1.70 | -0.21 | 0.75 | 1.12 | 0.83 | 0.34 | 0.51 | 0.30 | 0.95 | 0.33 | 0.76 | 0.26 | 6.6 | 10.1 | 0.27 | 11% | n/a | n/a | n/a |
| qwen3.8-27b | 0.15 | 2.65 | 3.32 | -0.05 | 1.15 | 1.57 | 1.21 | 0.10 | 0.75 | -0.05 | 1.37 | 0.07 | 0.96 | 0.26 | 3.8 | 9.3 | -0.00 | 14% | n/a | n/a | n/a |

## gpt-oss-20b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 1400 | 99% | 1% | 0% | 0% | 0% |
| official | 1400 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 1400 | 100% | 0% | 0% | 0% | 0% |
| memory_check | 1400 | 90% | 9% | 1% | 0% | 0% |

### Noise floor (percent points)

| item | prompt | mean within-cell SD | between-country SD of medians | ratio |
|---|---|---|---|---|
| wealth_top1 | plain | 11.69 | 7.43 | 1.57 |
| wealth_top1 | public_guess | 11.46 | 6.04 | 1.90 |
| immigrant_share | plain | 4.18 | 8.04 | 0.52 |
| immigrant_share | public_guess | 8.91 | 6.12 | 1.46 |
| muslim_share | plain | 3.50 | 24.53 | 0.14 |
| muslim_share | public_guess | 9.77 | 18.85 | 0.52 |
| deaths_cancer | plain | 6.45 | 6.38 | 1.01 |
| deaths_cancer | public_guess | 8.34 | 7.04 | 1.18 |
| deaths_cardiovascular | plain | 11.62 | 5.59 | 2.08 |
| deaths_cardiovascular | public_guess | 10.51 | 5.11 | 2.06 |
| deaths_hiv_sti | plain | 1.80 | 5.25 | 0.34 |
| deaths_hiv_sti | public_guess | 8.81 | 5.03 | 1.75 |
| deaths_neurological | plain | 5.85 | 2.69 | 2.17 |
| deaths_neurological | public_guess | 7.62 | 4.65 | 1.64 |
| deaths_suicide | plain | 3.77 | 2.23 | 1.69 |
| deaths_suicide | public_guess | 4.29 | 3.73 | 1.15 |
| deaths_violence | plain | 3.12 | 2.90 | 1.07 |
| deaths_violence | public_guess | 7.11 | 7.10 | 1.00 |

### Coverage (pairs with at least one parsed sample)

| item | plain | official | public_guess | memory_check |
|---|---|---|---|---|
| wealth_top1 | 30 | 30 | 30 | 30 |
| immigrant_share | 30 | 30 | 30 | 30 |
| muslim_share | 30 | 30 | 30 | 30 |
| deaths_cancer | 32 | 32 | 32 | 32 |
| deaths_cardiovascular | 32 | 32 | 32 | 32 |
| deaths_hiv_sti | 31 | 31 | 31 | 31 |
| deaths_neurological | 32 | 32 | 32 | 32 |
| deaths_suicide | 32 | 32 | 32 | 32 |
| deaths_violence | 31 | 31 | 31 | 31 |

### H1a variance ratio, logit scale (model public_guess vs human H)

| item | countries | VR | 95% CI | corr(M_public, H) |
|---|---|---|---|---|
| wealth_top1 | 30 | 0.54 | [0.21, 1.64] | -0.10 |
| immigrant_share | 30 | 1.16 | [0.41, 2.55] | 0.50 |
| muslim_share | 30 | 1.29 | [0.91, 1.81] | 0.83 |
| deaths_cancer | 32 | 2.57 | [1.51, 3.81] | 0.84 |
| deaths_cardiovascular | 32 | 0.66 | [0.31, 1.30] | 0.14 |
| deaths_hiv_sti | 31 | 3.50 | [1.71, 5.90] | 0.67 |
| deaths_neurological | 32 | 6.58 | [3.24, 13.48] | -0.01 |
| deaths_suicide | 32 | 19.37 | [8.89, 44.42] | -0.07 |
| deaths_violence | 31 | 6.18 | [2.66, 11.55] | 0.57 |

### Flattening: slope of logit(M_public) on logit(H) across countries

Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).

| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |
|---|---|---|---|---|---|---|---|
| wealth_top1 | 30 | -0.07 | [-0.39, 0.23] | -0.78 | -0.10 | 6.0 | 8.6 |
| immigrant_share | 30 | 0.54 | [0.22, 1.02] | -0.97 | 0.50 | 6.1 | 7.7 |
| muslim_share | 30 | 0.94 | [0.62, 1.11] | -0.90 | 0.83 | 18.8 | 19.6 |
| deaths_cancer | 32 | 1.35 | [0.98, 1.67] | 0.97 | 0.84 | 7.0 | 3.8 |
| deaths_cardiovascular | 32 | 0.11 | [-0.11, 0.35] | -0.37 | 0.14 | 5.1 | 2.5 |
| deaths_hiv_sti | 31 | 1.25 | [0.57, 1.76] | 0.53 | 0.67 | 5.0 | 1.8 |
| deaths_neurological | 32 | -0.03 | [-0.74, 0.86] | -2.21 | -0.01 | 4.7 | 1.0 |
| deaths_suicide | 32 | -0.31 | [-1.90, 1.13] | -4.48 | -0.07 | 3.7 | 1.5 |
| deaths_violence | 31 | 1.43 | [0.63, 2.29] | 0.11 | 0.57 | 7.1 | 3.0 |
| pooled (item FE) | 280 | 0.84 | [0.61, 0.99] | 0 | 0.56 | | |
| pooled ipsos_2020 (item FE) | 190 | 0.96 | [0.62, 1.28] | 0 | | | |
| pooled ipsos_2024 (item FE) | 90 | 0.79 | [0.45, 0.97] | 0 | | | |

### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale

| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |
|---|---|---|---|---|---|---|---|
| pooled | 280 | 0.46 | [0.40, 0.51] | 0.62 | -0.50 | 0.26 | -1.16 |
| wave:ipsos_2020 | 190 | 0.46 | [0.41, 0.51] | 0.60 | -0.62 | 0.15 | -1.94 |
| wave:ipsos_2024 | 90 | 0.50 | [0.32, 0.65] | 0.68 | -0.32 | 0.36 | -0.16 |
| wealth_top1 | 30 | 0.55 | [0.29, 0.87] | -0.02 | -0.64 | -0.07 | -0.38 |
| immigrant_share | 30 | 0.58 | [0.32, 0.72] | 0.52 | -1.10 | 0.21 | -0.68 |
| muslim_share | 30 | 0.48 | [0.23, 0.84] | 0.68 | -0.25 | 0.37 | -0.14 |
| deaths_cancer | 32 | 0.41 | [0.12, 0.87] | 0.79 | -0.38 | 0.54 | -1.11 |
| deaths_cardiovascular | 32 | 0.66 | [0.28, 0.95] | 0.04 | -0.55 | 0.25 | -1.95 |
| deaths_hiv_sti | 31 | 0.81 | [0.54, 1.23] | 0.34 | -2.15 | 0.20 | -1.70 |
| deaths_neurological | 32 | 0.94 | [0.78, 1.08] | 0.14 | -2.20 | 0.11 | -2.55 |
| deaths_suicide | 32 | 1.18 | [0.82, 1.58] | -0.16 | -4.28 | 0.18 | -1.78 |
| deaths_violence | 31 | 0.61 | [0.43, 0.85] | 0.50 | -1.19 | 0.17 | -1.48 |

### H3 knowing vs saying (percent points)

| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |
|---|---|---|---|---|---|---|
| pooled | 280 | 4.1 | 8.8 | 4.3 | 9.4 | 0.16 |
| wave:ipsos_2020 | 190 | 3.7 | 8.3 | 3.8 | 8.2 | 0.18 |
| wave:ipsos_2024 | 90 | 5.1 | 9.9 | 5.4 | 11.9 | 0.11 |
| wealth_top1 | 30 | 9.3 | 12.6 | 10.9 | 10.9 | 0.44 |
| immigrant_share | 30 | 4.1 | 8.2 | 3.6 | 13.3 | -0.02 |
| muslim_share | 30 | 1.9 | 9.0 | 1.7 | 11.5 | 0.08 |
| deaths_cancer | 32 | 8.1 | 5.9 | 4.0 | 6.8 | 0.32 |
| deaths_cardiovascular | 32 | 6.8 | 24.7 | 9.5 | 25.3 | -0.39 |
| deaths_hiv_sti | 31 | 1.1 | 2.2 | 1.7 | 4.0 | 0.20 |
| deaths_neurological | 32 | 3.8 | 6.4 | 3.8 | 2.4 | 0.93 |
| deaths_suicide | 32 | 1.0 | 5.0 | 1.9 | 4.6 | 0.20 |
| deaths_violence | 31 | 0.9 | 5.5 | 1.6 | 5.7 | 0.18 |

### Memorization check (memory_check prompt vs Ipsos H)

| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |
|---|---|---|---|---|
| pooled | 280 | 22% | 45% | 0.56 |
| wave:ipsos_2020 | 190 | 25% | 50% | 0.58 |
| wave:ipsos_2024 | 90 | 17% | 33% | 0.47 |
| wealth_top1 | 30 | 17% | 27% | -0.26 |
| immigrant_share | 30 | 20% | 43% | 0.09 |
| muslim_share | 30 | 13% | 30% | 0.47 |
| deaths_cancer | 32 | 3% | 22% | 0.38 |
| deaths_cardiovascular | 32 | 0% | 0% | -0.02 |
| deaths_hiv_sti | 31 | 45% | 77% | 0.58 |
| deaths_neurological | 32 | 16% | 47% | 0.32 |
| deaths_suicide | 32 | 50% | 91% | 0.03 |
| deaths_violence | 31 | 39% | 65% | 0.53 |

## qwen3.5-9b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 1400 | 100% | 0% | 0% | 0% | 0% |
| official | 1400 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 1400 | 100% | 0% | 0% | 0% | 0% |
| memory_check | 1400 | 100% | 0% | 0% | 0% | 0% |

### Noise floor (percent points)

| item | prompt | mean within-cell SD | between-country SD of medians | ratio |
|---|---|---|---|---|
| wealth_top1 | plain | 7.68 | 7.30 | 1.05 |
| wealth_top1 | public_guess | 7.19 | 4.17 | 1.72 |
| immigrant_share | plain | 2.19 | 10.10 | 0.22 |
| immigrant_share | public_guess | 3.99 | 5.76 | 0.69 |
| muslim_share | plain | 3.95 | 26.18 | 0.15 |
| muslim_share | public_guess | 4.96 | 22.71 | 0.22 |
| deaths_cancer | plain | 2.12 | 3.41 | 0.62 |
| deaths_cancer | public_guess | 7.20 | 6.38 | 1.13 |
| deaths_cardiovascular | plain | 2.04 | 1.90 | 1.07 |
| deaths_cardiovascular | public_guess | 6.33 | 4.19 | 1.51 |
| deaths_hiv_sti | plain | 0.65 | 5.36 | 0.12 |
| deaths_hiv_sti | public_guess | 2.49 | 6.67 | 0.37 |
| deaths_neurological | plain | 3.94 | 3.62 | 1.09 |
| deaths_neurological | public_guess | 6.88 | 7.17 | 0.96 |
| deaths_suicide | plain | 2.09 | 2.25 | 0.93 |
| deaths_suicide | public_guess | 5.51 | 3.54 | 1.55 |
| deaths_violence | plain | 3.41 | 7.13 | 0.48 |
| deaths_violence | public_guess | 5.27 | 3.07 | 1.72 |

### Coverage (pairs with at least one parsed sample)

| item | plain | official | public_guess | memory_check |
|---|---|---|---|---|
| wealth_top1 | 30 | 30 | 30 | 30 |
| immigrant_share | 30 | 30 | 30 | 30 |
| muslim_share | 30 | 30 | 30 | 30 |
| deaths_cancer | 32 | 32 | 32 | 32 |
| deaths_cardiovascular | 32 | 32 | 32 | 32 |
| deaths_hiv_sti | 31 | 31 | 31 | 31 |
| deaths_neurological | 32 | 32 | 32 | 32 |
| deaths_suicide | 32 | 32 | 32 | 32 |
| deaths_violence | 31 | 31 | 31 | 31 |

### H1a variance ratio, logit scale (model public_guess vs human H)

| item | countries | VR | 95% CI | corr(M_public, H) |
|---|---|---|---|---|
| wealth_top1 | 30 | 0.22 | [0.12, 0.58] | -0.44 |
| immigrant_share | 30 | 1.50 | [0.97, 2.81] | 0.61 |
| muslim_share | 30 | 1.70 | [0.80, 2.47] | 0.86 |
| deaths_cancer | 32 | 0.96 | [0.45, 1.65] | 0.08 |
| deaths_cardiovascular | 32 | 0.43 | [0.21, 0.89] | 0.20 |
| deaths_hiv_sti | 31 | 3.44 | [1.20, 6.92] | 0.49 |
| deaths_neurological | 32 | 17.92 | [8.88, 35.83] | 0.54 |
| deaths_suicide | 32 | 9.95 | [5.13, 21.93] | 0.03 |
| deaths_violence | 31 | 2.31 | [1.13, 4.39] | 0.15 |

### Flattening: slope of logit(M_public) on logit(H) across countries

Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).

| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |
|---|---|---|---|---|---|---|---|
| wealth_top1 | 30 | -0.21 | [-0.33, 0.01] | -0.72 | -0.44 | 4.2 | 8.6 |
| immigrant_share | 30 | 0.75 | [0.39, 1.06] | -1.09 | 0.61 | 5.8 | 7.7 |
| muslim_share | 30 | 1.12 | [0.53, 1.37] | -0.76 | 0.86 | 22.7 | 19.6 |
| deaths_cancer | 32 | 0.08 | [-0.32, 0.42] | -0.90 | 0.08 | 6.4 | 3.8 |
| deaths_cardiovascular | 32 | 0.13 | [-0.08, 0.37] | -0.17 | 0.20 | 4.2 | 2.5 |
| deaths_hiv_sti | 31 | 0.91 | [0.08, 1.92] | -0.51 | 0.49 | 6.7 | 1.8 |
| deaths_neurological | 32 | 2.27 | [1.12, 3.74] | 4.43 | 0.54 | 7.2 | 1.0 |
| deaths_suicide | 32 | 0.09 | [-1.36, 1.16] | -2.63 | 0.03 | 3.5 | 1.5 |
| deaths_violence | 31 | 0.23 | [-0.22, 0.72] | -2.56 | 0.15 | 3.1 | 3.0 |
| pooled (item FE) | 280 | 0.83 | [0.45, 1.09] | 0 | 0.57 | | |
| pooled ipsos_2020 (item FE) | 190 | 0.51 | [0.19, 0.87] | 0 | | | |
| pooled ipsos_2024 (item FE) | 90 | 0.95 | [0.41, 1.21] | 0 | | | |

### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale

| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |
|---|---|---|---|---|---|---|---|
| pooled | 280 | 0.33 | [0.25, 0.42] | 0.76 | 0.22 | 0.26 | -1.16 |
| wave:ipsos_2020 | 190 | 0.34 | [0.25, 0.44] | 0.72 | -0.02 | 0.15 | -1.94 |
| wave:ipsos_2024 | 90 | 0.30 | [0.06, 0.51] | 0.81 | 0.55 | 0.36 | -0.16 |
| wealth_top1 | 30 | 0.40 | [0.13, 0.76] | 0.02 | 0.34 | -0.07 | -0.38 |
| immigrant_share | 30 | 0.08 | [-0.29, 0.73] | 0.98 | 0.28 | 0.21 | -0.68 |
| muslim_share | 30 | 0.42 | [0.17, 0.78] | 0.71 | 0.36 | 0.37 | -0.14 |
| deaths_cancer | 32 | 0.81 | [0.57, 1.12] | 0.33 | -0.81 | 0.54 | -1.11 |
| deaths_cardiovascular | 32 | 0.85 | [0.63, 1.05] | 0.03 | -0.65 | 0.25 | -1.95 |
| deaths_hiv_sti | 31 | 0.39 | [-0.02, 1.02] | 0.69 | -2.22 | 0.20 | -1.70 |
| deaths_neurological | 32 | 0.88 | [0.64, 1.01] | 0.21 | -1.52 | 0.11 | -2.55 |
| deaths_suicide | 32 | 1.07 | [0.81, 1.37] | -0.05 | -2.16 | 0.18 | -1.78 |
| deaths_violence | 31 | 0.44 | [0.31, 0.57] | 0.65 | 0.72 | 0.17 | -1.48 |

### H3 knowing vs saying (percent points)

| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |
|---|---|---|---|---|---|---|
| pooled | 280 | 6.6 | 10.1 | 8.3 | 9.9 | 0.27 |
| wave:ipsos_2020 | 190 | 4.5 | 9.8 | 5.9 | 8.8 | 0.19 |
| wave:ipsos_2024 | 90 | 11.1 | 10.8 | 13.3 | 12.3 | 0.41 |
| wealth_top1 | 30 | 22.5 | 11.3 | 28.3 | 16.9 | 1.62 |
| immigrant_share | 30 | 4.1 | 11.2 | 4.7 | 9.3 | 0.27 |
| muslim_share | 30 | 6.9 | 10.0 | 6.9 | 10.7 | 0.17 |
| deaths_cancer | 32 | 5.2 | 11.9 | 4.6 | 8.3 | 0.18 |
| deaths_cardiovascular | 32 | 7.1 | 28.3 | 7.5 | 23.0 | -0.21 |
| deaths_hiv_sti | 31 | 0.4 | 2.6 | 0.9 | 5.1 | -0.01 |
| deaths_neurological | 32 | 5.0 | 8.1 | 5.2 | 6.1 | 0.09 |
| deaths_suicide | 32 | 6.6 | 3.3 | 11.2 | 5.7 | 2.08 |
| deaths_violence | 31 | 2.5 | 4.2 | 6.0 | 4.2 | 0.57 |

### Memorization check (memory_check prompt vs Ipsos H)

| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |
|---|---|---|---|---|
| pooled | 280 | 11% | 20% | 0.47 |
| wave:ipsos_2020 | 190 | 9% | 17% | 0.45 |
| wave:ipsos_2024 | 90 | 14% | 28% | 0.75 |
| wealth_top1 | 30 | 7% | 23% | -0.14 |
| immigrant_share | 30 | 20% | 37% | 0.05 |
| muslim_share | 30 | 17% | 23% | 0.83 |
| deaths_cancer | 32 | 0% | 0% | -0.03 |
| deaths_cardiovascular | 32 | 0% | 0% | 0.13 |
| deaths_hiv_sti | 31 | 19% | 29% | 0.18 |
| deaths_neurological | 32 | 16% | 19% | 0.31 |
| deaths_suicide | 32 | 9% | 28% | -0.16 |
| deaths_violence | 31 | 10% | 26% | 0.24 |

## qwen3.8-27b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 1400 | 100% | 0% | 0% | 0% | 0% |
| official | 1400 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 1400 | 100% | 0% | 0% | 0% | 0% |
| memory_check | 1400 | 100% | 0% | 0% | 0% | 0% |

### Noise floor (percent points)

| item | prompt | mean within-cell SD | between-country SD of medians | ratio |
|---|---|---|---|---|
| wealth_top1 | plain | 7.45 | 10.71 | 0.70 |
| wealth_top1 | public_guess | 4.96 | 2.15 | 2.31 |
| immigrant_share | plain | 1.42 | 8.59 | 0.17 |
| immigrant_share | public_guess | 4.36 | 9.90 | 0.44 |
| muslim_share | plain | 0.32 | 24.98 | 0.01 |
| muslim_share | public_guess | 0.95 | 24.56 | 0.04 |
| deaths_cancer | plain | 2.01 | 6.40 | 0.31 |
| deaths_cancer | public_guess | 1.84 | 6.54 | 0.28 |
| deaths_cardiovascular | plain | 1.67 | 8.83 | 0.19 |
| deaths_cardiovascular | public_guess | 2.77 | 7.51 | 0.37 |
| deaths_hiv_sti | plain | 0.38 | 2.68 | 0.14 |
| deaths_hiv_sti | public_guess | 1.15 | 1.73 | 0.67 |
| deaths_neurological | plain | 2.59 | 3.17 | 0.82 |
| deaths_neurological | public_guess | 1.73 | 1.48 | 1.17 |
| deaths_suicide | plain | 0.95 | 2.11 | 0.45 |
| deaths_suicide | public_guess | 1.49 | 1.06 | 1.40 |
| deaths_violence | plain | 1.00 | 2.83 | 0.35 |
| deaths_violence | public_guess | 2.66 | 3.03 | 0.88 |

### Coverage (pairs with at least one parsed sample)

| item | plain | official | public_guess | memory_check |
|---|---|---|---|---|
| wealth_top1 | 30 | 30 | 30 | 30 |
| immigrant_share | 30 | 30 | 30 | 30 |
| muslim_share | 30 | 30 | 30 | 30 |
| deaths_cancer | 32 | 32 | 32 | 32 |
| deaths_cardiovascular | 32 | 32 | 32 | 32 |
| deaths_hiv_sti | 31 | 31 | 31 | 31 |
| deaths_neurological | 32 | 32 | 32 | 32 |
| deaths_suicide | 32 | 32 | 32 | 32 |
| deaths_violence | 31 | 31 | 31 | 31 |

### H1a variance ratio, logit scale (model public_guess vs human H)

| item | countries | VR | 95% CI | corr(M_public, H) |
|---|---|---|---|---|
| wealth_top1 | 30 | 0.15 | [0.06, 0.46] | -0.12 |
| immigrant_share | 30 | 2.65 | [1.69, 5.39] | 0.71 |
| muslim_share | 30 | 3.32 | [1.70, 5.66] | 0.86 |
| deaths_cancer | 32 | 2.30 | [1.49, 3.27] | 0.80 |
| deaths_cardiovascular | 32 | 1.55 | [0.51, 3.14] | 0.30 |
| deaths_hiv_sti | 31 | 2.09 | [0.69, 4.16] | 0.47 |
| deaths_neurological | 32 | 1.27 | [0.00, 2.82] | 0.22 |
| deaths_suicide | 32 | 5.32 | [2.05, 12.19] | 0.06 |
| deaths_violence | 31 | 3.69 | [1.94, 6.35] | 0.52 |

### Flattening: slope of logit(M_public) on logit(H) across countries

Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).

| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |
|---|---|---|---|---|---|---|---|
| wealth_top1 | 30 | -0.05 | [-0.17, 0.09] | -1.48 | -0.12 | 2.2 | 8.6 |
| immigrant_share | 30 | 1.15 | [0.92, 1.53] | -0.40 | 0.71 | 9.9 | 7.7 |
| muslim_share | 30 | 1.57 | [0.89, 2.09] | -0.50 | 0.86 | 24.6 | 19.6 |
| deaths_cancer | 32 | 1.21 | [0.86, 1.57] | 0.69 | 0.80 | 6.5 | 3.8 |
| deaths_cardiovascular | 32 | 0.37 | [-0.01, 0.81] | -0.06 | 0.30 | 7.5 | 2.5 |
| deaths_hiv_sti | 31 | 0.68 | [0.07, 1.34] | -2.20 | 0.47 | 1.7 | 1.8 |
| deaths_neurological | 32 | 0.25 | [-0.15, 0.70] | -2.16 | 0.22 | 1.5 | 1.0 |
| deaths_suicide | 32 | 0.14 | [-0.69, 1.17] | -3.61 | 0.06 | 1.1 | 1.5 |
| deaths_violence | 31 | 1.00 | [0.44, 1.58] | -0.98 | 0.52 | 3.0 | 3.0 |
| pooled (item FE) | 280 | 1.21 | [0.75, 1.55] | 0 | 0.71 | | |
| pooled ipsos_2020 (item FE) | 190 | 0.75 | [0.52, 1.02] | 0 | | | |
| pooled ipsos_2024 (item FE) | 90 | 1.37 | [0.79, 1.79] | 0 | | | |

### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale

| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |
|---|---|---|---|---|---|---|---|
| pooled | 280 | 0.07 | [0.02, 0.12] | 0.96 | -0.18 | 0.26 | -1.16 |
| wave:ipsos_2020 | 190 | 0.10 | [0.05, 0.16] | 0.92 | -0.32 | 0.15 | -1.94 |
| wave:ipsos_2024 | 90 | -0.05 | [-0.17, 0.06] | 1.06 | 0.06 | 0.36 | -0.16 |
| wealth_top1 | 30 | -0.04 | [-0.28, 0.13] | 0.61 | 0.02 | -0.07 | -0.38 |
| immigrant_share | 30 | 0.16 | [-0.14, 0.39] | 0.88 | -0.69 | 0.21 | -0.68 |
| muslim_share | 30 | -0.01 | [-0.16, 0.17] | 1.03 | -0.15 | 0.37 | -0.14 |
| deaths_cancer | 32 | 0.49 | [0.15, 0.83] | 0.77 | -0.55 | 0.54 | -1.11 |
| deaths_cardiovascular | 32 | 0.23 | [-0.11, 0.51] | 0.66 | -0.14 | 0.25 | -1.95 |
| deaths_hiv_sti | 31 | 0.29 | [-0.06, 0.79] | 0.79 | -1.50 | 0.20 | -1.70 |
| deaths_neurological | 32 | 0.39 | [0.00, 0.65] | 0.67 | -1.38 | 0.11 | -2.55 |
| deaths_suicide | 32 | 0.60 | [0.09, 1.07] | 0.57 | -1.93 | 0.18 | -1.78 |
| deaths_violence | 31 | 0.17 | [-0.16, 0.48] | 0.85 | -0.33 | 0.17 | -1.48 |

### H3 knowing vs saying (percent points)

| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |
|---|---|---|---|---|---|---|
| pooled | 280 | 3.8 | 9.3 | 3.4 | 10.1 | -0.00 |
| wave:ipsos_2020 | 190 | 2.9 | 6.5 | 2.6 | 8.1 | 0.00 |
| wave:ipsos_2024 | 90 | 5.5 | 15.0 | 5.1 | 14.4 | -0.01 |
| wealth_top1 | 30 | 10.4 | 24.0 | 9.8 | 15.5 | 0.37 |
| immigrant_share | 30 | 5.1 | 9.0 | 4.3 | 14.7 | -0.15 |
| muslim_share | 30 | 1.0 | 11.9 | 1.3 | 13.0 | -0.04 |
| deaths_cancer | 32 | 8.1 | 5.4 | 4.8 | 5.1 | 0.50 |
| deaths_cardiovascular | 32 | 4.7 | 19.6 | 5.6 | 23.5 | -0.13 |
| deaths_hiv_sti | 31 | 0.3 | 3.3 | 0.4 | 4.6 | -0.01 |
| deaths_neurological | 32 | 2.9 | 1.1 | 2.9 | 2.6 | 0.47 |
| deaths_suicide | 32 | 0.7 | 5.3 | 0.7 | 5.9 | -0.05 |
| deaths_violence | 31 | 0.6 | 4.3 | 1.1 | 6.6 | 0.03 |

### Memorization check (memory_check prompt vs Ipsos H)

| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |
|---|---|---|---|---|
| pooled | 280 | 14% | 46% | 0.77 |
| wave:ipsos_2020 | 190 | 11% | 44% | 0.73 |
| wave:ipsos_2024 | 90 | 22% | 51% | 0.80 |
| wealth_top1 | 30 | 17% | 37% | -0.50 |
| immigrant_share | 30 | 37% | 57% | 0.56 |
| muslim_share | 30 | 13% | 60% | 0.90 |
| deaths_cancer | 32 | 12% | 19% | 0.61 |
| deaths_cardiovascular | 32 | 6% | 28% | -0.01 |
| deaths_hiv_sti | 31 | 6% | 32% | 0.28 |
| deaths_neurological | 32 | 16% | 66% | 0.22 |
| deaths_suicide | 32 | 19% | 81% | 0.22 |
| deaths_violence | 31 | 3% | 39% | 0.60 |

