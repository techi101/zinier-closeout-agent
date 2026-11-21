# Rules baseline: the keyword + regex extractor a team would ship first (no ML).
import re

WORDNUM = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
           "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30}

FAULT_KW = [  # first match wins, ordered most specific first
    ("OUTAGE", r"outage|whole street|area wide|lost power"),
    ("CABINET_PORT", r"cab(inet)? port|port at the cab|cabinet"),
    ("FIBRE_BREAK", r"fibre break|break|snapped|splic"),
    ("DROP_DAMAGE", r"\bdrop\b"),
    ("DIRTY_CONNECTOR", r"dirty|clean(ed)? (the )?connector|filthy"),
    ("INTERNAL_CABLING", r"faceplate|patch (lead|cord)|internal"),
    ("PSU_FAULT", r"\bpsu\b|power supply|power brick"),
    ("ONT_FAULT", r"\bont\b.*(dead|faulty|replac|swap)|(replac|swap)\w* (the )?ont"),
    ("ROUTER_FAULT", r"router|hub|boot loop|firmware"),
    ("WIFI_CONFIG", r"wi-?fi|channel|band steering|mesh|extender|5ghz"),
    ("NO_FAULT_FOUND", r"no fault found|\bnff\b"),
]

PART_KW = {
    "ONT": r"(replac|swap|install|new)\w*[^.]{0,25}\bont\b|\bont\b (replaced|swapped)",
    "ROUTER": r"(replac|swap|new)\w*[^.]{0,25}\b(router|hub)\b|\brouter (replaced|swapped)",
    "PSU": r"(new|swap|replac|fitted)\w*[^.]{0,15}\b(psu|power supply)\b|\bpsu\b (fitted|replaced)",
    "PATCH_CORD": r"(\d+|a|one|two|new)?\s*patch (lead|cord)s?",
    "CONNECTOR": r"(\d+|a|one|two|new)?\s*(field )?connectors?\b",
    "SPLICE_PROTECTOR": r"(\d+|one|two|three|four)?\s*splice protectors?",
    "FACEPLATE": r"(new|replac)\w*[^.]{0,15}faceplate",
    "DROP_CABLE_M": r"(\d+)\s*(m|metres|meters)\b",
}


def _num(tok):
    if tok is None: return 1
    tok = tok.strip().lower()
    if tok.isdigit(): return int(tok)
    return WORDNUM.get(tok, 1)


def extract(note: str) -> dict:
    t = note.lower()
    # outcome
    if re.search(r"escalat|raised to network|passed (it )?to (noc|network|civils)|\bnoc\b", t):
        outcome = "ESCALATED"
    elif re.search(r"not in|no answer|nobody home|no-one in|no one in|access refused|access denied|no access|cancelled|locked|asked me to leave|card left|left (a )?card", t):
        outcome = "NO_ACCESS"
    elif re.search(r"back tomorrow|back tmrw|rebook|coming back|come back|needs civils|need civils|permission|two man|2 person|wayleave", t):
        outcome = "REVISIT"
    else:
        outcome = "RESOLVED"
    # fault
    fault = None
    if outcome != "NO_ACCESS":
        for code, pat in FAULT_KW:
            if re.search(pat, t):
                fault = code; break
    # parts (skip negated mentions like "didnt need it")
    parts = {}
    if outcome in ("RESOLVED", "REVISIT"):
        for sku, pat in PART_KW.items():
            m = re.search(pat, t)
            if not m: continue
            window = t[max(0, m.start() - 30): m.end() + 30]
            if re.search(r"didnt need|didn't need|not replaced|ran out|didnt have|ordered", window): continue
            if sku == "DROP_CABLE_M":
                if "drop" in t: parts[sku] = int(m.group(1))
                continue
            if sku in ("PATCH_CORD", "CONNECTOR", "SPLICE_PROTECTOR"):
                if not re.search(r"replac|new|fitted|used|added|swap|\d", m.group(0) + window): continue
                parts[sku] = _num(m.group(1))
            else:
                parts[sku] = 1
    # optical reading: last "-dd.d" or "minus <words>" in the note
    dbm = None
    nums = re.findall(r"(?<![\w.])-\s?(\d{2}(?:\.\d)?)", t)
    if nums:
        dbm = -float(nums[-1])
    else:
        m = re.findall(r"minus (\w+)(?: (one|two|three|four|five|six|seven|eight|nine))?(?: point (\w+))?", t)
        vals = []
        for a, b, c in m:
            if a in WORDNUM:
                v = WORDNUM[a] + (WORDNUM.get(b, 0) if b else 0) + (WORDNUM.get(c, 0) / 10 if c else 0)
                if v >= 10: vals.append(-v)
        if vals: dbm = vals[-1]
    # signoff
    signoff = None
    if re.search(r"refused to sign|did not sign|didnt sign|no sig|no signature|wasnt around to sign|not around to sign", t):
        signoff = False
    elif re.search(r"\bsigned|signature|\bsig\b", t):
        signoff = True
    # revisit reason
    revisit = None
    if outcome == "REVISIT":
        for code, pat in [("CIVILS", r"civils|dig"), ("PERMISSION", r"permission|landlord|wayleave"),
                          ("SECOND_TECH", r"two man|2 person|second tech|cherry picker|ladder"),
                          ("PARTS", r"ran out|dont have|didnt have|don't have|ordered|not enough"),
                          ("CUSTOMER_UNAVAILABLE", r"customer (had to|needed to) leave|wasnt there|wasn't there")]:
            if re.search(pat, t): revisit = code; break
        revisit = revisit or "OTHER"
    return dict(outcome=outcome, fault=fault, parts=parts, dbm=dbm, signoff=signoff, revisit=revisit)
