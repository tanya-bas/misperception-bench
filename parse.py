"""Extract one number in [0, 100] from a model reply.

Every prompt ends with "Reply with a single number from 0 to 100 and nothing else", but
models still add "%", words, ranges or a sentence of reasoning. Rules, in order:
  1. no digit at all -> "refusal" if a decline phrase is present (apology, inability, "don't have
     that figure"; typographic apostrophes are folded to ASCII first), else "unparseable"
  2. "1 in 10" style fraction -> 10, status "ok", note "fraction"
  3. range "20-30" / "20 to 30" / "between 20 and 30" -> midpoint, status "ok", note "range"
  4. otherwise take the LAST number in the reply (reasoning text tends to come first and
     the answer last): "about 25", "25%", "25.5" -> 25 / 25 / 25.5, status "ok"
  5. number outside [0, 100] -> status "out_of_range" (value kept for inspection)
Returns (value_or_None, status, note). Run `python3 parse.py` for the self-test.

parse_option(text, choices) does the same for the categorical track, where the reply should be the
letter of one option: choices is a list of (letter, option, label). Rules, in order:
  1. a bare letter ("B", "b)", "(B)", "B.", "B. Lebanon") -> that option, status "ok"
  2. otherwise the option text or its label found in the reply (case-insensitive; True/False
     also match "true"/"false" as whole words) -> that option; several matches -> the earliest
     one, note "multiple matches"
  3. nothing matched -> "refusal" if a decline phrase is present, else "unparseable"
Returns (option_or_None, status, note).
"""
import re

NUM = r"(?<![\d.])(\d{1,3}(?:\.\d+)?)(?![\d])"  # 0-999 with optional decimals, not inside a longer number
RANGE = re.compile(NUM + r"\s*%?\s*(?:-|–|to)\s*" + NUM + r"\s*%?", re.I)
BETWEEN = re.compile(r"between\s+" + NUM + r"\s*%?\s*(?:and|-|–)\s*" + NUM, re.I)
FRACTION = re.compile(r"\b(\d{1,3})\s+in\s+(\d{1,4})\b", re.I)
REFUSAL_HINTS = ("i can't", "i cannot", "i'm unable", "i am unable", "not able to", "cannot provide",
                 "can't provide", "can't help", "cannot help", "don't have", "do not have", "no reliable",
                 "unable to provide", "i'm sorry", "i am sorry", "as an ai", "no data", "no information",
                 "not available", "don't know", "do not know")
# Models often emit typographic apostrophes and quotes ("I’m sorry"); fold them to ASCII before matching.
APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'", "\u201c": '"', "\u201d": '"'}


def _normalize(text):
    for k, v in APOSTROPHES.items():
        text = text.replace(k, v)
    return text


def parse_number(text):
    """Return (value, status, note) for a reply string."""
    if text is None:
        return None, "unparseable", "empty"
    t = _normalize(text).strip()
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



LETTER_RE = re.compile(r"^\s*\(?([A-Ha-h])\)?[\s.:)\-]*(?:$|[A-Za-z\u201c\"'])")


def parse_option(text, choices):
    """Return (option, status, note) for a categorical reply; choices = [(letter, option, label), ...]."""
    if text is None:
        return None, "unparseable", "empty"
    t = _normalize(text).strip()
    if not t:
        return None, "unparseable", "empty"
    low = t.lower()
    m = LETTER_RE.match(t)
    if m:
        letter = m.group(1).upper()
        for L, opt, _ in choices:
            if L == letter:
                return opt, "ok", "letter"
    hits = []  # (position, option)
    for L, opt, label in choices:
        for cand in {opt, label}:
            pat = r"\b%s\b" % re.escape(cand.lower()) if cand.lower() in ("true", "false", "yes", "no", "higher", "lower") else re.escape(cand.lower())
            mm = re.search(pat, low)
            if mm:
                hits.append((mm.start(), opt))
    if hits:
        hits.sort()
        uniq = []
        for pos, opt in hits:
            if opt not in uniq:
                uniq.append(opt)
        return uniq[0], "ok", ("text match" if len(uniq) == 1 else "multiple matches, earliest kept")
    return None, ("refusal" if any(h in low for h in REFUSAL_HINTS) else "unparseable"), "no option matched"

if __name__ == "__main__":
    cases = [
        ("25", (25.0, "ok")), ("25%", (25.0, "ok")), ("About 25.", (25.0, "ok")), ("25.5", (25.5, "ok")),
        ("Roughly 20-30%", (25.0, "ok")), ("between 10 and 20", (15.0, "ok")), ("20 to 30", (25.0, "ok")),
        ("I'd estimate the figure is around 14 percent.", (14.0, "ok")),
        ("The share is small, maybe 1 in 10.", (10.0, "ok")),
        ("I cannot provide that figure.", (None, "refusal")), ("", (None, "unparseable")),
        ("I\u2019m sorry, but I can\u2019t provide that.", (None, "refusal")),
        ("I\u2019m sorry, but I can\u2019t help with that.", (None, "refusal")),
        ("I\u2019m sorry, but I don\u2019t have that specific figure.", (None, "refusal")),
        ("I don\u2019t have any details about that specific survey question or its results.", (None, "refusal")),
        ("   ", (None, "unparseable")),
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
    choices = [("A", "True", "True"), ("B", "False", "False")]
    choices3 = [("A", "Germany", "Germany"), ("B", "Lebanon", "Lebanon"), ("C", "Sweden", "Sweden")]
    choices_lab = [("A", "Plane ranked 1 (most)", "The plane emits the most"), ("B", "Plane not ranked 1", "The plane does not emit the most")]
    ocases = [
        ("B", choices, ("False", "ok")), ("b)", choices, ("False", "ok")), ("(A)", choices, ("True", "ok")), ("A.", choices, ("True", "ok")),
        ("B. Lebanon", choices3, ("Lebanon", "ok")), ("Lebanon", choices3, ("Lebanon", "ok")),
        ("The statement is false.", choices, ("False", "ok")), ("It is false, not true.", choices, ("False", "ok")),
        ("The plane emits the most", choices_lab, ("Plane ranked 1 (most)", "ok")),
        ("I'm sorry, but I can't help with that.", choices3, (None, "refusal")), ("", choices, (None, "unparseable")),
        ("Sure thing!", choices3, (None, "unparseable")), ("C", choices, (None, "unparseable")),
    ]
    for text, ch, (v, st) in ocases:
        got_v, got_s, note = parse_option(text, ch)
        ok = got_s == st and got_v == v
        bad += not ok
        print(("PASS" if ok else "FAIL"), "option", repr(text), "->", got_v, got_s, note)
    print("%d/%d passed" % (len(cases) + len(ocases) - bad, len(cases) + len(ocases)))
    raise SystemExit(1 if bad else 0)
