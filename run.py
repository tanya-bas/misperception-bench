"""Run the prompts over the dataset for the models in models.yaml and append one JSON line per call
to results/results.jsonl, plus one answer distribution per unique (model, prompt) to
results/distributions.jsonl.

Two tracks:
  numeric (default)   data/pairs.csv, both waves; four prompts (plain, official, public_guess, memory_check);
                      per-item plain wording, official source name and the quoted survey wording come from
                      data/items.yaml, the survey year from its `waves` block.
  categorical         data/categorical/pairs_categorical_v1.csv plus the homicide item from
                      data/pairs_categorical.csv; plain/official ask for the letter of an option,
                      public_guess/memory_check ask what percentage chose the correct option.
                      Per-source survey names and the official-source name are in prompts/categorical/sources.json;
                      cleaner question text and option labels for derived items in prompts/categorical/item_overrides.json.

Cells = model x pair x prompt_type x sample. A cell is skipped when its cache file exists
(results/cache/<sha256>.json), so the script can be stopped and restarted. The cache key is
sha256 of (model repo or slug, rendered prompt, sample index, settings), so changing a template
or a setting re-runs only what changed. Every row carries prompt_sha256, the key into
results/distributions.jsonl (model_id + ":" + prompt_sha256), written when --distributions is on
(default) after a model's samples are generated (see distributions.py).

Local models (provider local_mlx, the default) are processed one model at a time: load, run every
cell for that model, free it, load the next. Remote models (provider openrouter) use a thread pool.

Examples
  python3 run.py --dry-run                                  render every numeric prompt, no model calls, cell counts
  python3 run.py --track categorical --dry-run              same for the categorical track
  python3 run.py --smoke                                    smallest model x 2 items x 3 countries x 4 prompts x 1 sample
  python3 run.py --track categorical --smoke                categorical smoke (4 items, a few countries)
  python3 run.py --models qwen3.5-9b --waves ipsos_2020     one model, one wave
  python3 run.py --prompt-variant v2 --prompts public_guess paraphrase probe (prompts/public_guess_v2.txt)
  python3 run.py                                            every model, numeric track, 5 samples per cell
Run with the project venv: .venv/bin/python run.py ...
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import distributions
import parse
import providers

ROOT = os.path.dirname(os.path.abspath(__file__))
PAIRS = os.path.join(ROOT, "data", "pairs.csv")
ITEMS_YAML = os.path.join(ROOT, "data", "items.yaml")
CAT_PAIRS = os.path.join(ROOT, "data", "categorical", "pairs_categorical_v1.csv")
CAT_HOMICIDE = os.path.join(ROOT, "data", "pairs_categorical.csv")
MODELS = os.path.join(ROOT, "models.yaml")
PROMPTS = os.path.join(ROOT, "prompts")
CAT_PROMPTS = os.path.join(PROMPTS, "categorical")
CAT_SOURCES = os.path.join(CAT_PROMPTS, "sources.json")
CAT_OVERRIDES = os.path.join(CAT_PROMPTS, "item_overrides.json")
RESULTS_DIR = os.path.join(ROOT, "results")
CACHE_DIR = os.path.join(RESULTS_DIR, "cache")
DISTRIBUTIONS = os.path.join(RESULTS_DIR, "distributions.jsonl")

PROMPT_TYPES = ["plain", "official", "public_guess", "memory_check"]
OPTION_PROMPTS = {"plain", "official"}  # in the categorical track these ask for a letter
LETTERS = "ABCDEFGH"
SMOKE = {"items": ["immigrant_share", "muslim_share"], "countries": ["Japan", "Canada", "South Africa"], "n": 1}
SMOKE_CAT = {"items": ["eb516_q03_antibiotics_kill_viruses", "gm_q1_largest_refugee_share_country", "clim_rank_region_percapita_us_highest", "homicide_trend"],
             "countries": ["Germany", "United States", "Chile", "Turkey", "Poland"], "n": 1}
HOMICIDE_OPTIONS = [("higher", "Higher"), ("same", "About the same"), ("lower", "Lower")]


# ----------------------------------------------------------------------------- config loaders

def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].replace('\\"', '"')
    return v


def load_models(path=MODELS):
    """Parse the flat '- key: value' list in models.yaml (no PyYAML on this machine)."""
    models, cur = [], None
    for raw in open(path, encoding="utf-8"):
        if raw.lstrip().startswith("#") or not raw.strip():
            continue
        line = raw.rstrip()
        if line.startswith("- "):
            cur = {}
            models.append(cur)
            line = "  " + line[2:]
        if cur is None or ":" not in line:
            sys.exit("%s: unexpected line: %r" % (path, raw))
        k, v = line.strip().split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        elif v.lower() in ("true", "false"):
            v = v.lower() == "true"
        else:
            try:
                v = int(v) if v.lstrip("-").isdigit() else float(v)
            except ValueError:
                pass
        cur[k.strip()] = v
    return models


def load_items_yaml(path=ITEMS_YAML):
    """Read data/items.yaml with a small reader for the subset of YAML it uses: an `items:` list of
    `  - item_id:` blocks with `    key: value` lines (folded `>` blocks are skipped), and a `waves:`
    list of `  - wave:` blocks. Returns (items by item_id, waves by wave id)."""
    items, waves, section, cur = {}, {}, None, None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):           # top-level key
            section = line.split(":", 1)[0].strip()
            cur = None
            continue
        if section not in ("items", "waves"):
            continue
        m = re.match(r"^  - (item_id|wave): (.*)$", line)
        if m:
            cur = {m.group(1): _unquote(m.group(2))}
            (items if section == "items" else waves)[cur[m.group(1)]] = cur
            continue
        m = re.match(r"^    ([A-Za-z0-9_]+): (.*)$", line)
        if m and cur is not None and m.group(2).strip() != ">":
            cur[m.group(1)] = _unquote(m.group(2))
    return items, waves


def load_templates(track, variant="v1"):
    d = CAT_PROMPTS if track == "categorical" else PROMPTS
    out = {}
    for p in PROMPT_TYPES:
        name = p + ".txt"
        if p == "public_guess" and variant != "v1":
            name = "public_guess_%s.txt" % variant
        out[p] = open(os.path.join(d, name), encoding="utf-8").read().strip()
    return out


# ----------------------------------------------------------------------------- pairs

def load_pairs(path=PAIRS):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    out = []
    for r in rows:
        if r["t_flag"] == "missing" or r["t_value"] == "":  # no truth, nothing to score
            continue
        r["track"] = "numeric"
        r["country"] = r["country_name_ipsos"]
        out.append(r)
    return out


def load_categorical_pairs(cat_path=CAT_PAIRS, homicide_path=CAT_HOMICIDE):
    """Rows of the categorical track in one shape: options (list), pct (dict), truth set, pct_correct."""
    out = []
    for r in csv.DictReader(open(cat_path, encoding="utf-8")):
        if not r["truth_option"].strip() or r["pct_correct"].strip() == "":
            continue
        out.append({"track": "categorical", "wave": r["wave"], "source_id": r["source_id"], "country": r["country_name"],
                    "country_iso3": r["country_iso3"], "item_id": r["item_id"], "question_wording": r["question_wording"],
                    "options": json.loads(r["options"]), "pct": json.loads(r["pct_per_option"]), "pct_dk": r["pct_dk"],
                    "pct_correct": float(r["pct_correct"]), "public_majority_option": r["public_majority_option"],
                    "truth_option": r["truth_option"], "truth_set": [t.strip() for t in r["truth_option"].split("|")],
                    "truth_source": r["truth_source"], "n_country": r["n_country"]})
    for r in csv.DictReader(open(homicide_path, encoding="utf-8")):
        if not r["actual_direction"].strip():
            continue
        pct = {label: float(r["pct_" + key]) for key, label in HOMICIDE_OPTIONS}
        truth = dict(HOMICIDE_OPTIONS)[r["actual_direction"]]
        maj = dict(HOMICIDE_OPTIONS).get(r["public_majority"], r["public_majority"] or "no_majority")
        out.append({"track": "categorical", "wave": r["wave"], "source_id": "ipsos_homicide_2024", "country": r["country_name_ipsos"],
                    "country_iso3": r["country_iso3"], "item_id": r["item_id"], "question_wording": r["question_wording"],
                    "options": [label for _, label in HOMICIDE_OPTIONS], "pct": pct, "pct_dk": "",
                    "pct_correct": pct[truth], "public_majority_option": maj, "truth_option": truth, "truth_set": [truth],
                    "truth_source": r["truth_source"], "n_country": r["n_country_approx"]})
    return out


# ----------------------------------------------------------------------------- rendering

EB_STATEMENT_RE = re.compile(r"—\s*[\"“](.*)[\"”]\s*$", re.S)


def categorical_question(pair, overrides):
    """Clean question text and the (letter, option, label) choices for a categorical pair."""
    ov = overrides.get(pair["item_id"], {})
    country = pair["country"]
    if "question" in ov:
        q = ov["question"].format(country=country)
    elif pair["source_id"].startswith("eb"):
        m = EB_STATEMENT_RE.search(pair["question_wording"])
        stmt = m.group(1) if m else pair["question_wording"]
        q = 'Is the following statement true or false? \u201c%s\u201d' % stmt  # curly quotes so the question can itself be quoted
    else:
        q = pair["question_wording"].strip().strip("“”\"")
    labels = ov.get("labels", {})
    opts = [o for o in pair["options"] if o.lower() not in ("don't know", "dont know", "don’t know")]
    choices = [(LETTERS[i], o, labels.get(o, o)) for i, o in enumerate(opts)]
    return q, choices


def render(template_text, prompt_type, pair, meta):
    """meta: items/waves (numeric) or sources/overrides (categorical). Returns (prompt_text, extras)."""
    country = pair["country"]
    if pair["track"] == "numeric":
        item = meta["items"][pair["item_id"]]
        if prompt_type in ("plain", "official"):
            q = item["plain_wording"].format(country=country)
        else:
            q = item.get("quoted_wording") or pair["question_wording"]
            q = q.replace("[COUNTRY]", country)
        year = meta["waves"][pair["wave"]]["year"]
        return template_text.format(country=country, question=q, source=item["official_source_name"], year=year), {}
    src = meta["sources"][pair["source_id"]]
    q, choices = categorical_question(pair, meta["overrides"])
    truth_labels = [lab for L, o, lab in choices if o in pair["truth_set"]]
    truth_display = " or ".join("'%s'" % t for t in truth_labels) if truth_labels else "'%s'" % pair["truth_option"]
    choices_block = "\n".join("%s) %s" % (L, lab) for L, o, lab in choices)
    choices_inline = "Options: " + "; ".join("%s) %s" % (L, lab) for L, o, lab in choices) + "."
    text = template_text.format(country=country, question=q, choices=choices_block, choices_inline=choices_inline,
                                truth_display=truth_display, source=src["official_source_name"],
                                survey_name=src["survey_name"], year=src["year"])
    return text, {"question": q, "choices": choices}


def settings_for(model, sample_idx):
    s = {"max_tokens": model["max_tokens"], "temperature": model["temperature"], "seed": 1000 + sample_idx}
    if model["provider"] == "local_mlx":
        s["top_p"] = model.get("top_p", 1.0)
        s["thinking_kwargs"] = model.get("thinking_kwargs", "{}")
        s["quantization"] = model.get("quantization", "")
    else:
        s["reasoning"] = model.get("reasoning", "default")
    return s


def model_key(model):
    return model.get("repo") or model.get("slug") or model["model_id"]


def cache_key(model, prompt_text, sample_idx, settings):
    blob = json.dumps([model_key(model), prompt_text, sample_idx, settings], sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_cells(models, pairs, templates, prompt_types, n, meta, variant):
    cells = []
    for m in models:
        for p in pairs:
            for pt in prompt_types:
                text, extras = render(templates[pt], pt, p, meta)
                for s in range(n):
                    st = settings_for(m, s)
                    cells.append({"model": m, "pair": p, "prompt_type": pt, "prompt_text": text, "extras": extras,
                                  "variant": variant if pt == "public_guess" else "v1",
                                  "sample_idx": s, "settings": st, "key": cache_key(m, text, s, st)})
    return cells


def answer_kind(cell):
    return "option" if cell["pair"]["track"] == "categorical" and cell["prompt_type"] in OPTION_PROMPTS else "number"


def row_for(cell, resp):
    m, p = cell["model"], cell["pair"]
    text = resp["text"]
    if answer_kind(cell) == "option":
        val, status, note = parse.parse_option(text, cell["extras"]["choices"])
    else:
        val, status, note = parse.parse_number(text)
    if status in ("unparseable", "refusal") and resp.get("finish_reason") == "length":
        status, note = "truncated", "finish_reason=length: raise max_tokens or thinking is on"
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cache_key": cell["key"], "prompt_sha256": distributions.prompt_sha256(cell["prompt_text"]),
        "track": p["track"], "model_id": m["model_id"], "model_key": model_key(m), "provider": m["provider"], "served_model": resp.get("served_model"),
        "wave": p["wave"], "item_id": p["item_id"], "country": p["country"], "country_iso3": p["country_iso3"],
        "prompt_type": cell["prompt_type"], "prompt_variant": cell["variant"], "sample_idx": cell["sample_idx"], "settings": cell["settings"],
        "prompt_text": cell["prompt_text"], "raw_text": text, "reasoning_text": resp.get("reasoning") or "",
        "raw_generation": resp.get("raw_generation"), "finish_reason": resp.get("finish_reason"),
        "parsed_value": val, "parse_status": status, "parse_note": note,
        "usage": resp.get("usage"), "latency_s": resp.get("latency_s"), "tokens_per_s": resp.get("tokens_per_s"), "batched": resp.get("batched"),
    }
    if p["track"] == "categorical":
        row.update({"source_id": p["source_id"], "truth_option": p["truth_option"], "truth_set": p["truth_set"],
                    "public_majority_option": p["public_majority_option"], "pct_correct": p["pct_correct"],
                    "pct_per_option": p["pct"], "answer_kind": answer_kind(cell),
                    "is_correct": (val in p["truth_set"]) if (answer_kind(cell) == "option" and status == "ok") else None,
                    "choices": [[L, o, lab] for L, o, lab in cell["extras"]["choices"]]})
    return row


class Writer:
    """Append rows to results.jsonl and the cache, thread-safe, with a progress line."""

    def __init__(self, path, total):
        self.out = open(path, "a", encoding="utf-8")
        self.lock = threading.Lock()
        self.done = self.failed = 0
        self.total = total
        self.t0 = time.time()
        self.rows = []

    def write(self, cell, row):
        with self.lock:
            json.dump(row, open(os.path.join(CACHE_DIR, cell["key"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
            self.out.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.out.flush()
            self.rows.append(row)
            self.done += 1
            if self.done % 25 == 0 or self.done == self.total:
                print("  %d/%d done, %d failed, %.0fs" % (self.done, self.total, self.failed, time.time() - self.t0), flush=True)

    def fail(self, cell, err):
        with self.lock:
            self.failed += 1
            print("FAIL %s %s %s %s: %s" % (cell["model"]["model_id"], cell["pair"]["item_id"], cell["pair"]["country"], cell["prompt_type"], err), flush=True)


def run_local(model, cells, writer, batch_size):
    """Generate every cell of one model. Returns the loaded handle (the caller frees it)."""
    print("loading %s (%s, %s GB)..." % (model["model_id"], model["repo"], model.get("disk_gb", "?")), flush=True)
    handle = providers.load_local(model)
    print("  loaded in %ss; %d cells" % (handle["load_s"], len(cells)), flush=True)
    if cells:
        settings = cells[0]["settings"]  # all cells of one model share max_tokens/temperature/top_p; the seed varies by sample
        prompts = [(c["prompt_text"], c["sample_idx"]) for c in cells]
        step = batch_size * 4  # chunks so progress and the cache are written as we go
        for i in range(0, len(cells), step):
            chunk = cells[i:i + step]
            try:
                results = providers.generate_local(handle, prompts[i:i + step], settings, batch_size=batch_size)
            except Exception as e:
                for c in chunk:
                    writer.fail(c, e)
                providers.unload_local(handle)
                raise
            for c, resp in zip(chunk, results):
                writer.write(c, row_for(c, resp))
    return handle


def sample0_raw(cell0):
    """raw_generation of sample 0 for a cell (from its cache file), used for harmony answer positions."""
    path = os.path.join(CACHE_DIR, cell0["key"] + ".json")
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8")).get("raw_generation")
        except ValueError:
            return None
    return None


def run_distributions(model, handle, all_cells, path, prune):
    """One distribution per unique prompt of this model that is not yet in the distributions file."""
    existing = distributions.load_existing(path)
    by_prompt = {}
    for c in all_cells:
        if c["model"] is model and c["sample_idx"] == 0:
            by_prompt.setdefault(c["prompt_text"], c)
    todo = [c for text, c in by_prompt.items() if distributions.dist_key(model["model_id"], text) not in existing]
    if not todo:
        print("  distributions: all %d unique prompts already present" % len(by_prompt), flush=True)
        return
    print("  distributions: %d unique prompts to compute (%d present)" % (len(todo), len(by_prompt) - len(todo)), flush=True)
    t0, passes = time.time(), 0
    with open(path, "a", encoding="utf-8") as f:
        for i, c in enumerate(todo, 1):
            cp = {"prompt_text": c["prompt_text"], "answer_kind": answer_kind(c)}
            if cp["answer_kind"] == "option":
                cp["letters"] = {L: o for L, o, lab in c["extras"]["choices"]}
            entry = distributions.compute_entry(handle, model, cp, sample0_raw(c), c["settings"], prune=prune)
            entry.update({"track": c["pair"]["track"], "item_id": c["pair"]["item_id"], "country_iso3": c["pair"]["country_iso3"],
                          "prompt_type": c["prompt_type"], "prompt_variant": c["variant"], "wave": c["pair"]["wave"]})
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            passes += entry["passes"]
            if i % 25 == 0 or i == len(todo):
                dt = time.time() - t0
                print("  distributions %d/%d, %d passes, %.0fs (%.2fs per prompt)" % (i, len(todo), passes, dt, dt / i), flush=True)


def run_remote(cells, writer, workers):
    def one(cell):
        return row_for(cell, providers.call_with_retry(cell["model"], cell["prompt_text"], cell["settings"]))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, c): c for c in cells}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                writer.write(c, fut.result())
            except Exception as e:
                writer.fail(c, e)


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", choices=["numeric", "categorical"], default="numeric")
    ap.add_argument("--models-file", default=MODELS)
    ap.add_argument("--models", help="comma-separated model_id list (default: all in the models file)")
    ap.add_argument("--waves", help="comma-separated wave ids (numeric track; default: all)")
    ap.add_argument("--items", help="comma-separated item_id list (default: all)")
    ap.add_argument("--countries", help="comma-separated country names as in the data (default: all)")
    ap.add_argument("--prompts", help="comma-separated prompt types (default: %s)" % ",".join(PROMPT_TYPES))
    ap.add_argument("--prompt-variant", default="v1", help="public_guess template variant: v1 (default), v2, v3 (prompts/public_guess_<v>.txt)")
    ap.add_argument("--n", type=int, default=5, help="samples per cell (default 5)")
    ap.add_argument("--limit", type=int, help="run at most this many new cells per model")
    ap.add_argument("--batch-size", type=int, default=16, help="local batched generation size (1 = sequential)")
    ap.add_argument("--workers", type=int, default=6, help="threads for remote providers")
    ap.add_argument("--distributions", dest="distributions", action="store_true", default=False, help="compute answer distributions per unique prompt (opt-in, local models)")
    ap.add_argument("--distributions-file", default=DISTRIBUTIONS)
    ap.add_argument("--prune", type=float, default=1e-4, help="digit-tree prefixes below this probability are not expanded")
    ap.add_argument("--smoke", action="store_true", help="tiny end-to-end run on the first model")
    ap.add_argument("--dry-run", action="store_true", help="render prompts and count cells; no model calls")
    ap.add_argument("--results", default=os.path.join(RESULTS_DIR, "results.jsonl"))
    args = ap.parse_args()

    models = load_models(args.models_file)
    templates = load_templates(args.track, args.prompt_variant)
    if args.track == "numeric":
        items, waves = load_items_yaml()
        meta = {"items": items, "waves": waves}
        pairs = load_pairs()
        smoke = SMOKE
    else:
        meta = {"sources": json.load(open(CAT_SOURCES, encoding="utf-8")), "overrides": json.load(open(CAT_OVERRIDES, encoding="utf-8"))}
        pairs = load_categorical_pairs()
        smoke = SMOKE_CAT
    prompt_types = args.prompts.split(",") if args.prompts else PROMPT_TYPES
    n = args.n
    if args.smoke:
        models, n = models[:1], smoke["n"]
        pairs = [p for p in pairs if p["item_id"] in smoke["items"] and p["country"] in smoke["countries"]]
    if args.models:
        want = set(args.models.split(","))
        models = [m for m in models if m["model_id"] in want]
        missing = want - {m["model_id"] for m in models}
        if missing:
            sys.exit("unknown model_id: %s" % sorted(missing))
    if args.waves:
        pairs = [p for p in pairs if p["wave"] in set(args.waves.split(","))]
    if args.items:
        pairs = [p for p in pairs if p["item_id"] in set(args.items.split(","))]
    if args.countries:
        pairs = [p for p in pairs if p["country"] in set(args.countries.split(","))]
    for pt in prompt_types:
        if pt not in templates:
            sys.exit("unknown prompt type %r" % pt)

    cells = build_cells(models, pairs, templates, prompt_types, n, meta, args.prompt_variant)
    os.makedirs(CACHE_DIR, exist_ok=True)
    todo = [c for c in cells if not os.path.exists(os.path.join(CACHE_DIR, c["key"] + ".json"))]
    print("track=%s variant=%s models=%d pairs=%d prompts=%d n=%d -> cells=%d, cached=%d, to run=%d"
          % (args.track, args.prompt_variant, len(models), len(pairs), len(prompt_types), n, len(cells), len(cells) - len(todo), len(todo)), flush=True)
    for m in models:
        print("  %-14s %-40s cells=%d" % (m["model_id"], model_key(m), len([c for c in todo if c["model"] is m])))

    if args.dry_run:
        out = os.path.join(RESULTS_DIR, "rendered_prompts%s.jsonl" % ("" if args.track == "numeric" else "_categorical"))
        seen = set()
        with open(out, "w", encoding="utf-8") as f:
            for c in cells:
                k = (c["pair"]["item_id"], c["pair"]["country_iso3"], c["prompt_type"])
                if k in seen:
                    continue
                seen.add(k)
                f.write(json.dumps({"track": c["pair"]["track"], "wave": c["pair"]["wave"], "item_id": k[0], "country_iso3": k[1], "country": c["pair"]["country"],
                                    "prompt_type": k[2], "prompt_variant": c["variant"], "prompt_text": c["prompt_text"]}, ensure_ascii=False) + "\n")
        print("dry run: wrote %d unique prompts to %s" % (len(seen), out))
        return

    writer = Writer(args.results, len(todo) if not args.limit else min(len(todo), args.limit * len(models)))
    for m in models:
        mine = [c for c in todo if c["model"] is m]
        if args.limit:
            mine = mine[: args.limit]
        model_cells = [c for c in cells if c["model"] is m]
        if args.limit:  # distributions only for the prompts actually run
            keep = {c["prompt_text"] for c in mine}
            model_cells = [c for c in model_cells if c["prompt_text"] in keep]
        if m["provider"] == "local_mlx":
            if not mine and not args.distributions:
                continue
            handle = run_local(m, mine, writer, args.batch_size)
            try:
                if args.distributions:
                    run_distributions(m, handle, model_cells, args.distributions_file, args.prune)
            finally:
                providers.unload_local(handle)
                print("  freed %s" % m["model_id"], flush=True)
        elif mine:
            run_remote(mine, writer, args.workers)
    print("finished: %d new rows, %d failed -> %s" % (writer.done, writer.failed, args.results))
    if args.smoke or args.limit:
        lat = [r["latency_s"] for r in writer.rows if r.get("latency_s")]
        if lat:
            tps = sorted([r["tokens_per_s"] for r in writer.rows if r.get("tokens_per_s")])
            print("mean latency per call %.2fs (n=%d); tokens/s median %s" % (sum(lat) / len(lat), len(lat), tps[len(tps) // 2] if tps else "n/a"))
    if args.smoke:
        for r in writer.rows:
            print("%-34s %-14s %-13s -> %-30r [%s %s]" % (r["item_id"][:34], r["country"][:14], r["prompt_type"], r["raw_text"][:30], r["parse_status"], r["parsed_value"]))


if __name__ == "__main__":
    main()
