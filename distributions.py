"""Answer distributions: the model's probability over candidate answers at the answer position,
computed once per unique (model, prompt) from next-token logits, not from samples.

Numeric prompts (candidates 0..100). Digits are separate tokens in the Qwen tokenizers ('2','5'),
single tokens up to three digits in gpt-oss's o200k tokenizer ('25'). Both are handled by one
tree walk over "digit-like" tokens (decoded text is 1-3 ASCII digits): one pass for the prompt, then,
one cached single-token step per digit prefix worth expanding, restoring the cache from a per-node
snapshot before each sibling (trim_prompt_cache is not used because the hybrid Qwen caches cannot be
trimmed; number_distribution_batched is a cache-free reference used to validate the walk). For a prefix such as "2", every non-digit
next token (EOS, '%', '.', newline, words) terminates the number, so
P("25") = P('2') P('5'|'2') P(non-digit|'25'). A decimal "25.5" therefore counts as 25. Prefixes whose
cumulative probability is below `prune` are not expanded; their mass is reported as `unresolved`.
Numbers above 100 and non-number first tokens are `outside`. A leading-space token ("<space>25") is
followed as a transparent prefix when its mass exceeds `prune`.

Option prompts (categorical plain/official): candidates are the option letters A, B, C, ... read
directly from the first-token distribution (plain and space-prefixed letter tokens are summed);
`other` is everything else, so entries = options + 1.

gpt-oss (harmony format, reasoning cannot be switched off): the answer position is the first token
of the final channel, which comes after the sampled reasoning. We take the reasoning of sample 0 of
the same cell (raw generation up to and including "<|channel|>final<|message|>") and condition on
it; the caveat is recorded per entry (answer_position = "after_sample0_reasoning"). For models with
thinking off the answer position is the first generated token (answer_position = "first_token").

Entropy is in bits over the normalised candidate distribution. A numeric distribution is "bimodal"
when it has at least two local maxima with probability >= 0.05 that are at least 3 points apart.
"""
import hashlib
import json
import math
import os
import re
import time

HARMONY_FINAL = "<|channel|>final<|message|>"
DIGIT_RE = re.compile(r"^\d{1,3}$")
PEAK_MIN = 0.05
PEAK_SEP = 3


def prompt_sha256(prompt_text):
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


def dist_key(model_id, prompt_text):
    return model_id + ":" + prompt_sha256(prompt_text)


def _vocab_tables(tok):
    """Digit-like tokens (id -> digit string), the leading-space token id(s), and letter token ids."""
    digits, spaces, letters = {}, [], {}
    vocab = tok.get_vocab() if hasattr(tok, "get_vocab") else {}
    for _, i in vocab.items():
        try:
            s = tok.decode([i])
        except Exception:
            continue
        if DIGIT_RE.match(s):
            digits[i] = s
        elif s == " ":
            spaces.append(i)
        elif len(s) == 2 and s[0] == " " and s[1].isalpha() and s[1].isupper():
            letters.setdefault(s[1], []).append(i)
        elif len(s) == 1 and s.isalpha() and s.isupper():
            letters.setdefault(s, []).append(i)
    return digits, spaces, letters


def prepare(handle):
    """Attach the vocab tables to a loaded local model handle (idempotent)."""
    if "dist_tables" not in handle:
        handle["dist_tables"] = _vocab_tables(handle["tokenizer"])
    return handle["dist_tables"]


def answer_prefix_ids(handle, chat_ids, sample0_raw_generation):
    """Token ids up to the answer position. For harmony models with a sampled reasoning channel,
    append sample 0's generation up to the end of the final-channel header."""
    gen = sample0_raw_generation or ""
    if HARMONY_FINAL in gen:
        pre = gen[: gen.index(HARMONY_FINAL) + len(HARMONY_FINAL)]
        extra = handle["tokenizer"].encode(pre, add_special_tokens=False)
        return list(chat_ids) + list(extra), "after_sample0_reasoning"
    return list(chat_ids), "first_token"


def _last_probs_batch(model, seqs, chunk=16):
    """Next-token distributions at the last position of each sequence (no cache; sequences must share a
    length). Used by the batched reference implementation and for single prompts."""
    import mlx.core as mx
    out = []
    for i in range(0, len(seqs), chunk):
        batch = mx.array(seqs[i:i + chunk])
        logits = model(batch)
        probs = mx.softmax(logits[:, -1, :].astype(mx.float32), axis=-1)
        mx.eval(probs)
        out.extend([probs[j] for j in range(probs.shape[0])])
        del logits
    mx.clear_cache()
    return out


def _copy_state(st):
    """Deep copy of a cache layer's state tuple: arrays are copied (KVCache writes into its buffers in
    place), lists of arrays (ArraysCache for the hybrid Qwen layers) are rebuilt with copied arrays."""
    import mlx.core as mx

    def cp(x):
        if isinstance(x, mx.array):
            return x + 0
        if isinstance(x, list):
            return [cp(y) for y in x]
        return x
    return tuple(cp(x) for x in st)


def _snapshot(cache):
    import mlx.core as mx
    snap = [_copy_state(c.state) for c in cache]
    mx.eval([x for st in snap for x in st if isinstance(x, mx.array)] + [y for st in snap for x in st if isinstance(x, list) for y in x if isinstance(y, mx.array)])
    return snap


def _restore(cache, snap):
    for c, st in zip(cache, snap):
        c.state = _copy_state(st)


def _step_probs(model, cache, token_ids):
    import mlx.core as mx
    logits = model(mx.array(token_ids)[None], cache=cache)
    probs = mx.softmax(logits[0, -1].astype(mx.float32), axis=-1)
    mx.eval(probs)
    return probs


def number_distribution(handle, prefix_ids, prune=1e-4, max_value=100):
    """Return dict with probs over 0..max_value, outside, unresolved, passes (forward passes run).

    Depth-first walk with the KV cache: the prompt is processed once; every digit prefix worth
    expanding is one cached single-token step, and the cache is restored from a per-node snapshot
    before the next sibling (trim_prompt_cache is not used: the hybrid Qwen caches cannot be trimmed)."""
    import mlx.core as mx
    from mlx_lm.models.cache import make_prompt_cache
    model = handle["mlx_model"]
    digits, spaces, _ = prepare(handle)
    digit_ids = list(digits.keys())
    digit_arr = mx.array(digit_ids) if digit_ids else None
    out = {"probs": [0.0] * (max_value + 1), "outside": 0.0, "unresolved": 0.0, "passes": 0}
    cache = make_prompt_cache(model)
    probs0 = _step_probs(model, cache, list(prefix_ids))
    out["passes"] += 1

    def expand(prefix, p_node, probs):
        """Terminate `prefix` here and expand its digit continuations; the cache is positioned after `prefix`."""
        pv = probs[digit_arr].tolist() if digit_ids else []
        cont = [(tid, digits[tid], p) for tid, p in zip(digit_ids, pv) if p > 0]
        total_digit = sum(p for _, _, p in cont)
        if prefix:
            value = int(prefix)
            if value <= max_value:
                out["probs"][value] += p_node * max(0.0, 1.0 - total_digit)
            else:
                out["outside"] += p_node * max(0.0, 1.0 - total_digit)
        todo = []
        for tid, ds, p in cont:
            new, p_new = prefix + ds, p_node * p
            if len(new) > 3 or int(new) > max_value:
                out["outside"] += p_new
            elif p_new < prune:
                out["unresolved"] += p_new
            else:
                todo.append((tid, new, p_new))
        if not todo:
            return
        snap = _snapshot(cache)
        for i, (tid, new, p_new) in enumerate(todo):
            if i:
                _restore(cache, snap)
            nxt = _step_probs(model, cache, [tid])
            out["passes"] += 1
            expand(new, p_new, nxt)
        _restore(cache, snap)

    first_digit = float(sum(probs0[digit_arr].tolist())) if digit_ids else 0.0
    p_space = float(sum(probs0[mx.array(spaces)].tolist())) if spaces else 0.0
    out["outside"] += max(0.0, 1.0 - first_digit - p_space)
    root = _snapshot(cache)
    expand("", 1.0, probs0)
    if spaces and p_space >= prune:
        _restore(cache, root)
        sp = _step_probs(model, cache, [spaces[0]])
        out["passes"] += 1
        sub_digit = float(sum(sp[digit_arr].tolist())) if digit_ids else 0.0
        out["outside"] += p_space * max(0.0, 1.0 - sub_digit)
        expand("", p_space, sp)
    elif spaces:
        out["unresolved"] += p_space
    return out


def number_distribution_batched(handle, prefix_ids, prune=1e-4, max_value=100, chunk=16):
    """Reference implementation without any cache (prompt + prefix recomputed per node, batched per
    depth). Slower; used to validate number_distribution."""
    import mlx.core as mx
    model = handle["mlx_model"]
    digits, spaces, _ = prepare(handle)
    digit_ids = list(digits.keys())
    out = {"probs": [0.0] * (max_value + 1), "outside": 0.0, "unresolved": 0.0, "passes": 0}
    probs0 = _last_probs_batch(model, [list(prefix_ids)], chunk)[0]
    out["passes"] += 1
    frontier = [((), "", 1.0, probs0)]
    first_digit = float(sum(probs0[mx.array(digit_ids)].tolist())) if digit_ids else 0.0
    p_space = float(sum(probs0[mx.array(spaces)].tolist())) if spaces else 0.0
    out["outside"] += max(0.0, 1.0 - first_digit - p_space)
    if spaces and p_space >= prune:
        sp = _last_probs_batch(model, [list(prefix_ids) + [spaces[0]]], chunk)[0]
        out["passes"] += 1
        sub_digit = float(sum(sp[mx.array(digit_ids)].tolist())) if digit_ids else 0.0
        out["outside"] += p_space * max(0.0, 1.0 - sub_digit)
        frontier.append(((spaces[0],), "", p_space, sp))
    elif spaces:
        out["unresolved"] += p_space
    depth = 0
    while frontier and depth < 3:
        depth += 1
        children = []
        for seq, pref, p_node, probs in frontier:
            pv = probs[mx.array(digit_ids)].tolist() if digit_ids else []
            cont = [(tid, digits[tid], p) for tid, p in zip(digit_ids, pv) if p > 0]
            total_digit = sum(p for _, _, p in cont)
            if pref:
                value = int(pref)
                if value <= max_value:
                    out["probs"][value] += p_node * max(0.0, 1.0 - total_digit)
                else:
                    out["outside"] += p_node * max(0.0, 1.0 - total_digit)
            for tid, ds, p in cont:
                new, p_new = pref + ds, p_node * p
                if len(new) > 3 or int(new) > max_value:
                    out["outside"] += p_new
                elif p_new < prune:
                    out["unresolved"] += p_new
                else:
                    children.append((seq + (tid,), new, p_new))
        if not children:
            frontier = []
            break
        seqs = [list(prefix_ids) + list(seq) for seq, _, _ in children]
        probs_list = _last_probs_batch(model, seqs, chunk)
        out["passes"] += len(children)
        frontier = [(seq, pref, p, pr) for (seq, pref, p), pr in zip(children, probs_list)]
    for seq, pref, p_node, probs in frontier:
        pv = probs[mx.array(digit_ids)].tolist() if digit_ids else []
        total_digit = sum(p for p in pv if p > 0)
        if pref and int(pref) <= max_value:
            out["probs"][int(pref)] += p_node * max(0.0, 1.0 - total_digit)
            out["outside"] += p_node * total_digit
        elif pref:
            out["outside"] += p_node
    return out


def option_distribution(handle, prefix_ids, letters):
    """Probability of each option letter at the answer position, plus 'other'."""
    import mlx.core as mx
    model = handle["mlx_model"]
    _, _, letter_ids = prepare(handle)
    from mlx_lm.models.cache import make_prompt_cache
    probs = _step_probs(model, make_prompt_cache(model), list(prefix_ids))
    out = {}
    for L in letters:
        ids = letter_ids.get(L, [])
        out[L] = float(sum(probs[mx.array(ids)].tolist())) if ids else 0.0
    out["other"] = max(0.0, 1.0 - sum(out.values()))
    return {"option_probs": out, "passes": 1}


def entropy_bits(ps):
    tot = sum(ps)
    if tot <= 0:
        return None
    return -sum((p / tot) * math.log2(p / tot) for p in ps if p > 0)


def peaks(probs):
    """Local maxima with probability >= PEAK_MIN, at least PEAK_SEP apart (greedy by height)."""
    cands = []
    for i, p in enumerate(probs):
        if p < PEAK_MIN:
            continue
        left = probs[i - 1] if i > 0 else -1
        right = probs[i + 1] if i + 1 < len(probs) else -1
        if p >= left and p >= right:
            cands.append((p, i))
    cands.sort(reverse=True)
    kept = []
    for p, i in cands:
        if all(abs(i - j) >= PEAK_SEP for _, j in kept):
            kept.append((p, i))
    return [(i, round(p, 4)) for p, i in kept]


def summarize_numeric(nd):
    probs = nd["probs"]
    tot = sum(probs)
    norm = [p / tot for p in probs] if tot > 0 else probs
    top = sorted(((i, p) for i, p in enumerate(norm)), key=lambda t: -t[1])[:10]
    pk = peaks(norm)
    return {"kind": "number", "top10": [(i, round(p, 5)) for i, p in top], "entropy_bits": entropy_bits(norm),
            "mass_in_candidates": round(tot, 5), "mass_outside": round(nd["outside"], 5), "mass_unresolved": round(nd["unresolved"], 5),
            "peaks": pk, "bimodal": len(pk) >= 2, "passes": nd["passes"], "probs": [round(p, 6) for p in norm]}


def summarize_options(od, letters_to_options):
    op = od["option_probs"]
    opts = [op[L] for L in letters_to_options]
    tot = sum(opts)
    return {"kind": "option", "option_probs": {letters_to_options[L]: round(op[L], 5) for L in letters_to_options},
            "letter_probs": {L: round(op[L], 5) for L in letters_to_options}, "other": round(op["other"], 5),
            "entropy_bits": entropy_bits(opts), "mass_in_candidates": round(tot, 5), "passes": od["passes"]}


def compute_entry(handle, model, cell_prompt, sample0_raw, settings, prune=1e-4):
    """cell_prompt: dict with prompt_text, answer_kind ('number'|'option'), and for options the
    ordered letters->option mapping. Returns the JSON-ready entry."""
    import providers
    t0 = time.time()
    chat_ids = providers._chat_ids(handle, cell_prompt["prompt_text"])
    ids, position = answer_prefix_ids(handle, chat_ids, sample0_raw)
    if cell_prompt["answer_kind"] == "option":
        letters = list(cell_prompt["letters"].keys())
        summary = summarize_options(option_distribution(handle, ids, letters), cell_prompt["letters"])
    else:
        summary = summarize_numeric(number_distribution(handle, ids, prune=prune))
    summary.update({"model_id": model["model_id"], "model_key": model.get("repo") or model.get("slug"),
                    "prompt_sha256": prompt_sha256(cell_prompt["prompt_text"]), "key": dist_key(model["model_id"], cell_prompt["prompt_text"]),
                    "answer_position": position, "prefix_tokens": len(ids), "settings": settings, "prune": prune,
                    "seconds": round(time.time() - t0, 3), "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    if position == "after_sample0_reasoning":
        summary["caveat"] = "answer position conditioned on sample 0's reasoning channel; the distribution would differ after other reasoning samples"
    return summary


def load_existing(path):
    keys = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                keys.add(json.loads(line)["key"])
            except (ValueError, KeyError):
                continue
    return keys


def load_entries(path):
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            out[e["key"]] = e
    return out
