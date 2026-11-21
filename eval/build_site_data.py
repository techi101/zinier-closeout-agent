# Builds site/data.js from cached results so the live page needs no API key.
import json, pathlib
R = pathlib.Path(__file__).parent / "results"
summary = json.loads((R / "summary.json").read_text())
tickets = json.loads((R / "per_ticket.json").read_text())
HERO = json.loads((pathlib.Path(__file__).parent / "hero.json").read_text())
def get(split):
    d = {x["system"]: x for x in summary["splits"][split]}
    return d["Rules baseline"], d["LLM only"], d["LLM + grounding check"]
r, l, g = get("holdout")
ra, la, ga = get("all")
cleared_ok = sum(1 for t in tickets if t["split"] == "holdout" for d in t["dropped"]
                 if d[0] == "parts" and d[1] in t["gold"]["parts"])
finding = (f"On the {g['n']} holdout notes, written after the rules were frozen, the rules extractor got <b>{r['record_exact']}</b> records fully right "
           f"and asked {r['missing']['false_prompts']} wrong questions. The model alone got <b>{l['record_exact']}</b>, but it also invented "
           f"{l['invented_values']} values no note states, like a sign-off from \"customer satisfied\". The grounding check removed every invented value "
           f"and caught <b>{g['missing']['caught']} of {g['missing']['gold_total']}</b> missing fields.</p><p class=\"lede-2\">It had a cost: its own word list was too narrow for new words "
           f"like \"gateway\" and \"sleeve\", so it cleared {cleared_ok} correct parts and fully correct records fell to {g['record_exact']}. "
           f"So in the product I would ground only the fields where a guess does harm (light level, sign-off) and check parts against van stock. "
           f"</p><p class=\"fine\">Across all {ga['n']} notes: rules {ra['record_exact']}, model {la['record_exact']}, model plus check {ga['record_exact']} fully correct; "
           f"invented values {la['invented_values']} with the model alone, {ga['invented_values']} with the check.")
m = summary["meta"]
method = (f"Model: {m['model']} on the Gemini free tier, temperature 0, one call per note, median {m['median_latency_s']} s per call. "
          "The grounding check is about 30 lines of plain code after the model: it clears a value when the note has no words "
          "that support it, for example a light level whose number never appears, or a sign-off with no mention of signing. "
          "The policy that decides which fields are missing is the same function for every system, so the systems differ only in extraction.")
data = dict(summary=summary, tickets=tickets, hero=HERO, finding='<p class="lede-2">' + finding + "</p>", method=method)
out = pathlib.Path(__file__).parents[1] / "site" / "data.js"
out.write_text("window.CLOSEOUT = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
print(finding)
