"""Summarize a bot run's tuning telemetry (logs/run-telemetry/run-*.jsonl, written by RunTelemetry.cs).

Usage:
    python run_telemetry_report.py <install root | logs folder | run-*.jsonl ...> [--since 2026-10-27T18:00] [--out REPORT.txt]

With an install root (the folder holding runtime/ or logs/) it reads every run-*.jsonl under
logs/run-telemetry and, when present, server.log for AUTONOMOUS_BOT_DEATH lines. The report
is printed and also written next to the telemetry as RUN-REPORT.txt unless --out says otherwise.
"""
import argparse
import collections
import glob
import json
import os
import re
import statistics
import sys
from datetime import datetime


def band(level, width=10):
    level = int(level or 0)
    low = (max(level, 1) - 1) // width * width + 1
    return f"{low:>2}-{low + width - 1:<2}"


def median(values):
    return statistics.median(values) if values else 0


def pct(part, whole):
    return 100.0 * part / whole if whole else 0.0


def table(headers, rows, out):
    rows = [[str(c) for c in r] for r in rows]
    widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]
    out.append("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    out.append("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        out.append("  " + "  ".join(c.ljust(w) for c, w in zip(r, widths)))
    out.append("")


def find_inputs(paths):
    files, server_logs = [], []
    for p in paths:
        if os.path.isfile(p):
            (server_logs if p.lower().endswith(".log") else files).append(p)
            continue
        for root in (p, os.path.join(p, "runtime", "server"), os.path.join(p, "runtime")):
            files += glob.glob(os.path.join(root, "logs", "run-telemetry", "run-*.jsonl"))
            files += glob.glob(os.path.join(root, "run-telemetry", "run-*.jsonl"))
            files += glob.glob(os.path.join(root, "run-*.jsonl"))
            server_logs += glob.glob(os.path.join(root, "logs", "server*.log"))
            server_logs += glob.glob(os.path.join(root, "server*.log"))
    return sorted(set(files)), sorted(set(server_logs))


def load(files, since):
    events = collections.defaultdict(list)
    first = last = None
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                t = rec.get("t", "")
                if since and t < since:
                    continue
                first = t if first is None or t < first else first
                last = t if last is None or t > last else last
                events[rec.get("ev")].append(rec.get("detail") or {})
    return events, first, last


def loot_section(loot, out):
    out.append("== LOOT ==")
    if not loot:
        out.append("  no loot records\n")
        return
    by_band = collections.defaultdict(lambda: {"kills": 0, "items": 0, "coin": 0, "lvl_gap": [], "quality": [],
                                               "utility": [], "rog": 0, "unique": 0, "template": 0, "empty": 0})
    by_mob = collections.defaultdict(lambda: [0, 0, 0])
    item_counts = collections.Counter()
    overlevel = collections.Counter()
    for d in loot:
        b = by_band[band(d.get("mobLevel"))]
        b["kills"] += 1
        b["coin"] += d.get("coin", 0)
        items = d.get("items", [])
        if not items:
            b["empty"] += 1
        m = by_mob[(d.get("mob"), d.get("mobLevel"))]
        m[0] += 1
        m[1] += len(items)
        m[2] += d.get("coin", 0)
        for it in items:
            b["items"] += 1
            b[it.get("source", "template")] += 1
            b["lvl_gap"].append(it.get("level", 0) - d.get("mobLevel", 0))
            b["quality"].append(it.get("quality", 0))
            b["utility"].append(it.get("utility", 0))
            item_counts[it.get("name")] += 1
            if it.get("level", 0) - d.get("mobLevel", 0) >= 5:
                overlevel[(d.get("mob"), d.get("mobLevel"), it.get("name"), it.get("level"))] += 1
    rows = []
    for k in sorted(by_band):
        b = by_band[k]
        rows.append([k, b["kills"], f"{b['items'] / b['kills']:.2f}", f"{pct(b['empty'], b['kills']):.0f}%",
                     f"{b['coin'] / b['kills']:.0f}", f"{median(b['lvl_gap']):+.0f}", f"{median(b['quality']):.0f}",
                     f"{median(b['utility']):.0f}", f"{b['rog']}/{b['unique']}/{b['template']}"])
    out.append("  By monster level (items per kill, coin per kill in copper, item level minus monster level):")
    table(["mob lvl", "kills", "items/kill", "no drop", "coin/kill", "lvl gap", "quality", "utility", "rog/uniq/tmpl"], rows, out)
    out.append("  Most dropped items:")
    table(["count", "item"], [[c, n] for n, c in item_counts.most_common(15)], out)
    stingy = sorted(((k, v) for k, v in by_mob.items() if v[0] >= 20 and v[1] == 0), key=lambda kv: -kv[1][0])[:15]
    if stingy:
        out.append("  Monsters killed 20+ times that never dropped an item:")
        table(["kills", "coin/kill", "monster (level)"], [[v[0], f"{v[2] / v[0]:.0f}", f"{k[0]} ({k[1]})"] for k, v in stingy], out)
    if overlevel:
        out.append("  Items 5+ levels above the monster that dropped them:")
        table(["count", "monster (lvl)", "item (lvl)"],
              [[c, f"{k[0]} ({k[1]})", f"{k[2]} ({k[3]})"] for k, c in overlevel.most_common(15)], out)


def fight_section(fights, out):
    out.append("== FIGHTS ==")
    if not fights:
        out.append("  no fight records\n")
        return
    cls = collections.defaultdict(lambda: {"win": 0, "loss": 0, "reset": 0, "ttk": [], "dps": [], "taken": [], "hp": []})
    mobs = collections.defaultdict(lambda: {"win": 0, "loss": 0, "reset": 0, "ttk": [], "baf": []})
    for d in fights:
        outcome = d.get("outcome")
        m = mobs[(d.get("mob"), d.get("mobLevel"))]
        m[outcome] = m.get(outcome, 0) + 1
        if outcome == "win":
            m["ttk"].append(d.get("durationMs", 0) / 1000)
            m["baf"].append(d.get("baf", 0))
        for w in d.get("who", []):
            if w.get("kind") not in ("bot", "player"):
                continue
            c = cls[(w.get("cls") or "?", band(w.get("level")), "solo" if d.get("participants", 1) == 1 else "group")]
            c[outcome] = c.get(outcome, 0) + 1
            if outcome == "win":
                secs = max(d.get("durationMs", 0) / 1000, 0.5)
                c["ttk"].append(secs)
                c["dps"].append(w.get("dealt", 0) / secs)
                c["taken"].append(w.get("taken", 0))
                c["hp"].append(w.get("hp", 0))
    out.append("  By class, level band and solo/group (time to kill and damage per second on won fights;")
    out.append("  hp is the participant's health % when the monster died):")
    rows = []
    for k in sorted(cls, key=lambda k: (k[0], k[1], k[2])):
        c = cls[k]
        total = c["win"] + c["loss"] + c["reset"]
        if total < 5:
            continue
        rows.append([k[0], k[1], k[2], total, f"{pct(c['loss'], total):.1f}%", f"{pct(c['reset'], total):.1f}%",
                     f"{median(c['ttk']):.1f}s", f"{median(c['dps']):.0f}", f"{median(c['taken']):.0f}", f"{median(c['hp']):.0f}%"])
    table(["class", "lvl", "mode", "fights", "loss", "reset", "ttk", "dps", "taken", "hp"], rows, out)
    deadly = sorted(((k, v) for k, v in mobs.items() if v["win"] + v["loss"] >= 10 and v["loss"]),
                    key=lambda kv: -kv[1]["loss"] / (kv[1]["win"] + kv[1]["loss"]))[:15]
    if deadly:
        out.append("  Deadliest monsters (10+ fights, bot/player losses per fight):")
        table(["loss rate", "fights", "ttk", "baf adds", "monster (lvl)"],
              [[f"{pct(v['loss'], v['win'] + v['loss']):.0f}%", v["win"] + v["loss"], f"{median(v['ttk']):.1f}s",
                f"{statistics.mean(v['baf']) if v['baf'] else 0:.1f}", f"{k[0]} ({k[1]})"] for k, v in deadly], out)
    slow = sorted(((k, v) for k, v in mobs.items() if len(v["ttk"]) >= 10), key=lambda kv: -median(kv[1]["ttk"]))[:10]
    if slow:
        out.append("  Slowest monsters to kill (10+ wins):")
        table(["ttk", "wins", "monster (lvl)"], [[f"{median(v['ttk']):.1f}s", len(v["ttk"]), f"{k[0]} ({k[1]})"] for k, v in slow], out)


def mob_ai_section(fights, path_failures, out):
    out.append("== MONSTER AI ==")
    resets = collections.Counter()
    reset_hp = collections.defaultdict(list)
    for d in fights:
        if d.get("outcome") == "reset":
            key = (d.get("mob"), d.get("mobLevel"), d.get("zone"))
            resets[key] += 1
            reset_hp[key].append(d.get("mobHp", 0))
    if resets:
        out.append("  Most resets (monster gave up and walked home; mob hp is its health % when it left):")
        table(["resets", "mob hp", "monster (lvl)", "zone"],
              [[c, f"{median(reset_hp[k]):.0f}%", f"{k[0]} ({k[1]})", k[2]] for k, c in resets.most_common(15)], out)
        why = [d for d in fights if d.get("outcome") == "reset" and "mobSwings" in d]
        if why:
            # A monster leaves when its hate list empties or nothing has hit either way for 25 s.
            never = sum(1 for d in why if d.get("mobSwings", 0) == 0)
            idle = sum(1 for d in why if d.get("mobLastSwingAgoMs", -1) >= 20000 and d.get("mobLastHitAgoMs", -1) >= 20000)
            far = [w.get("distance", -1) for d in why for w in d.get("who", []) if w.get("distance", -1) >= 0]
            out.append(f"  Why they reset ({len(why)} with reasons): monster never swung {pct(never, len(why)):.0f}%, "
                       f"20+ s without a swing or a hit {pct(idle, len(why)):.0f}%, median chase from spawn "
                       f"{median([d.get('fromSpawn', 0) for d in why]):.0f}, median distance to the bot {median(far):.0f}\n")
    paths = collections.Counter()
    for d in path_failures:
        for c in d.get("counts", []):
            paths[(c.get("mob"), c.get("region"), c.get("status"), c.get("jumped"), c.get("spawnX", ""), c.get("spawnY", ""))] += c.get("count", 0)
    if paths:
        out.append("  Path failures while chasing (jumped = teleported to the nearest reachable node; spawn to 100 units):")
        table(["count", "status", "jumped", "region", "spawn x,y", "monster"],
              [[c, k[2], k[3], k[1], f"{k[4]},{k[5]}" if k[4] != "" else "-", k[0]] for k, c in paths.most_common(20)], out)
    if not resets and not paths:
        out.append("  no monster AI records\n")


def swing_section(fights, swings, out):
    out.append("== SWINGS ==")
    if not swings:
        out.append("  no swing records\n")
        return
    side = collections.defaultdict(lambda: collections.Counter())
    for d in swings:
        for c in d.get("counts", []):
            key = (c.get("side"), c.get("who") if c.get("side") == "bot" else "", f"{c.get('band', 0)}-{c.get('band', 0) + 9}")
            n = c.get("count", 0)
            s = side[key]
            s["swings"] += n
            s["damage"] += c.get("damage", 0)
            s["off"] += n if c.get("offHand") else 0
            s["styled"] += n if c.get("styled") else 0
            for chance in ("miss", "evade", "parry", "block"):
                s[chance + "Chance"] += c.get(chance, 0) * n
            r = c.get("result", "")
            s["hit" if r in ("HitUnstyled", "HitStyle") else r] += n
    def rows(which):
        result = []
        for k in sorted(k for k in side if k[0] == which):
            s = side[k]
            n = s["swings"]
            if n < 50:
                continue
            result.append([k[1] or "monsters", k[2], n, f"{pct(s['hit'], n):.0f}%", f"{pct(s['Missed'], n):.0f}%",
                           f"{pct(s['Evaded'], n):.0f}%", f"{pct(s['Parried'], n):.0f}%", f"{pct(s['Blocked'], n):.0f}%",
                           f"{pct(s['OutOfRange'] + s['NotAllowed_ServerRules'] + s['TargetNotVisible'], n):.0f}%",
                           f"{s['damage'] / s['hit'] if s['hit'] else 0:.0f}", f"{pct(s['styled'], n):.0f}%", f"{pct(s['off'], n):.0f}%"])
        return result
    headers = ["who", "lvl", "swings", "hit", "miss", "evaded", "parried", "blocked", "no swing", "dmg/hit", "styled", "off-hand"]
    out.append("  Monster swings at players and bots, by monster level (no swing = out of range, not allowed or unseen):")
    table(headers, rows("mob"), out)
    out.append("  Bot swings at monsters, by class and bot level:")
    table(headers, rows("bot"), out)
    counted = [d for d in fights if "mobSwings" in d and d.get("outcome") == "win"]
    if counted:
        zero = [d for d in counted if all(w.get("taken", 0) == 0 for w in d.get("who", []))]
        out.append(f"  Won fights with no damage taken: {len(zero)} of {len(counted)}; in those the monster swung a median "
                   f"{median([d.get('mobSwings', 0) for d in zero]):.0f} times and landed {median([d.get('mobHits', 0) for d in zero]):.0f}\n")


def progress_section(snapshots, out):
    out.append("== BOT PROGRESS ==")
    if not snapshots:
        out.append("  no snapshots\n")
        return
    rates = collections.defaultdict(lambda: {"minutes": 0.0, "levels": 0.0, "money": 0, "deaths": 0, "kills": 0, "bots": set(), "gear": []})
    stalled = collections.defaultdict(int)
    stalled_info = {}
    activity = collections.Counter()
    by_bot = collections.defaultdict(list)
    for d in snapshots:
        by_bot[d.get("botId")].append(d)
        activity[(d.get("activity") or "?")[:60]] += 1
    for bot_id, snaps in by_bot.items():
        prev = None
        for d in snaps:
            minutes = d.get("minutes", 0)
            if prev is not None and minutes > 0:
                r = rates[(d.get("cls"), band(prev.get("level")))]
                r["minutes"] += minutes
                r["levels"] += (d["level"] + d.get("levelPercent", 0) / 100) - (prev["level"] + prev.get("levelPercent", 0) / 100)
                r["money"] += d.get("moneyGained", 0)
                r["deaths"] += d.get("deaths", 0)
                r["kills"] += d.get("kills", 0)
                r["bots"].add(bot_id)
                r["gear"].append(d.get("gearValue", 0))
                if d.get("xpGained", 0) <= 0 and d.get("level", 0) < 50:
                    stalled[bot_id] += 1
                    stalled_info[bot_id] = d
                else:
                    stalled[bot_id] = 0
            prev = d
    rows = []
    for k in sorted(rates, key=lambda k: (k[0] or "", k[1])):
        r = rates[k]
        hours = r["minutes"] / 60
        if hours < 0.25:
            continue
        rows.append([k[0], k[1], len(r["bots"]), f"{hours:.1f}", f"{r['levels'] / hours:.2f}", f"{r['money'] / hours:.0f}",
                     f"{r['kills'] / hours:.0f}", f"{r['deaths'] / hours:.2f}", f"{median(r['gear']):.0f}"])
    out.append("  By class and starting level band (bot-hours observed; levels, copper, kills and deaths per bot-hour):")
    table(["class", "lvl", "bots", "hours", "levels/h", "copper/h", "kills/h", "deaths/h", "gear value"], rows, out)
    stuck = sorted(((b, n) for b, n in stalled.items() if n >= 3), key=lambda bn: -bn[1])[:20]
    if stuck:
        out.append("  Bots with no XP for 3+ snapshots in a row at the end of the run:")
        table(["snaps", "bot", "class", "lvl", "zone", "activity"],
              [[n, stalled_info[b].get("bot"), stalled_info[b].get("cls"), stalled_info[b].get("level"),
                stalled_info[b].get("zone"), (stalled_info[b].get("activity") or "")[:60]] for b, n in stuck], out)
    out.append("  Where bot time went (share of snapshots by activity):")
    total = sum(activity.values())
    table(["share", "activity"], [[f"{pct(c, total):.1f}%", a] for a, c in activity.most_common(15)], out)


def economy_section(trades, out):
    out.append("== ECONOMY ==")
    if not trades:
        out.append("  no trade records\n")
        return
    kinds = collections.defaultdict(lambda: {"count": 0, "copper": 0, "items": 0})
    for d in trades:
        k = kinds[(d.get("kind"), band(d.get("level")))]
        k["count"] += 1
        k["copper"] += d.get("copper", 0)
        k["items"] += d.get("count", 1)
    table(["kind", "lvl", "records", "items", "copper", "copper each"],
          [[k[0], k[1], v["count"], v["items"], v["copper"], f"{v['copper'] / v['count']:.0f}"]
           for k, v in sorted(kinds.items())], out)
    bought = collections.Counter(d.get("item") for d in trades if d.get("kind") == "buy")
    if bought:
        out.append("  Most bought vendor upgrades:")
        table(["count", "item"], [[c, n] for n, c in bought.most_common(10)], out)


def pull_section(pulls, out):
    out.append("== PULL TARGETS (sampled) ==")
    if not pulls:
        out.append("  no pull-target records\n")
        return
    con = collections.Counter(d.get("con") for d in pulls)
    total = len(pulls)
    out.append(f"  {total} sampled picks; already in combat {pct(sum(1 for d in pulls if d.get('targetInCombat')), total):.1f}%, "
               f"median distance {median([d.get('distance', 0) for d in pulls]):.0f}, "
               f"median other monsters within 500 {median([d.get('nearbyMonsters', 0) for d in pulls]):.0f}, "
               f"median bot hp {median([d.get('hp', 0) for d in pulls]):.0f}%")
    table(["share", "con"], [[f"{pct(c, total):.1f}%", k] for k, c in con.most_common()], out)
    crowded = collections.Counter((d.get("target"), d.get("targetLevel"), d.get("zone"))
                                  for d in pulls if d.get("nearbyMonsters", 0) >= 3)
    if crowded:
        out.append("  Pulls with 3+ other monsters within 500 units (add risk):")
        table(["count", "target (lvl)", "zone"], [[c, f"{k[0]} ({k[1]})", k[2]] for k, c in crowded.most_common(10)], out)


DEATH = re.compile(r'(?P<t>^\S+ \S+).*AUTONOMOUS_BOT_DEATH .*?level=(?P<level>\d+) class="(?P<cls>[^"]*)".*?killer="(?P<killer>[^"]*)" '
                   r'killerKind=(?P<kind>\S+) killerLevel=(?P<klevel>\d+) con=(?P<con>\S+) attackers=(?P<attackers>\d+).*?'
                   r'arrivedAtCamp=(?P<arrived>\S+) activity="(?P<activity>[^"]*)"')


def death_section(server_logs, out):
    out.append("== BOT DEATHS (server.log) ==")
    deaths = []
    for path in server_logs:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "AUTONOMOUS_BOT_DEATH" in line:
                    m = DEATH.search(line)
                    if m:
                        deaths.append(m.groupdict())
    if not deaths:
        out.append("  no AUTONOMOUS_BOT_DEATH lines found\n")
        return
    out.append(f"  {len(deaths)} deaths; on the way to camp {pct(sum(d['arrived'] == 'False' for d in deaths), len(deaths)):.0f}%, "
               f"3+ attackers {pct(sum(int(d['attackers']) >= 3 for d in deaths), len(deaths)):.0f}%")
    table(["count", "killer kind"], [[c, k] for k, c in collections.Counter(d["kind"] for d in deaths).most_common()], out)
    table(["count", "con"], [[c, k] for k, c in collections.Counter(d["con"] for d in deaths).most_common()], out)
    out.append("  Top killers:")
    table(["count", "killer (lvl)"], [[c, f"{k[0]} ({k[1]})"] for k, c in
                                      collections.Counter((d["killer"], d["klevel"]) for d in deaths).most_common(15)], out)
    out.append("  Deaths by class:")
    table(["count", "class"], [[c, k] for k, c in collections.Counter(d["cls"] for d in deaths).most_common()], out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--since", help="ISO time (UTC) to start from, e.g. 2026-10-27T18:00")
    ap.add_argument("--out")
    args = ap.parse_args()
    files, server_logs = find_inputs(args.paths)
    if not files:
        sys.exit("no run-*.jsonl files found")
    events, first, last = load(files, args.since)
    if first:
        # server.log rolls over daily: keep the files written to since the first telemetry record.
        start = datetime.fromisoformat(first.replace("Z", "+00:00")).timestamp()
        server_logs = [p for p in server_logs if os.path.getmtime(p) >= start]
    out = [f"RUN TELEMETRY REPORT  generated {datetime.now():%Y-%m-%d %H:%M}",
           f"  records {first} .. {last} (UTC) from {len(files)} file(s)",
           "  " + ", ".join(f"{k}={len(v)}" for k, v in sorted(events.items())), ""]
    loot_section(events.get("loot", []), out)
    fight_section(events.get("fight", []), out)
    mob_ai_section(events.get("fight", []), events.get("mob-path-failures", []), out)
    swing_section(events.get("fight", []), events.get("swings", []), out)
    progress_section(events.get("snapshot", []), out)
    economy_section(events.get("trade", []), out)
    pull_section(events.get("pull-target", []), out)
    death_section(server_logs, out)
    text = "\n".join(out)
    print(text)
    target = args.out or os.path.join(os.path.dirname(files[-1]), "RUN-REPORT.txt")
    with open(target, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\nwritten to {target}")


if __name__ == "__main__":
    main()
