# Score rules vs LLM vs LLM+grounding on the synthetic set. Writes results/summary.json and results/per_ticket.json.
import json, pathlib
from dataset import load, missing_fields
from rules import extract as rules_extract
from agent import normalise, ground, CACHE

FIELDS = ["outcome", "fault", "parts", "dbm", "signoff", "revisit"]
OUT = pathlib.Path(__file__).parent / "results"


def same(f, a, b):
    if f == "dbm":
        return (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 0.05)
    return a == b


def score(name, preds, gold):
    n = len(gold)
    field_ok = {f: sum(same(f, p[f], g[f]) for p, g in zip(preds, gold)) for f in FIELDS}
    all_ok = sum(all(same(f, p[f], g[f]) for f in FIELDS) for p, g in zip(preds, gold))
    # missing-data detection over (ticket, field) pairs
    tp = fp = fn = 0
    tickets_flag_ok = 0
    for p, g in zip(preds, gold):
        pm, gm = set(missing_fields(p)), set(g["missing"])
        tp += len(pm & gm); fp += len(pm - gm); fn += len(gm - pm)
        tickets_flag_ok += (pm == gm)
    # invented values: gold says not stated (null / empty), system filled something
    invented = sum((g[f] is None and p[f] is not None) for p, g in zip(preds, gold) for f in ("dbm", "signoff", "fault"))
    invented += sum(len(set(p["parts"]) - set(g["parts"])) for p, g in zip(preds, gold))
    gold_missing_total = sum(len(g["missing"]) for g in gold)
    return dict(system=name, n=n, field_correct=field_ok, record_exact=all_ok,
                missing=dict(tp=tp, fp=fp, fn=fn, gold_total=gold_missing_total,
                             tickets_needing_prompt=sum(bool(g["missing"]) for g in gold),
                             caught=tp, false_prompts=fp, tickets_flag_exact=tickets_flag_ok),
                invented_values=invented)


def main():
    gold = load()
    cache = json.loads(CACHE.read_text())
    rules = [rules_extract(g["note"]) for g in gold]
    llm = [normalise(cache[g["id"]]["raw"]) for g in gold]
    grounded, drops = zip(*[ground(p, g["note"]) for p, g in zip(llm, gold)])
    def trio(idx):
        pick = lambda xs: [xs[i] for i in idx]
        G = pick(gold)
        return [score("Rules baseline", pick(rules), G), score("LLM only", pick(llm), G),
                score("LLM + grounding check", pick(list(grounded)), G)]
    splits = {name: trio([i for i, g in enumerate(gold) if name == "all" or g["split"] == name])
              for name in ("all", "dev", "holdout")}
    res = splits["all"]
    lat = sorted(cache[g["id"]]["latency_s"] for g in gold)
    meta = dict(model=cache[gold[0]["id"]]["model"], median_latency_s=lat[len(lat) // 2],
                p90_latency_s=lat[int(len(lat) * 0.9)], grounding_drops=sum(len(d) for d in drops))
    OUT.mkdir(exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(dict(meta=meta, systems=res, splits=splits), indent=1))
    per = []
    for g, r, l, gr, d in zip(gold, rules, llm, grounded, drops):
        per.append(dict(id=g["id"], split=g["split"], note=g["note"], gold={k: g[k] for k in FIELDS + ["missing"]},
                        rules=dict(r, missing=missing_fields(r)), llm=dict(l, missing=missing_fields(l)),
                        grounded=dict(gr, missing=missing_fields(gr)), dropped=[list(x) for x in d],
                        evidence=cache[g["id"]]["raw"].get("evidence", {})))
    (OUT / "per_ticket.json").write_text(json.dumps(per, indent=1))
    for name, rs in splits.items():
      print("==", name)
      for s in rs:
        m = s["missing"]
        print(f'{s["system"]:24} exact {s["record_exact"]}/{s["n"]}  missing caught {m["caught"]}/{m["gold_total"]}  '
              f'false prompts {m["false_prompts"]}  invented {s["invented_values"]}  fields {s["field_correct"]}')
    print(meta)


if __name__ == "__main__":
    main()
