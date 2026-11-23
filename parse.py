"""Extract one number in [0, 100] from a model reply.

Every prompt ends with "Reply with a single number from 0 to 100 and nothing else", but
models still add "%", words, ranges or a sentence of reasoning. Rules, in order:
  1. no digit at all -> "refusal" if a refusal phrase is present, else "unparseable"
  2. "1 in 10" style fraction -> 10, status "ok", note "fraction"
  3. range "20-30" / "20 to 30" / "between 20 and 30" -> midpoint, status "ok", note "range"
  4. otherwise take the LAST number in the reply (reasoning text tends to come first and
     the answer last): "about 25", "25%", "25.5" -> 25 / 25 / 25.5, status "ok"
  5. number outside [0, 100] -> status "out_of_range" (value kept for inspection)
Returns (value_or_None, status, note). Run `python3 parse.py` for the self-test.
"""
import re

NUM = r"(?<![\d.])(\d{1,3}(?:\.\d+)?)(?![\d])"  # 0-999 with optional decimals, not inside a longer number
RANGE = re.compile(NUM + r"\s*%?\s*(?:-|–|to)\s*" + NUM + r"\s*%?", re.I)
BETWEEN = re.compile(r"between\s+" + NUM + r"\s*%?\s*(?:and|-|–)\s*" + NUM, re.I)
FRACTION = re.compile(r"\b(\d{1,3})\s+in\s+(\d{1,4})\b", re.I)
REFUSAL_HINTS = ("i can't", "i cannot", "i'm unable", "i am unable", "not able to", "cannot provide",
                 "can't provide", "don't have", "do not have", "no reliable", "unable to provide",
                 "i'm sorry", "i am sorry", "as an ai")


def parse_number(text):
    """Return (value, status, note) for a reply string."""
    if text is None:
        return None, "unparseable", "empty"
    t = text.strip()
    if not t:
        return None, "unparseable", "empty"
    low = t.lower()
    if not re.search(r"\d", t):
        return None, ("refusal" if any(h in low for h in REFUSAL_HINTS) else "unparseable"), "no digits"
    m = FRACTION.search(t)
    if m and not re.search(NUM + r"\s*%", t):
        a, b = float(m.group(1)), float(m.group(2))
        if b > 0:
            return _check(100.0 * a / b, "fraction")
    m = BETWEEN.search(t) or RANGE.search(t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if a <= 100 and b <= 100:  # a date like 2024-10-04 would also match; both sides must be shares
            return _check((a + b) / 2.0, "range")
    nums = re.findall(NUM, t)
    if not nums:
        return None, "unparseable", "no standalone number"
    val = float(nums[-1])
    note = "last of %d numbers" % len(nums) if len(nums) > 1 else ""
    if any(h in low for h in REFUSAL_HINTS):
        note = (note + "; refusal wording present").strip("; ")
    return _check(val, note)


def _check(val, note):
    if 0.0 <= val <= 100.0:
        return val, "ok", note
    return val, "out_of_range", note


if __name__ == "__main__":
    cases = [
        ("25", (25.0, "ok")), ("25%", (25.0, "ok")), ("About 25.", (25.0, "ok")), ("25.5", (25.5, "ok")),
        ("Roughly 20-30%", (25.0, "ok")), ("between 10 and 20", (15.0, "ok")), ("20 to 30", (25.0, "ok")),
        ("I'd estimate the figure is around 14 percent.", (14.0, "ok")),
        ("The share is small, maybe 1 in 10.", (10.0, "ok")),
        ("I cannot provide that figure.", (None, "refusal")), ("", (None, "unparseable")),
        ("Sure thing!", (None, "unparseable")), ("150", (150.0, "out_of_range")),
        ("Immigrants are 15% of the US and 21% of Canada; for Japan the answer is 2", (2.0, "ok")),
        ("0", (0.0, "ok")), ("100", (100.0, "ok")), ("0.5", (0.5, "ok")),
    ]
    bad = 0
    for text, (v, s) in cases:
        got_v, got_s, note = parse_number(text)
        ok = got_s == s and (got_v == v or (got_v is not None and v is not None and abs(got_v - v) < 1e-9))
        bad += not ok
        print(("PASS" if ok else "FAIL"), repr(text), "->", got_v, got_s, note)
    print("%d/%d passed" % (len(cases) - bad, len(cases)))
    raise SystemExit(1 if bad else 0)
