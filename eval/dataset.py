# Synthetic FTTP (fibre broadband) technician close-out notes, hand-written and hand-labelled.
# NOT real customer data. Written to mimic voice-to-text job notes from telecom field techs.
# Gold fields: outcome, fault, parts {SKU: qty}, dbm (final optical reading), signoff (True/False/None), revisit.
import json, pathlib

OUTCOMES = ["RESOLVED", "REVISIT", "NO_ACCESS", "ESCALATED"]
FAULTS = ["FIBRE_BREAK", "DROP_DAMAGE", "INTERNAL_CABLING", "DIRTY_CONNECTOR", "CABINET_PORT",
          "ONT_FAULT", "ROUTER_FAULT", "PSU_FAULT", "WIFI_CONFIG", "OUTAGE", "NO_FAULT_FOUND"]
PARTS = ["ONT", "ROUTER", "PSU", "PATCH_CORD", "DROP_CABLE_M", "CONNECTOR", "SPLICE_PROTECTOR", "FACEPLATE"]
REVISIT = ["PARTS", "CUSTOMER_UNAVAILABLE", "CIVILS", "PERMISSION", "SECOND_TECH", "OTHER"]

R, V, N, E = "RESOLVED", "REVISIT", "NO_ACCESS", "ESCALATED"
T, F_ = True, False

# (note, outcome, fault, parts, dbm, signoff, revisit)
ROWS = [
 ("ONT dead no lights at all. swapped ONT, new unit synced first time. rx -19.8 dBm. customer signed on the tablet.", R, "ONT_FAULT", {"ONT": 1}, -19.8, T, None),
 ("no light at the ONT. traced it back, drop cable chewed thru by squirrels on the pole run. replaced 40m of drop and fitted a new connector. light level now minus twenty point five. cust signed", R, "DROP_DAMAGE", {"DROP_CABLE_M": 40, "CONNECTOR": 1}, -20.5, T, None),
 ("Customer not in. Called twice no answer, left card.", N, None, {}, None, None, None),
 ("wifi dropping upstairs. nothing wrong with the line, moved router to the landing and changed channel to 36. cust happy.", R, "WIFI_CONFIG", {}, None, None, None),
 ("cleaned the connector at the wall socket, was filthy. reading went from -27 to -18.6. signed.", R, "DIRTY_CONNECTOR", {}, -18.6, T, None),
 ("fibre snapped in the loft where the builder was working. just needs a re-route but i dont have enough drop on the van, back tomorrow", V, "FIBRE_BREAK", {}, None, None, "PARTS"),
 ("port at the cabinet is dead, moved customer to port 14 at the cab, ont back up -21.2", R, "CABINET_PORT", {}, -21.2, None, None),
 ("router wouldnt power on, it was the power supply not the router. swapped psu only, all green. customer signed off", R, "PSU_FAULT", {"PSU": 1}, None, T, None),
 ("Tested everything, line is fine -19 at ONT, speeds good. no fault found. cust signed.", R, "NO_FAULT_FOUND", {}, -19.0, T, None),
 ("no service, duct got crushed by the driveway works and the drop inside is damaged. needs civils to dig before we can pull new cable", V, "DROP_DAMAGE", {}, None, None, "CIVILS"),
 ("whole street is down, not a customer side issue, cabinet looks like it lost power. escalated to network ops", E, "OUTAGE", {}, None, None, None),
 ("replaced 2 patch leads and the faceplate, customer had yanked the cable out of the wall. light level ok.", R, "INTERNAL_CABLING", {"PATCH_CORD": 2, "FACEPLATE": 1}, None, None, None),
 ("customer had to leave for school pickup halfway thru. ONT swapped but didnt get to test. coming back thurs", V, "ONT_FAULT", {"ONT": 1}, None, None, "CUSTOMER_UNAVAILABLE"),
 ("landlord wont allow drilling the external wall so cant run new drop until we get permission. old drop is cracked at the entry point", V, "DROP_DAMAGE", {}, None, None, "PERMISSION"),
 ("drop is sagging and damaged at the pole, its a 9m pole and my ladder wont reach safely. needs a two man crew, rebooking", V, "DROP_DAMAGE", {}, None, None, "SECOND_TECH"),
 ("no fault found, everything working when i got here. customer says it drops in the evenings. advised to call in if it happens again", R, "NO_FAULT_FOUND", {}, None, None, None),
 ("router was in a boot loop, factory reset didnt fix it so swapped for a new hub. rx -22.1. got sig.", R, "ROUTER_FAULT", {"ROUTER": 1}, -22.1, T, None),
 ("ONT had water damage from the leak in the cupboard. replaced the ONT and also gave them a new router as the old one was ancient", R, "ONT_FAULT", {"ONT": 1, "ROUTER": 1}, None, None, None),
 ("Fibre break about 3m from the house, spliced it, used 2 splice protectors. light -20.9 after. Customer signed.", R, "FIBRE_BREAK", {"SPLICE_PROTECTOR": 2}, -20.9, T, None),
 ("connector end face was scratched, cleaning didnt help so fitted a new field connector. -19.4 now. customer refused to sign, said theyve been waiting 3 weeks", R, "DIRTY_CONNECTOR", {"CONNECTOR": 1}, -19.4, F_, None),
 ("nobody home, dog loose in the garden so couldnt get to the external box. card left", N, None, {}, None, None, None),
 ("access refused by the site manager at the office block, they had no booking on their side", N, None, {}, None, None, None),
 ("speed complaint. laptop was stuck on 2.4GHz, turned on band steering, 600+ on 5GHz now. light level -17.5 for the record. customer signed", R, "WIFI_CONFIG", {}, -17.5, T, None),
 ("minus three outside and the ONT power supply had packed in. new psu fitted, ont lit up. reading minus 18.2. signed", R, "PSU_FAULT", {"PSU": 1}, -18.2, T, None),
 ("ont flashing red. light level -31, way too low. cleaned the connector, -30, no change so fault is upstream. raised to network to check the cabinet port", E, "CABINET_PORT", {}, -30.0, None, None),
 ("Replaced ONT. Signed.", R, "ONT_FAULT", {"ONT": 1}, None, T, None),
 ("fixed", R, None, {}, None, None, None),
 ("fibre patch lead from the wall to the ONT was kinked behind the sofa. new patch lead fitted. -20. cust signed", R, "INTERNAL_CABLING", {"PATCH_CORD": 1}, -20.0, T, None),
 ("found the break in the drop at the pole, started splicing but ran out of splice protectors. back tmrw first thing", V, "FIBRE_BREAK", {}, None, None, "PARTS"),
 ("router swapped", R, "ROUTER_FAULT", {"ROUTER": 1}, None, None, None),
 ("so basically the customer said the internet had been off since the storm, I checked the ONT and there was no light, went outside and the drop had come off the hook on the wall and snapped, so I ran a new drop, about 25 metres, put a new connector on, and we're getting minus nineteen at the ONT now, customer signed for it", R, "DROP_DAMAGE", {"DROP_CABLE_M": 25, "CONNECTOR": 1}, -19.0, T, None),
 ("had a spare router in the van but didnt need it, issue was the customers own mesh system fighting with our wifi. turned off our wifi, mesh in bridge mode. sig captured", R, "WIFI_CONFIG", {}, None, T, None),
 ("Customer cancelled at the door, said it started working this morning. didnt go in.", N, None, {}, None, None, None),
 ("ONT replaced, -21.7 at ONT, customer wasnt around to sign, wife let me in and she had to go", R, "ONT_FAULT", {"ONT": 1}, -21.7, F_, None),
 ("tested line from the cabinet, reading fine at the cab but nothing at the house. break somewhere in the underground section, needs civils", V, "FIBRE_BREAK", {}, None, None, "CIVILS"),
 ("dirty connector on the ONT side, cleaned both ends. was -26.4 now -19.1. no new parts. customer signed", R, "DIRTY_CONNECTOR", {}, -19.1, T, None),
 ("ONT power supply was dead, swapped it, also replaced 1 patch cord while I was there as it looked worn. Not sure what the reading was, forgot to note it. customer signed", R, "PSU_FAULT", {"PSU": 1, "PATCH_CORD": 1}, None, T, None),
 ("cab port fault, re-patched to spare port 7. light good at -18.9. no signature, customer at work, neighbour had the key", R, "CABINET_PORT", {}, -18.9, F_, None),
 ("gate locked, no answer on the phone, waited 15 mins", N, None, {}, None, None, None),
 ("its an area outage, there are 3 other jobs on this street with the same thing. passed it to NOC", E, "OUTAGE", {}, None, None, None),
 ("replaced 30m drop cable and 2 connectors, old drop was cut by a hedge trimmer. light level minus twenty one point three. customer signed", R, "DROP_DAMAGE", {"DROP_CABLE_M": 30, "CONNECTOR": 2}, -21.3, T, None),
 ("customer said router keeps rebooting. firmware was old, updated firmware and it's been stable for 30 mins. no parts. customer signed.", R, "ROUTER_FAULT", {}, None, T, None),
 ("wall faceplate smashed when they moved furniture. new faceplate and a patch cord fitted. reading -20.2", R, "INTERNAL_CABLING", {"FACEPLATE": 1, "PATCH_CORD": 1}, -20.2, None, None),
 ("needs a cherry picker, drop is on a tall pole over the main road and traffic management is needed. raised for a 2 person crew", V, "DROP_DAMAGE", {}, None, None, "SECOND_TECH"),
 ("ONT faulty, I didnt have one on the van, ordered one, will come back once it arrives", V, "ONT_FAULT", {}, None, None, "PARTS"),
 ("no fault found. light -18.5, sync fine, speedtest 940/110. customer still unhappy, did not sign", R, "NO_FAULT_FOUND", {}, -18.5, F_, None),
 ("customer was rude and asked me to leave before i could start. nothing done", N, None, {}, None, None, None),
 ("swapped router, -20.6, signed", R, "ROUTER_FAULT", {"ROUTER": 1}, -20.6, T, None),
 ("power surge killed the ONT, replaced the ONT and its PSU to be safe. light -19.9. customer signed on the app", R, "ONT_FAULT", {"ONT": 1, "PSU": 1}, -19.9, T, None),
 ("cleaned connector, all good now", R, "DIRTY_CONNECTOR", {}, None, None, None),
 ("building has no riser access tonight, management office closed. need the building manager to sign the wayleave before install", V, None, {}, None, None, "PERMISSION"),
 ("got there, power cut on the whole road so cant test anything. rebook", V, None, {}, None, None, "OTHER"),
 ("customer moved the ONT themselves and bent the internal fibre too tight. re-routed the internal cable, added one splice protector where I re-spliced. -22.4. signature taken", R, "INTERNAL_CABLING", {"SPLICE_PROTECTOR": 1}, -22.4, T, None),
 ("cust reported slow speeds on the TV. it was on wifi in the far room, set up a dedicated 5GHz network for it. speeds fine. -17.9. customer signed", R, "WIFI_CONFIG", {}, -17.9, T, None),
 ("checked ont, rx minus twenty three, bit low but within spec. cleaned the patch cord anyway, back to minus twenty point one. signed", R, "DIRTY_CONNECTOR", {}, -20.1, T, None),
 ("installed new ONT, customer signed, light level was good", R, "ONT_FAULT", {"ONT": 1}, None, T, None),
 ("fault is in the cabinet splitter not the port, beyond what I can do. escalated to network engineering with photos", E, "CABINET_PORT", {}, None, None, None),
 ("drop cable fine, ONT fine, router fine. customer's wifi extender was the problem, factory reset it and paired again. customer happy and signed", R, "WIFI_CONFIG", {}, None, T, None),
 ("break in the drop at the wall bracket, replaced 15 metres drop and 1 connector. minus eighteen point seven at ONT. customer was out, no sig", R, "DROP_DAMAGE", {"DROP_CABLE_M": 15, "CONNECTOR": 1}, -18.7, F_, None),
 ("ONT dead. Replaced router and ONT. Customer signed. -19.6", R, "ONT_FAULT", {"ROUTER": 1, "ONT": 1}, -19.6, T, None),
 ("sorted the wifi", R, "WIFI_CONFIG", {}, None, None, None),
 ("cabinet port swap, light -20.4 at ont, customer signed", R, "CABINET_PORT", {}, -20.4, T, None),
 ("no-one in, left a card, rang the number on the job, voicemail", N, None, {}, None, None, None),
 ("started the job but customer needed to leave for a hospital appointment, will need to rebook. nothing replaced yet, suspect the ONT", V, "ONT_FAULT", {}, None, None, "CUSTOMER_UNAVAILABLE"),
 ("spliced the fibre at the joint box, used 4 splice protectors as there were two breaks. readings ok. cust signed", R, "FIBRE_BREAK", {"SPLICE_PROTECTOR": 4}, None, T, None),
 ("router power brick was faulty, new PSU. tested -21.0 at the ONT for completeness. customer signed", R, "PSU_FAULT", {"PSU": 1}, -21.0, T, None),
 ("road dug up by gas company and our duct is exposed and cut. fibre break confirmed with the OTDR. passed to civils and network, multiple customers affected", E, "FIBRE_BREAK", {}, None, None, None),
 ("re-terminated the fibre at the faceplate with a new connector, old one was pulled out. -19.3, customer signed", R, "INTERNAL_CABLING", {"CONNECTOR": 1}, -19.3, T, None),
 ("weather too bad to climb, high winds, rebook for tomorrow. drop looks damaged at the pole", V, "DROP_DAMAGE", {}, None, None, "OTHER"),
 ("ONT faulty, swapped ONT, swapped router, 2 patch cords, -20.8, got signature", R, "ONT_FAULT", {"ONT": 1, "ROUTER": 1, "PATCH_CORD": 2}, -20.8, T, None),
 ("tested, NFF, signed", R, "NO_FAULT_FOUND", {}, None, T, None),
 ("cust says no internet. ONT showing LOS. traced to the external box, connector dirty, cleaned it. LOS cleared. reading minus nineteen point four. no sig as customer was on a work call", R, "DIRTY_CONNECTOR", {}, -19.4, F_, None),
 ("No access - apartment intercom broken, couldnt reach customer", N, None, {}, None, None, None),
 ("fixed the drop, about 20m replaced, customer signed", R, "DROP_DAMAGE", {"DROP_CABLE_M": 20}, None, T, None),
 ("ONT faulty. ONT swapped, router swapped too, light level fine", R, "ONT_FAULT", {"ONT": 1, "ROUTER": 1}, None, None, None),
 ("issue was with the cabinet, cant fix from the house. escalated", E, "CABINET_PORT", {}, None, None, None),
 ("escalated, not sure what is wrong", E, None, {}, None, None, None),
 ("all done", R, None, {}, None, None, None),
 ("replaced the faceplate, -18.8, signed", R, "INTERNAL_CABLING", {"FACEPLATE": 1}, -18.8, T, None),
 ("customer needs to be there for the internal work and wasnt, partner didnt know about the appointment. rebooked for saturday", V, None, {}, None, None, "CUSTOMER_UNAVAILABLE"),
]

FIBRE_READING_REQUIRED = {"FIBRE_BREAK", "DROP_DAMAGE", "INTERNAL_CABLING", "DIRTY_CONNECTOR",
                          "CABINET_PORT", "ONT_FAULT", "NO_FAULT_FOUND"}


def missing_fields(rec):
    """Close-out policy: which required fields are absent for this outcome. Same function for gold and predictions."""
    o, miss = rec.get("outcome"), []
    if o == "RESOLVED":
        if not rec.get("fault"): miss.append("fault")
        elif rec["fault"] in FIBRE_READING_REQUIRED and rec.get("dbm") is None: miss.append("dbm")
        if rec.get("signoff") is None: miss.append("signoff")
    elif o == "REVISIT":
        if not rec.get("revisit"): miss.append("revisit")
        if not rec.get("fault"): miss.append("fault")
    elif o == "ESCALATED":
        if not rec.get("fault"): miss.append("fault")
    return miss


def load():
    out = []
    for i, (note, o, f, p, d, s, rv) in enumerate(ROWS, 1):
        rec = dict(id=f"T{i:03d}", note=note, outcome=o, fault=f, parts=p, dbm=d, signoff=s, revisit=rv)
        assert o in OUTCOMES and (f is None or f in FAULTS) and all(k in PARTS for k in p) and (rv is None or rv in REVISIT)
        rec["missing"] = missing_fields(rec)
        out.append(rec)
    return out


if __name__ == "__main__":
    data = load()
    pathlib.Path(__file__).with_name("tickets.json").write_text(json.dumps(data, indent=1))
    from collections import Counter
    print(len(data), Counter(r["outcome"] for r in data), sum(bool(r["missing"]) for r in data), "with missing")
