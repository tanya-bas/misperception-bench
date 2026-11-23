"""Providers. Default is local_mlx (models from Hugging Face, run on this Mac with Apple MLX).
OpenRouter is kept as an optional provider (models_openrouter.yaml) and the Anthropic one is a stub.

Every provider returns the same plain dict per call:
  {"text", "reasoning", "finish_reason", "usage": {...}, "latency_s", ...}

local_mlx is stateful: load_local(model) once per model, generate_local(handle, prompts, settings)
for many prompts, unload_local(handle) before loading the next model, so memory never holds two.
"""
import gc
import json
import os
import re
import time
import urllib.error
import urllib.request

# ----------------------------------------------------------------------------- local MLX

THINK_RE = re.compile(r"<think>.*?</think>\s*", re.S)
HARMONY_FINAL_RE = re.compile(r"<\|channel\|>final<\|message\|>(.*?)(?:<\|return\|>|<\|end\|>|$)", re.S)
HARMONY_ANALYSIS_RE = re.compile(r"<\|channel\|>analysis<\|message\|>(.*?)<\|end\|>", re.S)
SPECIAL_RE = re.compile(r"<\|[a-z_]+\|>")


def split_reasoning(text):
    """Separate the visible answer from any reasoning the model emitted despite thinking being off.
    Handles Qwen-style <think>...</think> and gpt-oss harmony channels; returns (answer, reasoning)."""
    reasoning = ""
    m = HARMONY_FINAL_RE.search(text)
    if m:
        a = HARMONY_ANALYSIS_RE.search(text)
        reasoning = a.group(1).strip() if a else ""
        return m.group(1).strip(), reasoning
    if "<|channel|>analysis" in text:  # reasoning but no final channel (ran out of tokens)
        a = HARMONY_ANALYSIS_RE.search(text)
        return "", (a.group(1).strip() if a else SPECIAL_RE.sub("", text).strip())
    thinks = THINK_RE.findall(text)
    if thinks:
        reasoning = " ".join(t.strip() for t in thinks)
        text = THINK_RE.sub("", text)
    if "<think>" in text:  # opened a think block and never closed it (token budget)
        reasoning = (reasoning + " " + text.split("<think>", 1)[1]).strip()
        text = text.split("<think>", 1)[0]
    return SPECIAL_RE.sub("", text).strip(), reasoning


def load_local(model):
    """Download (first time, into the Hugging Face cache) and load an MLX model."""
    from mlx_lm import load  # imported here so the OpenRouter path works without mlx installed
    t0 = time.time()
    mlx_model, tokenizer = load(model["repo"])
    return {"model": model, "mlx_model": mlx_model, "tokenizer": tokenizer, "load_s": round(time.time() - t0, 1)}


def unload_local(handle):
    import mlx.core as mx
    handle.clear()
    gc.collect()
    mx.clear_cache()


def _chat_ids(handle, user_text):
    """Token ids for one user turn through the model's chat template, with its thinking mode switched
    off / minimised. thinking_kwargs comes from models.yaml (enable_thinking=false for Qwen,
    reasoning_effort=low for gpt-oss); templates ignore kwargs they do not use."""
    kw = json.loads(handle["model"].get("thinking_kwargs") or "{}")
    ids = handle["tokenizer"].apply_chat_template(
        [{"role": "user", "content": user_text}], add_generation_prompt=True, tokenize=True, **kw)
    if isinstance(ids, dict) or hasattr(ids, "input_ids"):
        ids = ids["input_ids"]
    return list(ids)


def generate_local(handle, prompts, settings, batch_size=16, seed_base=1000):
    """Generate one reply per prompt. prompts is a list of (user_text, sample_idx).
    Uses mlx_lm batch_generate (present in mlx-lm 0.32) when batch_size > 1, else sequential generate.
    Returns a list of result dicts in the same order as prompts."""
    import mlx.core as mx
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler
    from mlx_lm.generate import batch_generate
    tok = handle["tokenizer"]
    sampler = make_sampler(temp=float(settings["temperature"]), top_p=float(settings.get("top_p", 0.0)))
    max_tokens = int(settings["max_tokens"])
    out = []
    if batch_size > 1 and len(prompts) > 1:
        for i in range(0, len(prompts), batch_size):
            chunk = prompts[i:i + batch_size]
            mx.random.seed(seed_base + chunk[0][1])
            ids = [_chat_ids(handle, p) for p, _ in chunk]
            t0 = time.time()
            resp = batch_generate(handle["mlx_model"], tok, ids, max_tokens=max_tokens, sampler=sampler,
                                  verbose=False, return_token_ids=True)
            dt = time.time() - t0
            tps = getattr(resp.stats, "generation_tps", None)
            for (p, s), raw, toks in zip(chunk, resp.texts, resp.token_ids):
                out.append(_local_result(raw, len(toks), max_tokens, dt / len(chunk), batched=len(chunk), tps=tps))
        return out
    for p, s in prompts:
        mx.random.seed(seed_base + s)
        t0 = time.time()
        raw = generate(handle["mlx_model"], tok, prompt=_chat_ids(handle, p), max_tokens=max_tokens, sampler=sampler, verbose=False)
        dt = time.time() - t0
        n_out = len(tok.encode(raw)) if raw else 0
        out.append(_local_result(raw, n_out, max_tokens, dt, batched=1, tps=(n_out / dt if dt > 0 else None)))
    return out


def _local_result(raw, n_out, max_tokens, latency, batched, tps):
    answer, reasoning = split_reasoning(raw)
    return {
        "text": answer, "reasoning": reasoning, "raw_generation": raw,
        "finish_reason": "length" if n_out >= max_tokens else "stop",
        "usage": {"prompt_tokens": None, "completion_tokens": n_out, "reasoning_tokens": None, "cost_usd": 0.0},
        "latency_s": round(latency, 3), "batched": batched,
        "tokens_per_s": round(tps, 1) if tps else None,
    }


# ----------------------------------------------------------------------------- OpenRouter (optional)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504}


class ProviderError(Exception):
    def __init__(self, status, body):
        super().__init__("HTTP %s: %s" % (status, str(body)[:300]))
        self.status = status
        self.body = body


def _reasoning_param(setting):
    s = str(setting).lower()
    if s in ("off", "false", "none", "disabled"):
        return {"enabled": False}
    if s in ("low", "medium", "high"):
        return {"effort": s}
    return None


def call_openrouter(model, prompt, settings):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ProviderError(0, "OPENROUTER_API_KEY is not set")
    body = {"model": model["slug"], "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(settings["max_tokens"]), "temperature": float(settings["temperature"]), "include_reasoning": True}
    if settings.get("seed") is not None:
        body["seed"] = int(settings["seed"])
    r = _reasoning_param(settings.get("reasoning", "default"))
    if r is not None:
        body["reasoning"] = r
    req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                                          "HTTP-Referer": "https://github.com/tanya-bas/misperception-bench", "X-Title": "misperception-bench v0"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=float(settings.get("timeout_s", 90))) as resp:
            status, data = resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ProviderError(e.code, e.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ProviderError(-1, repr(e))
    if "error" in data and not data.get("choices"):
        raise ProviderError(status, data["error"])
    choice = (data.get("choices") or [{}])[0]
    msg, usage = choice.get("message") or {}, data.get("usage") or {}
    return {"text": msg.get("content") or "", "reasoning": msg.get("reasoning") or "",
            "finish_reason": choice.get("finish_reason") or choice.get("native_finish_reason"),
            "usage": {"prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                      "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"), "cost_usd": usage.get("cost")},
            "latency_s": round(time.time() - t0, 3), "served_model": data.get("model"), "provider_name": data.get("provider")}


def call_anthropic(model, prompt, settings):
    # TODO: Claude models come in a later pass (anthropic SDK, output_config effort instead of temperature).
    raise NotImplementedError("anthropic provider is not implemented in v0; see RUNNING.md")


REMOTE_PROVIDERS = {"openrouter": call_openrouter, "anthropic": call_anthropic}


def call_with_retry(model, prompt, settings, tries=5, base_delay=2.0):
    fn = REMOTE_PROVIDERS[model["provider"]]
    last = None
    for attempt in range(tries):
        try:
            return fn(model, prompt, settings)
        except ProviderError as e:
            last = e
            if e.status not in RETRY_STATUSES and e.status != -1:
                raise
            time.sleep(min(base_delay * (2 ** attempt), 60))
    raise last
