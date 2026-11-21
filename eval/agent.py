# Close-out agent: LLM extraction (Gemini free tier) + deterministic grounding check + policy check.
# Raw model outputs are cached in results/llm_raw.json so the live page and re-scoring need no API key.
import json, os, re, sys, time, pathlib, urllib.request, urllib.error
from dataset import load, OUTCOMES, FAULTS, PARTS, REVISIT, missing_fields

MODEL = os.environ.get("CLOSEOUT_MODEL", "gemini-3.1-flash-lite")
CACHE = pathlib.Path(__file__).parent / "results" / "llm_raw.json"

SYSTEM = f"""You are the job close-out agent inside a field service platform for a fibre broadband operator.
A technician has just finished a visit and dictated a free-text note. Turn it into the job record.

Rules:
- Use only what the note states. If a field is not stated, return null. A null is useful: the agent will ask
  the technician for it before the job closes. A guessed value is harmful: it goes into SLA and billing reports.
- outcome: RESOLVED (fixed on this visit), REVISIT (another visit by us is needed), NO_ACCESS (could not start
  the work at the premises), ESCALATED (handed to network ops / NOC / engineering / civils as a wider fault).
- fault: the root cause, one of {FAULTS}.
- parts: parts fitted on this visit only, as SKU + quantity. SKUs: {PARTS}. DROP_CABLE_M quantity is metres.
  Do not list parts that were mentioned but not fitted.
- dbm: the final optical receive level at the ONT in dBm after the work (a negative number), or null.
- signoff: true if the customer signed, false if the note says they did not or could not sign, else null.
- revisit: if outcome is REVISIT, one of {REVISIT}; else null.
- evidence: for each non-null field, copy the shortest exact phrase from the note that states it.
Return JSON only, exactly this shape:
{{"outcome": str, "fault": str|null, "parts": [{{"sku": str, "qty": int}}], "dbm": number|null,
 "signoff": bool|null, "revisit": str|null,
 "evidence": {{"outcome": str|null, "fault": str|null, "parts": str|null, "dbm": str|null, "signoff": str|null, "revisit": str|null}}}}"""

NULLSTR = {"type": "STRING", "nullable": True}
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "outcome": {"type": "STRING", "enum": OUTCOMES},
        "fault": {"type": "STRING", "enum": FAULTS, "nullable": True},
        "parts": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "sku": {"type": "STRING", "enum": PARTS}, "qty": {"type": "INTEGER"}}, "required": ["sku", "qty"]}},
        "dbm": {"type": "NUMBER", "nullable": True},
        "signoff": {"type": "BOOLEAN", "nullable": True},
        "revisit": {"type": "STRING", "enum": REVISIT, "nullable": True},
        "evidence": {"type": "OBJECT", "properties": {k: NULLSTR for k in
                     ["outcome", "fault", "parts", "dbm", "signoff", "revisit"]}},
    },
    "required": ["outcome", "fault", "parts", "dbm", "signoff", "revisit", "evidence"],
}


def call_gemini(note: str) -> tuple[dict, float]:
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    body = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": f"Technician note:\n{note}"}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                                                  "thinkingConfig": {"thinkingLevel": os.environ.get("CLOSEOUT_THINKING", "low")}}}
    for attempt in range(6):
        t0 = time.time()
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            txt = [p["text"] for p in d["candidates"][0]["content"]["parts"] if "text" in p and not p.get("thought")][-1]
            return json.loads(txt), round(time.time() - t0, 2)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            print(f"  HTTP {e.code} attempt {attempt}: {msg}", file=sys.stderr)
            if e.code in (429, 500, 503): time.sleep(20 * (attempt + 1)); continue
            raise
        except (TimeoutError, urllib.error.URLError) as e:
            print(f"  network {e!r} attempt {attempt}", file=sys.stderr); time.sleep(10); continue
    raise RuntimeError("gave up")


def normalise(raw: dict) -> dict:
    parts = {}
    for p in raw.get("parts") or []:
        parts[p["sku"]] = parts.get(p["sku"], 0) + int(p["qty"])
    dbm = raw.get("dbm")
    return dict(outcome=raw.get("outcome"), fault=raw.get("fault"), parts=parts,
                dbm=None if dbm is None else -abs(round(float(dbm), 1)),
                signoff=raw.get("signoff"), revisit=raw.get("revisit") if raw.get("outcome") == "REVISIT" else None)


WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty".split()
PART_WORDS = {"ONT": r"\bont\b", "ROUTER": r"router|hub", "PSU": r"psu|power supply|power brick",
              "PATCH_CORD": r"patch", "DROP_CABLE_M": r"drop|metre|meter|\dm\b", "CONNECTOR": r"connector|re-?terminat",
              "SPLICE_PROTECTOR": r"splice protector", "FACEPLATE": r"faceplate"}


def ground(rec: dict, note: str) -> tuple[dict, list]:
    """Deterministic check: drop any value the note does not actually support. Returns (record, list of drops)."""
    t, rec, drops = note.lower(), json.loads(json.dumps(rec)), []
    if rec["dbm"] is not None:
        whole = int(abs(rec["dbm"]))
        spelled = [w for w in WORDS if w in t]
        if not (str(abs(rec["dbm"])).rstrip("0").rstrip(".") in t or str(whole) in t or
                (whole >= 20 and "twenty" in t) or (10 <= whole < 20 and WORDS[whole] in spelled) or
                (whole >= 30 and "thirty" in t)):
            drops.append(("dbm", rec["dbm"])); rec["dbm"] = None
    if rec["signoff"] is not None and not re.search(r"sign|\bsig\b", t):
        drops.append(("signoff", rec["signoff"])); rec["signoff"] = None
    for sku in list(rec["parts"]):
        if not re.search(PART_WORDS[sku], t):
            drops.append(("parts", sku)); rec["parts"].pop(sku)
    return rec, drops


def run_all():
    CACHE.parent.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    for r in load():
        if r["id"] in cache: continue
        raw, secs = call_gemini(r["note"])
        cache[r["id"]] = {"raw": raw, "latency_s": secs, "model": MODEL}
        CACHE.write_text(json.dumps(cache, indent=1))
        print(r["id"], secs, raw.get("outcome"), raw.get("fault"))
        time.sleep(6.5)  # stay under free-tier requests-per-minute
    return cache


if __name__ == "__main__":
    run_all()
