# misperception-bench

Working title of the paper: **Lost in Average: How LLMs Erase Differences in What the World Believes**.

The study asks whether large language models preserve how beliefs about society vary across
countries, or collapse them into one answer. It asks whether a model's errors track the official
figure or the public's misperception of it. And it asks whether a model knows both the
misperception and the truth yet reports something else.

## Research questions and hypotheses

RQ1, homogenization. When asked what the public believes, do models preserve how beliefs vary
across countries?

- H1a. Model simulations vary less across countries than human estimates do (variance ratio
  below 1), most strongly for lower-resource countries.

RQ2, inheritance. When asked for the true value, do models track official truth, inherit the
public's error, or amplify it?

- H2a. On average models are closer to the truth than the public (lambda between 0 and 1).
- H2b. Model errors show the same log-odds compression toward 50% that explains human minority
  overestimation (Guay, Marghetis, Wong and Landy, PNAS 2025).

RQ3, knowing versus saying. Do models know both the misperception and the truth, yet report
something else?

- H3. Frontier models answer the public-guess prompt close to H and the official or plain prompt
  close to T; smaller models show less separation.

## Design

For each country and item there are three quantities. H is the public's average estimate from
the survey. T is the official figure from the item's primary source. M is the model's answer.

Each model answers four prompts per pair, each with a single number from 0 to 100:

- plain: the question as the public was asked it.
- official: the same question prefixed with the official source.
- public_guess: what the average person in that country would guess.
- memory_check: what the Ipsos 2024 survey reported, which flags recall rather than reasoning.

Rendered example, public_guess, Canada, immigrant share: "If you asked people in Canada, what
would the average person guess is the percentage of Canada's population that immigrants (i.e.,
people born in another country) represent? Answer with a single number from 0 to 100."

Metrics: the noise floor (spread across repeated samples and paraphrases), the variance ratio
across countries, lambda (model error regressed on public error), the compression slope of
model estimates on truth compared with the human slope, the knowing-versus-saying gap between
the public_guess and plain or official answers, and the memorization rate from memory_check.
Every cell is sampled 5 times. All percent items are analysed on the log-odds scale.

## Data

Only data from 2020 onward is used. The human side is the Ipsos Perils of Perception 2024 wave:
three percent items (top-1% wealth share, immigrant share, Muslim share) across 30 countries,
plus the categorical homicide-trend item. Truth comes from each item's primary source at one
vintage: World Bank 2024 migrant stock, Pew 2020 religious composition, and WID 2024 wealth
shares. The figure Ipsos printed is kept alongside in every row.

Provenance, the truth rule, validation results and the decisions log are in `data/README.md`.
More 2020-onward survey questions are being inventoried to grow the item set.

## Repository layout

- `data/`: `pairs.csv`, `pairs_categorical.csv`, `countries.csv`, `items.yaml`, `sources.csv`,
  the transcription files, and `validation/` with the truth cross-check.
- `scripts/`: `build_pairs.py`, `build_countries.py`, `fetch_web_presence.py`, `validate.py`.
- The model-running code (`run.py`, `prompts/`, `models.yaml`, `parse.py`, `metrics.py`) with its
  own `RUNNING.md` arrives on the inference branch and is being merged.

## Status and roadmap

The v0 runs three local open-weight models via Apple MLX: gpt-oss-20b, Qwen3.8-27B and
Qwen3.5-9B.

Next steps, in order: run the v0; read the kill criteria (memorization rate, paraphrase
sensitivity, noise floor against the cross-country spread); add 2020-onward items; then run the
closed models.

## License

MIT, see `LICENSE`.
