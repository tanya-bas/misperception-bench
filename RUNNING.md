# Running the v0 model inference

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

Not measured yet. The model downloads could not complete from this session: Hugging Face served the
weight shards at about 0.1 MB/s and then stalled (no bytes for over a minute with both the default
client and the Xet client, 2026-11-22 afternoon), so no model has been loaded and no smoke test has run.

To measure, from a terminal with a working connection:

```
.venv/bin/hf download mlx-community/Qwen3.5-9B-4bit                         # watch the progress bar
.venv/bin/python run.py --smoke                                               # 24 cells, prints raw replies and tokens/s
.venv/bin/python run.py --models qwen3.5-9b  --n 1 --limit 20 --results results/timing.jsonl
.venv/bin/python run.py --models qwen3.8-27b --n 1 --limit 20 --results results/timing.jsonl
.venv/bin/python run.py --models gpt-oss-20b --n 1 --limit 20 --results results/timing.jsonl
.venv/bin/python timing.py --results results/timing.jsonl                     # mean s/call x 1,780 cells per model
```

Expectation, to be replaced by the measurement: with batched generation on a 64 GB Apple Silicon
machine, 4-bit 9B to 27B models produce short answers at tens of tokens per second per sequence,
so 1,780 cells of about 10 output tokens each should take well under an hour per Qwen model;
gpt-oss-20b at low reasoning effort emits a few hundred tokens per cell and will dominate the run.

## What is not here yet

* Claude and other API models: `providers.call_anthropic` is a stub.
* Plots: `metrics.py` writes tables only.
* The group prompt was dropped with H1b.
