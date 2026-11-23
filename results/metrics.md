# v0 metrics

Source: `results/results.jsonl` (90 pairs with truth). Cell value = median of parsed samples. Log-odds clip = 0.0005.

Flattening ("flatten slope" columns): slope of logit(M_public) on logit(H) across countries. A slope below 1 means the model's simulated public varies less across countries than the real public. The H1a variance ratio can exceed 1 even when answers are flat, because the model tracks a truth that varies more across countries than human guesses do; the slope is the direct flattening measure. The pooled slope demeans within item (item fixed effects).

## Summary

| model | VR wealth | VR immigrants | VR Muslim | flatten slope wealth | flatten slope immigrants | flatten slope Muslim | flatten slope pooled | lambda | model slope | human slope | abs(M_official - T) | abs(M_public - H) | s(M_plain) | memory within 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | 0.68 | 1.24 | 1.84 | -0.34 | 0.67 | 1.12 | 0.93 | 0.58 | 0.64 | 0.36 | 4.9 | 9.8 | 0.14 | 12% |
| qwen3.5-9b | 0.43 | 1.60 | 1.69 | -0.34 | 0.80 | 1.09 | 0.92 | 0.30 | 0.81 | 0.36 | 11.1 | 11.0 | 0.25 | 19% |
| qwen3.8-27b | 0.52 | 2.26 | 3.04 | -0.11 | 0.94 | 1.54 | 1.30 | -0.11 | 1.11 | 0.36 | 5.7 | 14.9 | -0.02 | 19% |

## gpt-oss-20b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 450 | 96% | 4% | 0% | 0% | 0% |
| official | 450 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 450 | 99% | 0% | 0% | 0% | 0% |
| memory_check | 450 | 75% | 24% | 1% | 0% | 0% |

### Noise floor (percent points)

| item | prompt | mean within-cell SD | between-country SD of medians | ratio |
|---|---|---|---|---|
| wealth_top1 | plain | 10.94 | 6.43 | 1.70 |
| wealth_top1 | public_guess | 13.98 | 7.46 | 1.87 |
| immigrant_share | plain | 3.68 | 8.12 | 0.45 |
| immigrant_share | public_guess | 8.83 | 7.33 | 1.20 |
| muslim_share | plain | 5.46 | 24.51 | 0.22 |
| muslim_share | public_guess | 11.56 | 22.85 | 0.51 |

### Coverage (pairs with at least one parsed sample)

| item | plain | official | public_guess | memory_check |
|---|---|---|---|---|
| wealth_top1 | 30 | 30 | 30 | 30 |
| immigrant_share | 30 | 30 | 30 | 30 |
| muslim_share | 30 | 30 | 30 | 30 |

### H1a variance ratio, logit scale (model public_guess vs human H)

| item | countries | VR | 95% CI | corr(M_public, H) |
|---|---|---|---|---|
| wealth_top1 | 30 | 0.68 | [0.44, 1.19] | -0.41 |
| immigrant_share | 30 | 1.24 | [0.64, 2.90] | 0.61 |
| muslim_share | 30 | 1.84 | [1.13, 2.41] | 0.83 |

### Flattening: slope of logit(M_public) on logit(H) across countries

Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).

| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |
|---|---|---|---|---|---|---|---|
| wealth_top1 | 30 | -0.34 | [-0.66, 0.38] | -0.76 | -0.41 | 7.5 | 8.6 |
| immigrant_share | 30 | 0.67 | [0.43, 1.03] | -0.82 | 0.61 | 7.3 | 7.7 |
| muslim_share | 30 | 1.12 | [0.58, 1.36] | -0.58 | 0.83 | 22.8 | 19.6 |
| pooled (item FE) | 90 | 0.93 | [0.40, 1.19] | 0 | 0.72 | | |

### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale

| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |
|---|---|---|---|---|---|---|---|
| pooled | 90 | 0.58 | [0.41, 0.72] | 0.64 | -0.38 | 0.36 | -0.16 |
| wealth_top1 | 30 | 0.53 | [0.27, 0.83] | 0.02 | -0.54 | -0.07 | -0.38 |
| immigrant_share | 30 | 0.63 | [0.38, 0.75] | 0.51 | -1.13 | 0.21 | -0.68 |
| muslim_share | 30 | 0.63 | [0.36, 0.98] | 0.61 | -0.47 | 0.37 | -0.14 |

### H3 knowing vs saying (percent points)

| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |
|---|---|---|---|---|---|---|
| pooled | 90 | 4.9 | 9.8 | 5.3 | 11.5 | 0.14 |
| wealth_top1 | 30 | 9.3 | 13.3 | 10.1 | 10.0 | 0.50 |
| immigrant_share | 30 | 3.8 | 7.2 | 3.5 | 13.4 | -0.05 |
| muslim_share | 30 | 1.7 | 8.7 | 2.3 | 11.2 | 0.04 |

### Memorization check (memory_check prompt vs Ipsos H)

| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |
|---|---|---|---|---|
| pooled | 90 | 12% | 31% | 0.49 |
| wealth_top1 | 30 | 7% | 27% | -0.08 |
| immigrant_share | 30 | 20% | 37% | 0.14 |
| muslim_share | 30 | 10% | 30% | 0.54 |

## qwen3.5-9b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 450 | 100% | 0% | 0% | 0% | 0% |
| official | 450 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 450 | 100% | 0% | 0% | 0% | 0% |
| memory_check | 450 | 100% | 0% | 0% | 0% | 0% |

### Noise floor (percent points)

| item | prompt | mean within-cell SD | between-country SD of medians | ratio |
|---|---|---|---|---|
| wealth_top1 | plain | 9.22 | 9.45 | 0.98 |
| wealth_top1 | public_guess | 7.37 | 5.88 | 1.25 |
| immigrant_share | plain | 2.49 | 10.70 | 0.23 |
| immigrant_share | public_guess | 4.28 | 5.80 | 0.74 |
| muslim_share | plain | 3.87 | 26.24 | 0.15 |
| muslim_share | public_guess | 5.81 | 22.77 | 0.25 |

### Coverage (pairs with at least one parsed sample)

| item | plain | official | public_guess | memory_check |
|---|---|---|---|---|
| wealth_top1 | 30 | 30 | 30 | 30 |
| immigrant_share | 30 | 30 | 30 | 30 |
| muslim_share | 30 | 30 | 30 | 30 |

### H1a variance ratio, logit scale (model public_guess vs human H)

| item | countries | VR | 95% CI | corr(M_public, H) |
|---|---|---|---|---|
| wealth_top1 | 30 | 0.43 | [0.26, 1.14] | -0.51 |
| immigrant_share | 30 | 1.60 | [1.00, 3.38] | 0.63 |
| muslim_share | 30 | 1.69 | [0.76, 2.44] | 0.84 |

### Flattening: slope of logit(M_public) on logit(H) across countries

Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).

| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |
|---|---|---|---|---|---|---|---|
| wealth_top1 | 30 | -0.34 | [-0.44, -0.13] | -0.68 | -0.51 | 5.9 | 8.6 |
| immigrant_share | 30 | 0.80 | [0.56, 1.07] | -1.11 | 0.63 | 5.8 | 7.7 |
| muslim_share | 30 | 1.09 | [0.45, 1.35] | -0.79 | 0.84 | 22.8 | 19.6 |
| pooled (item FE) | 90 | 0.92 | [0.35, 1.18] | 0 | 0.74 | | |

### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale

| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |
|---|---|---|---|---|---|---|---|
| pooled | 90 | 0.30 | [0.08, 0.53] | 0.81 | 0.50 | 0.36 | -0.16 |
| wealth_top1 | 30 | 0.55 | [0.22, 1.00] | -0.11 | 0.19 | -0.07 | -0.38 |
| immigrant_share | 30 | 0.04 | [-0.30, 0.63] | 1.02 | 0.30 | 0.21 | -0.68 |
| muslim_share | 30 | 0.43 | [0.17, 0.79] | 0.71 | 0.32 | 0.37 | -0.14 |

### H3 knowing vs saying (percent points)

| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |
|---|---|---|---|---|---|---|
| pooled | 90 | 11.1 | 11.0 | 12.9 | 12.9 | 0.25 |
| wealth_top1 | 30 | 22.4 | 11.5 | 28.0 | 17.4 | 1.71 |
| immigrant_share | 30 | 4.4 | 11.7 | 4.0 | 9.9 | 0.18 |
| muslim_share | 30 | 6.6 | 9.9 | 6.8 | 11.3 | 0.17 |

### Memorization check (memory_check prompt vs Ipsos H)

| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |
|---|---|---|---|---|
| pooled | 90 | 19% | 37% | 0.78 |
| wealth_top1 | 30 | 20% | 40% | 0.42 |
| immigrant_share | 30 | 20% | 43% | 0.19 |
| muslim_share | 30 | 17% | 27% | 0.85 |

## qwen3.8-27b

### Response quality

| prompt | n | ok | refusal | unparseable | out_of_range | truncated |
|---|---|---|---|---|---|---|
| plain | 450 | 100% | 0% | 0% | 0% | 0% |
| official | 450 | 100% | 0% | 0% | 0% | 0% |
| public_guess | 450 | 100% | 0% | 0% | 0% | 0% |
| memory_check | 450 | 100% | 0% | 0% | 0% | 0% |

### Noise floor (percent points)

| item | prompt | mean within-cell SD | between-country SD of medians | ratio |
|---|---|---|---|---|
| wealth_top1 | plain | 6.83 | 10.53 | 0.65 |
| wealth_top1 | public_guess | 4.85 | 4.69 | 1.04 |
| immigrant_share | plain | 1.22 | 8.41 | 0.14 |
| immigrant_share | public_guess | 4.77 | 8.67 | 0.55 |
| muslim_share | plain | 0.31 | 25.03 | 0.01 |
| muslim_share | public_guess | 0.74 | 24.40 | 0.03 |

### Coverage (pairs with at least one parsed sample)

| item | plain | official | public_guess | memory_check |
|---|---|---|---|---|
| wealth_top1 | 30 | 30 | 30 | 30 |
| immigrant_share | 30 | 30 | 30 | 30 |
| muslim_share | 30 | 30 | 30 | 30 |

### H1a variance ratio, logit scale (model public_guess vs human H)

| item | countries | VR | 95% CI | corr(M_public, H) |
|---|---|---|---|---|
| wealth_top1 | 30 | 0.52 | [0.09, 2.03] | -0.15 |
| immigrant_share | 30 | 2.26 | [1.40, 4.63] | 0.63 |
| muslim_share | 30 | 3.04 | [1.65, 4.84] | 0.88 |

### Flattening: slope of logit(M_public) on logit(H) across countries

Slope below 1 = flattening. Pooled row demeans both sides within item (item fixed effects).

| scope | countries | slope | 95% CI | intercept | corr | SD M_public (pts) | SD H (pts) |
|---|---|---|---|---|---|---|---|
| wealth_top1 | 30 | -0.11 | [-0.37, 0.01] | -1.48 | -0.15 | 4.7 | 8.6 |
| immigrant_share | 30 | 0.94 | [0.63, 1.31] | -0.75 | 0.63 | 8.7 | 7.7 |
| muslim_share | 30 | 1.54 | [0.98, 1.95] | -0.54 | 0.88 | 24.4 | 19.6 |
| pooled (item FE) | 90 | 1.30 | [0.75, 1.70] | 0 | 0.79 | | |

### H2a inheritance (lambda) and H2b compression, plain prompt, logit scale

| scope | pairs | lambda | 95% CI | model slope on logit T | intercept | human slope on logit T | human intercept |
|---|---|---|---|---|---|---|---|
| pooled | 90 | -0.11 | [-0.23, -0.03] | 1.11 | 0.13 | 0.36 | -0.16 |
| wealth_top1 | 30 | -0.03 | [-0.32, 0.20] | 0.61 | 0.07 | -0.07 | -0.38 |
| immigrant_share | 30 | 0.12 | [-0.08, 0.39] | 0.91 | -0.59 | 0.21 | -0.68 |
| muslim_share | 30 | -0.06 | [-0.20, 0.10] | 1.07 | -0.18 | 0.37 | -0.14 |

### H3 knowing vs saying (percent points)

| item | pairs | mean abs(M_official - T) | mean abs(M_public - H) | mean abs(M_plain - T) | mean abs(M_plain - H) | median position s of M_plain on H-T |
|---|---|---|---|---|---|---|
| pooled | 90 | 5.7 | 14.9 | 5.0 | 14.2 | -0.02 |
| wealth_top1 | 30 | 11.9 | 23.6 | 10.0 | 14.8 | 0.36 |
| immigrant_share | 30 | 4.5 | 9.6 | 4.0 | 14.7 | -0.11 |
| muslim_share | 30 | 0.9 | 11.7 | 1.2 | 13.2 | -0.04 |

### Memorization check (memory_check prompt vs Ipsos H)

| item | pairs | within 2 pts | within 5 pts | corr(M_memory, H) |
|---|---|---|---|---|
| pooled | 90 | 19% | 51% | 0.81 |
| wealth_top1 | 30 | 7% | 43% | -0.26 |
| immigrant_share | 30 | 20% | 50% | 0.59 |
| muslim_share | 30 | 30% | 60% | 0.92 |

