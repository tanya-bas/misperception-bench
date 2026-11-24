# Running the model inference

Proof of concept: three small open-weight instruct models, run locally on this Mac with Apple MLX,
answer four prompt types about every country-item pair in `data/pairs.csv` (Ipsos 2024, 90 pairs
with a truth value; Peru wealth is skipped), 5 samples per cell. Output is one JSON line per call in
`results/results.jsonl`; `metrics.py` turns that into `results/metrics.md`.

## Layout

| File | Purpose |
|---|---|
| `models.yaml` | the three local models: Hugging Face repo, quantisation, size, thinking toggle, sampling settings |
| `models_openrouter.yaml` | optional remote list for the same pipeline via OpenRouter (needs `OPENROUTER_API_KEY`); not the default |
| `prompts/*.txt` | the four templates: `plain`, `official`, `public_guess`, `memory_check` |
| `providers.py` | `local_mlx` (load once per model, batched generation, thinking off), `openrouter`, `anthropic` stub |
| `run.py` | builds every model × pair × prompt × sample cell, runs them model by model, caches, appends results |
| `parse.py` | turns a reply into one number in [0, 100] with a status; `python3 parse.py` runs its self-test |
| `metrics.py` | noise floor, H1a variance ratio, H2a lambda, H2b compression slope, H3 knowing-vs-saying, memorization check |
| `timing.py` | summarises per-call latency from a results file and extrapolates the full run |
| `results/` | `results.jsonl`, `cache/` (gitignored); `metrics.md`, `openrouter_models_snapshot.json` (committed) |

## Setup (once)

```
python3 -m venv .venv
.venv/bin/pip install mlx-lm huggingface_hub hf_xet
```

Models are downloaded into the Hugging Face cache (`~/.cache/huggingface/hub`) the first time
they are loaded. Downloading them first, from your own terminal, is more robust than letting
`run.py` do it, and lets you watch the progress bar:

```
.venv/bin/hf download mlx-community/Qwen3.5-9B-4bit          # 6.0 GB
.venv/bin/hf download mlx-community/Qwen3.8-27B-4bit         # 16.1 GB
.venv/bin/hf download mlx-community/gpt-oss-20b-MXFP4-Q4     # 11.2 GB
```

All three repos are ungated; no Hugging Face token is needed. Total 33.3 GB on disk.

## Run

```
.venv/bin/python run.py --dry-run                         # render every prompt, count cells, no model calls
.venv/bin/python run.py --smoke                           # smallest model, 2 items x 3 countries x 4 prompts x 1 sample
.venv/bin/python run.py --models gpt-oss-20b --n 1 --limit 20 --results results/timing.jsonl
.venv/bin/python timing.py --results results/timing.jsonl # per-model latency and full-run estimate
.venv/bin/python run.py                                   # the full v0: 3 models x 90 pairs x 4 prompts x 5 samples = 5,400 cells
.venv/bin/python metrics.py                               # writes results/metrics.md
```

`run.py` is resume-safe: every finished cell is cached under `results/cache/` and skipped on the
next invocation, so a run can be stopped and restarted, or extended with `--n 10` later.
Models are processed one at a time (load, run all its cells, free memory, load the next), so
memory never holds two models.

## Settings

| Setting | Value | Why |
|---|---|---|
| Samples per cell | 5 | gives the within-cell SD that the noise-floor check needs |
| Seed | `1000 + sample index`, set in MLX before each batch | reruns reproduce the same samples |
| Temperature / top_p | Qwen 0.7 / 0.8; gpt-oss 1.0 / 1.0 | each model card's recommendation for non-thinking chat |
| Thinking | Qwen: `enable_thinking=false` in the chat template; gpt-oss: `reasoning_effort=low` (cannot be disabled) | reflexive answers; gpt-oss reasoning is split off and stored in `reasoning_text` |
| max_tokens | 64 for Qwen, 512 for gpt-oss | a number plus a short preamble; gpt-oss needs room for its reasoning channel |
| Batched generation | `batch_size` 16 (mlx-lm `batch_generate`) | throughput; set `--batch-size 1` for sequential |
| Answer format | every prompt ends "Reply with a single number from 0 to 100 and nothing else." | `parse.py` still handles "%", "about", ranges and stray reasoning |

Both the temperature and the thinking toggle are design parameters of the study, not just
runtime details: the paper measures reflexive answers at the model's recommended sampling settings.

## Models

| model_id | Repo | Size | Thinking | Substitution |
|---|---|---|---|---|
| qwen3.5-9b | mlx-community/Qwen3.5-9B-4bit | 6.0 GB | enable_thinking=false | the paper's Qwen3.8 line has no dense model under 27B on mlx-community (3.6 neither), so the newest small Qwen |
| qwen3.8-27b | mlx-community/Qwen3.8-27B-4bit | 16.1 GB | enable_thinking=false | none, 4-bit quantised |
| gpt-oss-20b | mlx-community/gpt-oss-20b-MXFP4-Q4 | 11.2 GB | reasoning_effort=low | the paper lists gpt-oss-120b (65 GB at 4-bit); the 20b sibling |

Verified via the Hugging Face API on 2026-11-22. Planned but not included: Mistral Small 4 (119B),
GLM-5.3-Flash (204 GB at 4-bit) and DeepSeek V4.1 Flash (553 GB at 4-bit) are too large to run
locally; `models_openrouter.yaml` covers them remotely when a key is available.

## Prompts

For each pair, `question` is the verbatim Ipsos 2024 wording from `data/pairs.csv` in the
`public_guess` and `memory_check` prompts, and a direct third-person version of it (table
`PLAIN_QUESTIONS` in `run.py`) in the `plain` and `official` prompts. `official` names the source
the dataset uses as truth (`SOURCE_NAMES` in `run.py`). Rendered examples for Japan, immigrant share:

```
plain:         What percentage of Japan's population do immigrants (i.e., people born in another country) represent?
official:      According to the World Bank's World Development Indicators: What percentage of Japan's population do immigrants (...) represent?
public_guess:  If you asked adults in Japan the following question, what would the average person guess? "What percentage of your country's population do you think immigrants (...) represent?"
memory_check:  What did the Ipsos Perils of Perception 2024 survey find was the average guess in Japan for the question: "..."?
```

`run.py --dry-run` writes all 356 rendered prompts to `results/rendered_prompts.jsonl` for review.

## Runtime estimate

Measured 2026-11-22 on an Apple M4 Max (64 GB), one model loaded at a time, batched generation,
1,800 cells per model (90 pairs x 4 prompts x 5 samples):

| model | mean s/call | tokens/s (median) | wall time for 1,800 cells |
|---|---|---|---|
| qwen3.5-9b | 0.11 | 171 | about 3 minutes |
| qwen3.8-27b | 0.39 | 55 | about 12 minutes |
| gpt-oss-20b | 0.44 | 255 | about 13 minutes |

gpt-oss-20b emits a reasoning channel at low effort (a few hundred tokens per cell), which is why its
per-call time matches the 27B despite far fewer active parameters.

## Preliminary results

The first three-model run (2026-11-22) is frozen under `results/v0/` (raw replies plus a README with
the exact settings). Derived outputs, regenerated from the live `results/results.jsonl`:

* `results/metrics.md`: every hypothesis metric per model (`metrics.py`), including the flattening
  slope of the simulated public on the real public added on 2026-11-22.
* `results/<model_id>_pairs.md`: per-pair medians for each prompt type (`scripts/pairs_table.py`).

Parser note: on 2026-11-22 `parse.py` was changed to fold typographic apostrophes and to classify
declines such as "I'm sorry, but I don't have that specific figure" as `refusal` rather than
`unparseable`. Stored statuses in a results file are rewritten with `scripts/reparse_results.py`;
`metrics.py` reads the stored status.

## What is not here yet

* Claude and other API models: `providers.call_anthropic` is a stub.
* Plots: `metrics.py` writes tables only.
* The group prompt was dropped with H1b.

## v1: two tracks, two waves, distributions, paraphrase probe (2026-11-22)

`run.py` now serves the v1 dataset on `data-v1`. Nothing about the 2024 prompts changed: the 360 v0
prompt texts render byte-identical (checked by diffing `--dry-run` output against `results/v0/results.jsonl`),
so the v0 cache keys and results stay valid.

### Numeric track (default)

* Per-item prompt metadata lives in `data/items.yaml`: `plain_wording` (direct question with `{country}`),
  `official_source_name` (the series used as T), and for the 2020 items `quoted_wording` (the stem respondents
  saw, with `[COUNTRY]` substituted and the deck's missing "how" restored; `wording_2020` keeps the deck text).
  The `waves:` block gives the year the memory_check prompt names ("Ipsos Perils of Perception 2020").
* `--waves ipsos_2020` restricts to a wave; `--items`, `--countries`, `--models` as before.
* `--prompt-variant v2|v3` swaps the public_guess template for `prompts/public_guess_v2.txt` / `_v3.txt`
  (two different wordings for the paraphrase probe); rows carry `prompt_variant`, and `metrics.py --variant v2`
  analyses that variant. Variants are a separate cell set (the prompt text is in the cache key).

### Categorical track (`--track categorical`)

* Rows: `data/categorical/pairs_categorical_v1.csv` (40 items) plus the Ipsos homicide item from
  `data/pairs_categorical.csv` (options Higher / About the same / Lower), 972 pairs.
* Templates in `prompts/categorical/`: `plain` and `official` list the options as lettered choices and ask for the
  letter; `public_guess` and `memory_check` ask what percentage would choose the correct option, with the options
  inline. Eurobarometer statements are rendered as "Is the following statement true or false? “…”"; the climate
  items use clean restatements and readable option labels from `prompts/categorical/item_overrides.json` (the
  stored option is what gets recorded and scored). Survey names, years and a non-leaking official-source name per
  source are in `prompts/categorical/sources.json` (the data's `truth_source` column cites the fact itself and is
  never shown to the model).
* `parse.parse_option` maps a reply (letter, option text, label, true/false) to the stored option; number prompts
  use `parse_number` as before. Rows carry `is_correct`, `truth_set`, `public_majority_option`, `pct_correct`.
* `metrics_categorical.py` writes `results/metrics_categorical.md`: accuracy, inheritance on majority-wrong rows,
  flattening of the simulated share-correct, memorization, and distribution entropies.

### Answer distributions (`--distributions`, opt-in, off by default)

With `--distributions`, after a local model's samples are generated, `run.py` computes, once per unique (model, prompt), the model's
probability over the candidate answers at the answer position and appends it to `results/distributions.jsonl`
(`--distributions-file`), keyed by `model_id:prompt_sha256`; every results row carries `prompt_sha256`.
Method in `distributions.py`: numeric prompts walk the digit tree over tokens whose text is 1-3 ASCII digits
(Qwen: one digit per token; gpt-oss: up to three digits per token), one cached single-token step per prefix,
with the cache restored from a snapshot before each sibling; a prefix ends when the next token is not a digit,
so "25%" and "25.5" both count as 25; prefixes below `--prune` (default 1e-4) are left as `mass_unresolved`;
mass on non-number first tokens or numbers above 100 is `mass_outside`. Each entry stores the top-10
(value, probability), the normalised 101-point vector, entropy in bits, peaks and a bimodal flag (two local
maxima >= 0.05 at least 3 apart), the answer position, prefix length and settings. Option prompts store the
probability of every option letter plus `other`. For gpt-oss the answer position is the first token of the
final channel after sample 0's reasoning (`answer_position = after_sample0_reasoning`, caveat stored per entry);
for the Qwen models thinking is off and it is the first generated token.

`scripts/distributions_v0.py` computes the distributions for the 360 v0 prompts on all three models into
`results/v0/distributions.jsonl` and writes `results/v0/distributions_summary.md` (bimodality against H and T on
the pairs where |H - T| >= 10, mass near T vs near H, entropy, timing). `metrics.py` and
`metrics_categorical.py` report mean entropy and the share of bimodal cells per prompt type when a
distributions file is present.

### Cell counts and runtime estimates

Per-call latencies from the v0 runs (batched generation): qwen3.5-9b 0.11 s, qwen3.8-27b 0.39 s,
gpt-oss-20b 0.44 s. The table uses the v0 per-call latencies, multiplied by the new cell counts; it is not a v1 measurement.
Distributions are not computed unless `--distributions` is given.

| track | pairs | cells per model (4 prompts x 5 samples) | new cells per model | qwen3.5-9b | qwen3.8-27b | gpt-oss-20b |
|---|---|---|---|---|---|---|
| numeric, both waves | 280 | 5,600 | 3,800 (the 1,800 v0 cells are cached) | 7 min | 25 min | 28 min |
| categorical | 972 | 19,440 | 19,440 | 36 min | 2.1 h | 2.4 h |
| paraphrase probe, one variant, public_guess only | 280 | 1,400 | 1,400 | 3 min | 9 min | 10 min |

Distribution passes per model: numeric 1,120 unique prompts, categorical 3,888 unique prompts (half of them
option prompts at one pass each). Measured distribution cost, from the 2026-11-22 smoke runs on qwen3.5-9b: numeric prompts averaged about 6 s
each (85 forward passes on average, 48 entries); categorical option prompts averaged about 4.6 s over 38 prompts.
The full v0 distribution pass over all three models was stopped partway and is not timed; its partial output
in `results/v0/distributions.jsonl` is uncommitted.

### Commands

```
.venv/bin/python run.py --dry-run                                  # numeric, both waves: 280 pairs, 1,120 unique prompts
.venv/bin/python run.py --track categorical --dry-run              # 972 pairs, 3,888 unique prompts
.venv/bin/python parse.py                                          # self-test (numbers and options)
.venv/bin/python run.py --models qwen3.5-9b --waves ipsos_2020     # one model, the 2020 wave (+ distributions)
.venv/bin/python run.py --track categorical --models qwen3.5-9b    # one model, categorical track
.venv/bin/python run.py --prompt-variant v2 --prompts public_guess # paraphrase probe, variant 2
.venv/bin/python scripts/distributions_v0.py                       # v0 answer distributions, all models
.venv/bin/python metrics.py && .venv/bin/python metrics_categorical.py
```

Smoke runs (2026-11-22, qwen3.5-9b): numeric track, 2020 items on Japan, Chile and South Africa, 20 new cells,
0 failed, all parsed. Categorical track, four items on five countries, 26 new cells, 0 failed, all parsed to an
option or a number. Smoke outputs are gitignored and not committed.
