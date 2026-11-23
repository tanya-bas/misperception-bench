# Preliminary v0 results (2026-11-22)

Raw replies for the first three local model runs, on the v0 dataset (git tag `v0`: Ipsos Perils
of Perception 2024, 90 country-item pairs, 3 percent items x 30 countries). `results.jsonl` here
is a frozen copy of `results/results.jsonl` after the runs finished; the live file stays gitignored.

| model_id | repo | thinking | temperature / top_p | max_tokens | mean latency per call | tokens/s (median) |
|---|---|---|---|---|---|---|
| qwen3.5-9b | mlx-community/Qwen3.5-9B-4bit | enable_thinking=false | 0.7 / 0.8 | 64 | 0.11 s | 171 |
| qwen3.8-27b | mlx-community/Qwen3.8-27B-4bit | enable_thinking=false | 0.7 / 0.8 | 64 | 0.39 s | 55 |
| gpt-oss-20b | mlx-community/gpt-oss-20b-MXFP4-Q4 | reasoning_effort=low (cannot be disabled) | 1.0 / 1.0 | 512 | 0.44 s | 255 |

Design: 4 prompt types (plain, official, public_guess, memory_check; templates in `prompts/`),
5 samples per cell (MLX seed 1000 + sample index), 90 pairs, so 1,800 cells per model and 5,400
rows in total. Hardware: Apple M4 Max, 64 GB, mlx-lm 0.32.2, one model loaded at a time.
Latencies are means over all 1,800 rows of each model (batched generation; per-row latency is the
batch time divided by batch size).

Parsing: rows were re-parsed with `scripts/reparse_results.py` after the 2026-11-22 parser change
that folds typographic apostrophes and classifies declines ("I'm sorry, but I don't have that
specific figure") as `refusal` instead of `unparseable`. Status counts after re-parsing:
qwen3.5-9b 1,800 ok; qwen3.8-27b 1,800 ok; gpt-oss-20b 1,666 ok, 124 refusal (112 of them on
memory_check), 9 unparseable (empty replies), 1 truncated.

Noise: gpt-oss-20b's public_guess cells vary more across the 5 samples than the Qwen models'
(within-cell SD about 9 points on immigrant share vs 4 for qwen3.5-9b), so its cell medians are
less stable; see the noise-floor tables in `results/metrics.md`. A larger sample count for that
prompt is a planned follow-up.

Derived files: `results/metrics.md` (all hypothesis metrics, `metrics.py`), `results/<model>_pairs.md`
(per-pair medians, `scripts/pairs_table.py`).
