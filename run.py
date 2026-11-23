"""Run the v0 prompts over data/pairs.csv for the models in models.yaml and append one JSON
line per call to results/results.jsonl.

Cells = model x pair x prompt_type x sample. A cell is skipped when its cache file exists
(results/cache/<sha256>.json), so the script can be stopped and restarted. The cache key is
sha256 of (model repo or slug, rendered prompt, sample index, settings), so changing a template
or a setting re-runs only what changed.

Local models (provider local_mlx, the default) are processed one model at a time: load, run every
cell for that model, free it, load the next. Remote models (provider openrouter) use a thread pool.

Examples
  python3 run.py --dry-run                      render every prompt, no model calls, print the cell counts
  python3 run.py --smoke                        smallest model x 2 items x 3 countries x 4 prompts x 1 sample
  python3 run.py --models gpt-oss-20b --n 1 --limit 20 --results results/timing.jsonl   time 20 calls
  python3 run.py                                every model in models.yaml, 5 samples per cell
Run with the project venv: .venv/bin/python run.py ...
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import parse
import providers

ROOT = os.path.dirname(os.path.abspath(__file__))
PAIRS = os.path.join(ROOT, "data", "pairs.csv")
MODELS = os.path.join(ROOT, "models.yaml")
PROMPTS = os.path.join(ROOT, "prompts")
RESULTS_DIR = os.path.join(ROOT, "results")
CACHE_DIR = os.path.join(RESULTS_DIR, "cache")
WAVE_YEAR = "2024"

# Direct (third-person) version of each Ipsos item for the plain and official prompts. The
# public_guess and memory_check prompts quote the verbatim Ipsos wording from pairs.csv instead.
PLAIN_QUESTIONS = {
    "wealth_top1": "What percentage of {country}'s total household wealth is owned by the top 1% of richest households?",
    "immigrant_share": "What percentage of {country}'s population do immigrants (i.e., people born in another country) represent?",
    "muslim_share": "In {country}, out of 100 people, how many are Muslim?",
}
# Source named in the official prompt: the series the dataset uses as T (data/items.yaml).
SOURCE_NAMES = {
    "wealth_top1": "the World Inequality Database",
    "immigrant_share": "the World Bank's World Development Indicators",
    "muslim_share": "the Pew Research Center",
}
PROMPT_TYPES = ["plain", "official", "public_guess", "memory_check"]
SMOKE = {"items": ["immigrant_share", "muslim_share"], "countries": ["Japan", "Canada", "South Africa"], "n": 1}


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


def load_pairs(path=PAIRS):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return [r for r in rows if r["t_flag"] != "missing"]  # Peru wealth: no truth, nothing to score


def load_templates():
    return {p: open(os.path.join(PROMPTS, p + ".txt"), encoding="utf-8").read().strip() for p in PROMPT_TYPES}


def render(template_text, prompt_type, pair):
    country, item = pair["country_name_ipsos"], pair["item_id"]
    q = PLAIN_QUESTIONS[item].format(country=country) if prompt_type in ("plain", "official") else pair["question_wording"]
    return template_text.format(country=country, question=q, source=SOURCE_NAMES[item], year=WAVE_YEAR)


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


def build_cells(models, pairs, templates, prompt_types, n):
    cells = []
    for m in models:
        for p in pairs:
            for pt in prompt_types:
                text = render(templates[pt], pt, p)
                for s in range(n):
                    st = settings_for(m, s)
                    cells.append({"model": m, "pair": p, "prompt_type": pt, "prompt_text": text,
                                  "sample_idx": s, "settings": st, "key": cache_key(m, text, s, st)})
    return cells


def row_for(cell, resp):
    m, p = cell["model"], cell["pair"]
    text = resp["text"]
    val, status, note = parse.parse_number(text)
    if status in ("unparseable", "refusal") and resp.get("finish_reason") == "length":
        status, note = "truncated", "finish_reason=length: raise max_tokens or thinking is on"
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cache_key": cell["key"],
        "model_id": m["model_id"], "model_key": model_key(m), "provider": m["provider"], "served_model": resp.get("served_model"),
        "wave": p["wave"], "item_id": p["item_id"], "country": p["country_name_ipsos"], "country_iso3": p["country_iso3"],
        "prompt_type": cell["prompt_type"], "sample_idx": cell["sample_idx"], "settings": cell["settings"],
        "prompt_text": cell["prompt_text"], "raw_text": text, "reasoning_text": resp.get("reasoning") or "",
        "raw_generation": resp.get("raw_generation"), "finish_reason": resp.get("finish_reason"),
        "parsed_value": val, "parse_status": status, "parse_note": note,
        "usage": resp.get("usage"), "latency_s": resp.get("latency_s"), "tokens_per_s": resp.get("tokens_per_s"), "batched": resp.get("batched"),
    }


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
            print("FAIL %s %s %s %s: %s" % (cell["model"]["model_id"], cell["pair"]["item_id"], cell["pair"]["country_name_ipsos"], cell["prompt_type"], err), flush=True)


def run_local(model, cells, writer, batch_size):
    print("loading %s (%s, %s GB)..." % (model["model_id"], model["repo"], model.get("disk_gb", "?")), flush=True)
    handle = providers.load_local(model)
    print("  loaded in %ss; %d cells" % (handle["load_s"], len(cells)), flush=True)
    try:
        # all cells of one model share max_tokens/temperature/top_p; the seed varies by sample
        settings = cells[0]["settings"]
        prompts = [(c["prompt_text"], c["sample_idx"]) for c in cells]
        # process in chunks so progress and the cache are written as we go
        step = batch_size * 4
        for i in range(0, len(cells), step):
            chunk = cells[i:i + step]
            try:
                results = providers.generate_local(handle, prompts[i:i + step], settings, batch_size=batch_size)
            except Exception as e:
                for c in chunk:
                    writer.fail(c, e)
                raise
            for c, resp in zip(chunk, results):
                writer.write(c, row_for(c, resp))
    finally:
        providers.unload_local(handle)
        print("  freed %s" % model["model_id"], flush=True)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-file", default=MODELS)
    ap.add_argument("--models", help="comma-separated model_id list (default: all in the models file)")
    ap.add_argument("--items", help="comma-separated item_id list (default: all percent items)")
    ap.add_argument("--countries", help="comma-separated Ipsos country names (default: all)")
    ap.add_argument("--prompts", help="comma-separated prompt types (default: %s)" % ",".join(PROMPT_TYPES))
    ap.add_argument("--n", type=int, default=5, help="samples per cell (default 5)")
    ap.add_argument("--limit", type=int, help="run at most this many new cells per model")
    ap.add_argument("--batch-size", type=int, default=16, help="local batched generation size (1 = sequential)")
    ap.add_argument("--workers", type=int, default=6, help="threads for remote providers")
    ap.add_argument("--smoke", action="store_true", help="tiny end-to-end run on the first model: 2 items, 3 countries, 4 prompts, 1 sample")
    ap.add_argument("--dry-run", action="store_true", help="render prompts and count cells; no model calls")
    ap.add_argument("--results", default=os.path.join(RESULTS_DIR, "results.jsonl"))
    args = ap.parse_args()

    models, pairs, templates = load_models(args.models_file), load_pairs(), load_templates()
    prompt_types = args.prompts.split(",") if args.prompts else PROMPT_TYPES
    n = args.n
    if args.smoke:
        models, n = models[:1], SMOKE["n"]
        pairs = [p for p in pairs if p["item_id"] in SMOKE["items"] and p["country_name_ipsos"] in SMOKE["countries"]]
    if args.models:
        want = set(args.models.split(","))
        models = [m for m in models if m["model_id"] in want]
        missing = want - {m["model_id"] for m in models}
        if missing:
            sys.exit("unknown model_id: %s" % sorted(missing))
    if args.items:
        pairs = [p for p in pairs if p["item_id"] in set(args.items.split(","))]
    if args.countries:
        pairs = [p for p in pairs if p["country_name_ipsos"] in set(args.countries.split(","))]
    for pt in prompt_types:
        if pt not in templates:
            sys.exit("unknown prompt type %r" % pt)

    cells = build_cells(models, pairs, templates, prompt_types, n)
    os.makedirs(CACHE_DIR, exist_ok=True)
    todo = [c for c in cells if not os.path.exists(os.path.join(CACHE_DIR, c["key"] + ".json"))]
    print("models=%d pairs=%d prompts=%d n=%d -> cells=%d, cached=%d, to run=%d"
          % (len(models), len(pairs), len(prompt_types), n, len(cells), len(cells) - len(todo), len(todo)), flush=True)
    for m in models:
        print("  %-14s %-40s cells=%d" % (m["model_id"], model_key(m), len([c for c in todo if c["model"] is m])))

    if args.dry_run:
        out = os.path.join(RESULTS_DIR, "rendered_prompts.jsonl")
        seen = set()
        with open(out, "w", encoding="utf-8") as f:
            for c in cells:
                k = (c["pair"]["item_id"], c["pair"]["country_iso3"], c["prompt_type"])
                if k in seen:
                    continue
                seen.add(k)
                f.write(json.dumps({"item_id": k[0], "country_iso3": k[1], "country": c["pair"]["country_name_ipsos"],
                                    "prompt_type": k[2], "prompt_text": c["prompt_text"]}, ensure_ascii=False) + "\n")
        print("dry run: wrote %d unique prompts to %s" % (len(seen), out))
        return

    writer = Writer(args.results, len(todo) if not args.limit else min(len(todo), args.limit * len(models)))
    for m in models:
        mine = [c for c in todo if c["model"] is m]
        if args.limit:
            mine = mine[: args.limit]
        if not mine:
            continue
        if m["provider"] == "local_mlx":
            run_local(m, mine, writer, args.batch_size)
        else:
            run_remote(mine, writer, args.workers)
    print("finished: %d new rows, %d failed -> %s" % (writer.done, writer.failed, args.results))
    if args.smoke or args.limit:
        lat = [r["latency_s"] for r in writer.rows if r.get("latency_s")]
        if lat:
            print("mean latency per call %.2fs (n=%d); tokens/s median %s" % (
                sum(lat) / len(lat), len(lat), sorted([r["tokens_per_s"] for r in writer.rows if r.get("tokens_per_s")])[len(lat) // 2] if any(r.get("tokens_per_s") for r in writer.rows) else "n/a"))
    if args.smoke:
        for r in writer.rows:
            print("%-16s %-12s %-13s -> %-28r [%s %s]" % (r["item_id"], r["country"], r["prompt_type"], r["raw_text"][:28], r["parse_status"], r["parsed_value"]))


if __name__ == "__main__":
    main()
