(() => {
const D = window.CLOSEOUT;
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

const FIELDS = [
  {k:"outcome", label:"Outcome", c:"--f-outcome"},
  {k:"fault", label:"Root cause", c:"--f-fault"},
  {k:"parts", label:"Parts fitted", c:"--f-parts"},
  {k:"dbm", label:"Light level at ONT", c:"--f-dbm"},
  {k:"signoff", label:"Customer sign-off", c:"--f-signoff"},
  {k:"revisit", label:"Revisit reason", c:"--f-revisit"},
];
const ASK = {
  fault: "What was the root cause? Pick one from the list.",
  dbm: "What did the ONT read after the fix, in dBm?",
  signoff: "Did the customer sign? If not, why not?",
  revisit: "Why does this job need another visit?",
};
const pretty = s => s ? s.toLowerCase().replace(/_/g, " ").replace(/\bont\b/g,"ONT").replace(/\bpsu\b/g,"PSU").replace(/\bnoc\b/g,"NOC").replace(/^./, c => c.toUpperCase()) : s;
function fmt(k, v){
  if (k === "parts") { const e = Object.entries(v||{}); return e.length ? e.map(([s,q]) => s === "DROP_CABLE_M" ? `Drop cable ${q} m` : `${pretty(s)} x${q}`).join(", ") : "None"; }
  if (k === "dbm") return v == null ? null : `${v.toFixed(1)} dBm`;
  if (k === "signoff") return v == null ? null : (v ? "Signed" : "Not signed");
  return v == null ? null : pretty(v);
}

/* ---------- ribbon: 8 fibre-colour strands bleeding off the right edge ---------- */
(function ribbon(){
  const svg = $("#ribbon"); if (!svg) return;
  const cols = ["#2F6BD8","#FF4C24","#2E9D5B","#8A5A3B","#8F9BA8","#7D4CC8","#D9557E","#138F98"];
  let html = "";
  cols.forEach((c, i) => {
    const y0 = 40 + i*9, y1 = 470 + i*5;
    html += `<path d="M 900 ${y0} C 620 ${y0+30}, 520 ${y1-180}, 120 ${y1}" stroke="${c}" stroke-width="${i%3?3:4}" fill="none" stroke-linecap="round" opacity=".9"/>`;
  });
  svg.innerHTML = html;
})();

/* ---------- hero console ---------- */
const wave = $("#wave");
for (let i = 0; i < 64; i++) { const b = document.createElement("i"); b.style.height = (6 + Math.abs(Math.sin(i*1.7)*Math.cos(i*.37))*28) + "px"; wave.appendChild(b); }

const heroTickets = D.hero.map(h => ({...h, t: D.tickets.find(t => t.id === h.id)}));
const tabs = $("#tabs");
heroTickets.forEach((h, i) => {
  const b = document.createElement("button");
  b.className = "tab"; b.type = "button"; b.role = "tab"; b.textContent = h.label;
  b.setAttribute("aria-selected", i === 0 ? "true" : "false");
  b.onclick = () => { tabs.querySelectorAll(".tab").forEach(x => x.setAttribute("aria-selected","false")); b.setAttribute("aria-selected","true"); play(i); };
  tabs.appendChild(b);
});
$("#replay").onclick = () => play(cur);

let cur = 0, timers = [];
const later = (fn, ms) => timers.push(setTimeout(fn, still ? 0 : ms));

function findSpan(note, phrase){
  if (!phrase) return null;
  const i = note.toLowerCase().indexOf(phrase.toLowerCase().trim());
  return i < 0 ? null : [i, i + phrase.trim().length];
}

function play(idx){
  cur = idx; timers.forEach(clearTimeout); timers = [];
  const h = heroTickets[idx], t = h.t, rec = t.grounded, ev = t.evidence || {};
  $("#jobTitle").textContent = `Job ${h.job}, ${h.kind}, close-out`;
  // note with marks for grounded, non-null fields
  const spans = [];
  ["fault","parts","dbm","signoff","revisit"].map(k => FIELDS.find(f => f.k === k)).forEach(f => {
    const v = rec[f.k];
    const has = f.k === "parts" ? Object.keys(v||{}).length : v != null;
    if (!has) return;
    const sp = findSpan(t.note, ev[f.k]);
    if (sp && !spans.some(s => sp[0] < s.e && sp[1] > s.s)) spans.push({s:sp[0], e:sp[1], f});
  });
  (t.dropped || []).forEach(d => {
    const f = FIELDS.find(x => x.k === d[0]); const sp = findSpan(t.note, ev[d[0]]);
    if (f && sp && !spans.some(s => sp[0] < s.e && sp[1] > s.s)) spans.push({s:sp[0], e:sp[1], f, doubt:true});
  });
  spans.sort((a,b) => a.s - b.s);
  let html = "", p = 0;
  spans.forEach(s => { html += esc(t.note.slice(p, s.s)) + `<mark data-k="${s.f.k}"${s.doubt?' class="doubt"':""} style="--c:var(${s.doubt?"--ask":s.f.c})">${esc(t.note.slice(s.s, s.e))}</mark>`; p = s.e; });
  html += esc(t.note.slice(p));
  $("#note").innerHTML = html;
  wave.classList.add("live");
  // record rows (revisit only shown for REVISIT)
  const rows = FIELDS.filter(f => f.k !== "revisit" || rec.outcome === "REVISIT");
  const missing = new Set(rec.missing);
  $("#rec").innerHTML = rows.map(f => `<dt style="--c:var(${f.c})" data-k="${f.k}">${f.label}</dt><dd data-k="${f.k}"></dd>`).join("");
  $("#recState").textContent = "filling";
  $("#asks").hidden = true; $("#dropped").hidden = true;
  $("#strands").innerHTML = "";
  const dropped = t.dropped || [];
  rows.forEach((f, i) => {
    later(() => {
      const dd = $(`#rec dd[data-k="${f.k}"]`);
      const v = fmt(f.k, rec[f.k]);
      const drop = dropped.find(d => d[0] === f.k);
      let inner;
      if (v != null) inner = `<span class="val">${esc(v)}</span>`;
      else if (missing.has(f.k)) inner = `<span class="val empty">Needs input</span>`;
      else inner = `<span class="val na">Not required for this job</span>`;
      if (drop) inner += ` <span class="val strike" title="Removed by the grounding check">model said ${esc(drop[0] === "signoff" ? (drop[1] ? "signed" : "not signed") : drop[0] === "dbm" ? drop[1] + " dBm" : pretty(String(drop[1])))}</span>`;
      dd.innerHTML = inner;
      requestAnimationFrame(() => dd.querySelectorAll(".val").forEach(x => x.classList.add("in")));
      const m = document.querySelector(`#note mark[data-k="${f.k}"]`);
      if (m) { m.classList.add("on"); strand(m, $(`#rec dt[data-k="${f.k}"]`), m.classList.contains("doubt") ? "--ask" : f.c, m.classList.contains("doubt")); }
    }, 450 + i * 330);
  });
  later(() => {
    wave.classList.remove("live");
    $("#recState").textContent = missing.size ? `${missing.size} field${missing.size>1?"s":""} missing` : "ready to close";
    if (missing.size) { $("#askList").innerHTML = [...missing].map(k => `<li>${ASK[k]}</li>`).join(""); $("#asks").hidden = false; }
    if (dropped.length) {
      $("#dropped").textContent = `The grounding check removed ${dropped.length} value${dropped.length>1?"s":""} the model filled in but the note never says. ${h.why || ""}`;
      $("#dropped").hidden = false;
    }
  }, 450 + rows.length * 330 + 200);
}

function strand(fromEl, toEl, colorVar, dashed){
  const svg = $("#strands"); if (!fromEl || !toEl || getComputedStyle(svg).display === "none") return;
  const box = $("#stage").getBoundingClientRect();
  const rs = fromEl.getClientRects(), a = rs[rs.length - 1] || fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const np = document.querySelector(".note-pane").getBoundingClientRect();
  const x1 = np.right - box.left + 6, y1 = a.top + a.height/2 - box.top;
  const x2 = b.left - box.left - 8, y2 = b.top + b.height/2 - box.top;
  const mx = (x1 + x2) / 2;
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", `M${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`);
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  dot.setAttribute("cx", x1); dot.setAttribute("cy", y1); dot.setAttribute("r", 3.5);
  dot.setAttribute("fill", getComputedStyle(document.documentElement).getPropertyValue(colorVar).trim()); svg.appendChild(dot);
  p.setAttribute("stroke", getComputedStyle(document.documentElement).getPropertyValue(colorVar).trim());
  svg.appendChild(p);
  const L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
  p.getBoundingClientRect();
  if (dashed) { p.style.strokeDasharray = "5 5"; p.style.strokeDashoffset = 0; return; }
  p.style.transition = still ? "none" : "stroke-dashoffset .7s cubic-bezier(.16,1,.3,1)"; p.style.strokeDashoffset = 0;
}
addEventListener("resize", () => { clearTimeout(window.__rz); window.__rz = setTimeout(() => play(cur), 200); });
document.fonts.ready.then(() => play(0));

/* ---------- results ---------- */
const S = D.summary;
$("#finding").innerHTML = D.finding;
const SPLITS = {holdout:"Holdout 32, written after the rules froze", all:"All 112 notes", dev:"First 80"};
function drawCharts(split){
  const sys = S.splits[split], N = sys[0].n, gm = sys[0].missing.gold_total;
  const charts = [
    {title:"Job records fully correct", sub:`all 6 fields right, out of ${N} notes`, get:s => s.record_exact, max:N, best:"max"},
    {title:"Missing fields caught", sub:`out of ${gm} required fields the notes never state`, get:s => s.missing.caught, max:gm, best:"max"},
    {title:"Wrong questions", sub:"asks the technician for something already said, or not required (lower is better)", get:s => s.missing.false_prompts, max:Math.max(...sys.map(s=>s.missing.false_prompts),1), best:"min"},
    {title:"Invented values", sub:"filled in although the note never says it (lower is better)", get:s => s.invented_values, max:Math.max(...sys.map(s=>s.invented_values),1), best:"min"},
  ];
  $("#charts").innerHTML = charts.map(c => {
    const vals = sys.map(c.get), bestV = c.best === "max" ? Math.max(...vals) : Math.min(...vals);
    return `<figure class="chart" style="margin:0"><h3>${c.title}</h3><p>${c.sub}</p>${sys.map((s,i) => {
      const v = vals[i], w = Math.max(.5, v / c.max * 74);
      return `<div class="bar-row${v===bestV?" best":""}" title="${esc(s.system)}: ${v}${c.best==="max"?" of "+c.max:""}"><span>${esc(s.system)}</span><div class="bar-track"><div class="bar" style="width:${w}%"></div><span class="bar-lab" style="left:${w}%">${v}${c.best==="max"?" / "+c.max:""}</span></div></div>`;
    }).join("")}</figure>`;
  }).join("");
}
$("#splitCtl").innerHTML = Object.entries(SPLITS).map(([k,v],i) => `<button type="button" class="chip${i===0?" on":""}" data-split="${k}">${v}</button>`).join("");
$("#splitCtl").querySelectorAll(".chip").forEach(b => b.onclick = () => { $("#splitCtl").querySelectorAll(".chip").forEach(x => x.classList.remove("on")); b.classList.add("on"); drawCharts(b.dataset.split); });
drawCharts("holdout");
$("#method").innerHTML = D.method;

/* explorer */
const FK = ["outcome","fault","parts","dbm","signoff","revisit"];
const eq = (k,a,b) => k === "parts" ? JSON.stringify(Object.entries(a||{}).sort()) === JSON.stringify(Object.entries(b||{}).sort()) : k === "dbm" ? (a==null&&b==null)||(a!=null&&b!=null&&Math.abs(a-b)<.05) : a === b;
function sysCol(name, r, g){
  const bad = FK.filter(k => !eq(k, r[k], g[k]));
  const mi = (r.missing||[]).join(", ") || "nothing";
  return `<div><h4>${name}</h4><ul>${bad.length ? bad.map(k => `<li class="bad">${FIELDS.find(f=>f.k===k).label}: ${esc(fmt(k,r[k]) ?? "blank")}</li>`).join("") : "<li>All fields right</li>"}<li>Asks for: ${esc(mi)}</li></ul></div>`;
}
function renderList(f){
  let list = D.tickets;
  if (f === "missing") list = list.filter(t => t.gold.missing.length);
  if (f === "interesting") list = list.filter(t => ["rules","llm","grounded"].some(s => FK.some(k => !eq(k, t[s][k], t.gold[k]))));
  $("#exList").innerHTML = list.map(t => `<div class="ex-item"><div class="ex-id">${t.id}${t.split==="holdout"?"<br>holdout":""}</div><div><p class="ex-note">${esc(t.note)}</p><div class="ex-grid">
    <div><h4>Gold label</h4><ul>${FK.filter(k => k!=="revisit" || t.gold.outcome==="REVISIT").map(k => `<li>${FIELDS.find(x=>x.k===k).label}: ${esc(fmt(k,t.gold[k]) ?? "not stated")}</li>`).join("")}<li>Missing: ${esc(t.gold.missing.join(", ") || "nothing")}</li></ul></div>
    ${sysCol("Rules", t.rules, t.gold)}${sysCol("LLM only", t.llm, t.gold)}${sysCol("LLM + grounding", t.grounded, t.gold)}</div></div></div>`).join("") || "<p>No notes in this view.</p>";
}
document.querySelectorAll(".ex-controls .chip").forEach(c => c.onclick = () => { document.querySelectorAll(".ex-controls .chip").forEach(x => x.classList.remove("on")); c.classList.add("on"); renderList(c.dataset.f); });
renderList("interesting");

/* ---------- epics ---------- */
const EPICS = [
 {key:"ZCO-1", title:"Close-out extraction you can trust", why:"Technicians describe the job in their own words and get a filled record. Every value can be traced to what they said.", stories:[
  {key:"ZCO-11", pts:8, s:"As a field technician, I want to describe the job by voice or text and see the job record filled in, so that I can close the job without a long form.", ac:[
   "<b>Given</b> a fibre repair task in progress, <b>when</b> I submit a note, <b>then</b> outcome, root cause, parts, light level and sign-off are filled within 3 s at p90.",
   "<b>Given</b> a filled value, <b>when</b> I tap it, <b>then</b> I see the exact words in my note it came from.",
   "<b>Given</b> a filled record, <b>then</b> nothing is submitted until I tap Confirm, and every edit I make is logged as <code>closeout_field_edited</code>."]},
  {key:"ZCO-12", pts:5, s:"As an operations manager, I want the agent never to file a value the technician did not say, so that SLA and billing reports stay true.", ac:[
   "<b>Given</b> a light level or sign-off with no supporting words in the note, <b>when</b> the grounding check runs, <b>then</b> the value is cleared and the field becomes a question.",
   "<b>Given</b> parts the model extracted, <b>then</b> they are checked against van stock and the task's job type, not against a word list, because the word-list check cleared 7 correct parts on the holdout notes.",
   "<b>Then</b> <code>closeout_value_dropped</code> is logged with field, model value and rule name.",
   "<b>Given</b> the 112-note test set, <b>then</b> invented values are 0 before release."]},
  {key:"ZCO-13", pts:5, s:"As a stores controller, I want confirmed parts to come off the technician's van stock, so that stock matches reality.", ac:[
   "<b>Given</b> confirmed parts, <b>when</b> the job is submitted, <b>then</b> a consumption line is created against the task and the van.",
   "<b>Given</b> a part not in the van's stock, <b>then</b> the technician is asked to confirm before submit."]}]},
 {key:"ZCO-2", title:"Ask only for what is missing", why:"A policy says which fields each outcome needs. The agent asks one short question per gap instead of showing the whole form.", stories:[
  {key:"ZCO-21", pts:5, s:"As a solution consultant, I want to set required fields per job type and outcome in Studio, so that each customer's rules apply without a release.", ac:[
   "<b>Given</b> a policy change, <b>when</b> it is saved, <b>then</b> the next session uses it and every event carries <code>policy_version</code>.",
   "<b>Given</b> an invalid policy (unknown field), <b>then</b> save is blocked with the field named."]},
  {key:"ZCO-22", pts:3, s:"As a technician, I want the agent to ask me one question at a time for missing fields, so that I can answer by voice with my hands busy.", ac:[
   "<b>Given</b> missing required fields, <b>then</b> questions come one at a time, at most 3, in policy order.",
   "<b>Given</b> I answer \"don't know\", <b>then</b> the job can close only as not resolved, or with a supervisor override that is logged."]}]},
 {key:"ZCO-3", title:"Measure it like a product", why:"If we cannot see corrections, we cannot tell whether the agent is helping.", stories:[
  {key:"ZCO-31", pts:3, s:"As the product lead, I want every close-out session to emit the events below, so that quality is visible from week one.", ac:[
   "<b>Given</b> any session, <b>then</b> <code>closeout_session_started</code> and either <code>closeout_submitted</code> or <code>closeout_abandoned</code> are emitted.",
   "<b>Then</b> events are checked against the schema in CI and land in the warehouse within 15 minutes."]},
  {key:"ZCO-32", pts:5, s:"As the product lead, I want back-office corrections to become labelled test cases, so that each model or prompt change is tested on real jobs.", ac:[
   "<b>Given</b> a back-office edit to an agent-filled field within 7 days, <b>then</b> the note and corrected value join the golden set.",
   "<b>Given</b> a new model or prompt version, <b>then</b> it ships only if no field drops more than 2 points on the golden set."]}]},
];
$("#epicList").innerHTML = EPICS.map(e => `<div class="epic"><div class="epic-h"><span class="key">${e.key}</span><h3>${e.title}</h3></div><p>${e.why}</p>${e.stories.map((s,i) => `<details class="story"${i===0&&e.key==="ZCO-1"?" open":""}><summary><span class="skey">${s.key}</span><span>${s.s}</span><span class="pts">${s.pts} pts</span></summary><div class="ac"><h4>Acceptance criteria</h4><ol>${s.ac.map(a => `<li>${a}</li>`).join("")}</ol></div></details>`).join("")}</div>`).join("");

/* ---------- data spec ---------- */
const SPEC = [
 ["outcome","Enum: resolved, revisit, no access, escalated","Always","Note","Task status"],
 ["fault","Enum, 11 fault codes","Resolved, revisit, escalated","Note","Task fault code"],
 ["parts","List of SKU and quantity (drop cable in metres)","Never required; 'none' is a valid answer","Note, checked against van stock","Parts consumption, van stock"],
 ["dbm","Number, dBm","Resolved fibre faults and no-fault-found","Note, later the ONT reading over the network","Task test results, asset history"],
 ["signoff","Yes, no, or reason","Resolved","Note or signature capture","Task, customer record"],
 ["revisit","Enum: parts, customer unavailable, civils, permission, second tech, other","Revisit","Note","Follow-up task, scheduling"],
];
$("#fieldRows").innerHTML = SPEC.map(r => `<tr><td><span class="sw" style="--c:var(${FIELDS.find(f=>f.k===r[0]).c})"></span>${FIELDS.find(f=>f.k===r[0]).label}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td></tr>`).join("");

/* ---------- analytics ---------- */
const METRICS = [
 ["Back-office correction rate","Agent-filled fields changed in the office within 7 days, divided by agent-filled fields submitted. The north star; lower is better.",["closeout_submitted","closeout_backoffice_corrected"]],
 ["Auto-fill rate","Required fields the agent filled and the technician confirmed unchanged, divided by required fields.",["closeout_field_extracted","closeout_field_edited","closeout_submitted"]],
 ["Technician correction rate","Agent values the technician changed before submit, divided by agent values shown.",["closeout_field_extracted","closeout_field_edited"]],
 ["Missing-data prompt rate","Sessions with at least one question, and the share of questions answered.",["closeout_prompt_shown","closeout_prompt_answered"]],
 ["Fallback rate","Sessions where the technician left the agent for the full form, or abandoned.",["closeout_fallback_to_form","closeout_abandoned"]],
 ["Time to close","Median seconds from note submitted to job submitted, compared with the form for the same job type.",["closeout_note_submitted","closeout_submitted"]],
 ["Dropped-value rate","Values cleared by the grounding check, per 100 sessions, by field and model version. A rise means the model is guessing more.",["closeout_value_dropped"]],
 ["Downstream: incomplete evidence","Closed jobs missing a required field, per 100 jobs. Ties to SLA evidence and repeat visits within 30 days.",["closeout_submitted"]],
];
$("#metricRows").innerHTML = METRICS.map(m => `<tr><td>${m[0]}</td><td>${m[1]}</td><td>${m[2].map(e => `<code>${e}</code>`).join("")}</td></tr>`).join("");
const EVENTS = [
 ["closeout_session_started","task, technician, job type, channel, offline flag"],
 ["closeout_note_submitted","note length, speech-to-text confidence, language"],
 ["closeout_field_extracted","one per field: value present, evidence found, latency"],
 ["closeout_value_dropped","field, model value, grounding rule"],
 ["closeout_prompt_shown","field, question number"],
 ["closeout_prompt_answered","field, answer channel, seconds to answer, don't know"],
 ["closeout_field_edited","field, old source, new value class"],
 ["closeout_fallback_to_form","step reached, reason if given"],
 ["closeout_submitted","outcome, fields filled by agent, by tech, override used"],
 ["closeout_backoffice_corrected","field, hours after submit, editor role"],
];
$("#eventList").innerHTML = EVENTS.map(e => `<div class="ev"><code>${e[0]}</code><span>${e[1]}</span></div>`).join("");
$("#eventJson").textContent = JSON.stringify({
  event:"closeout_value_dropped", ts:"2026-11-21T10:42:07Z", session_id:"cs_8f21", task_id:"FR-48213",
  tenant_id:"telco_eu_01", job_type:"fibre_repair", field:"signoff", model_value:true,
  rule:"signoff_requires_sign_word", model_version:"gemini-3.5-flash-lite", prompt_version:"p3", policy_version:"fr-2026-11-a"
}, null, 2);
})();
