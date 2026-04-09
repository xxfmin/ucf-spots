"""Compare two buildings_enriched_<TERM>.json snapshots and report diffs.

Usage:
    python compare_enriched.py --old archive/old_buildings_enriched_SP26.json \
        --new archive/buildings_enriched_SP26.json \
        [--out archive/diff_report_SP26.json] [--top 20]

Outputs a concise stdout summary and a full JSON report so future analysis can
grep targeted sections instead of re-loading both source snapshots.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

GRAD_THRESHOLD = 5000
_NUM_RE = re.compile(r"(\d+)")


def load_sections(path: Path) -> list[dict[str, Any]]:
    """Flatten a snapshot into a list of section dicts tagged with bldg/room."""
    data = json.loads(path.read_text())
    buildings = data.get("buildings", {})
    out: list[dict[str, Any]] = []
    for bldg, binfo in buildings.items():
        rooms = (binfo or {}).get("rooms", {}) or {}
        for room, sections in rooms.items():
            for sec in sections or []:
                out.append({
                    "building": bldg,
                    "room": room,
                    "course": sec.get("course", ""),
                    "title": sec.get("title", ""),
                    "days": tuple(sec.get("days") or ()),
                    "start": (sec.get("time") or {}).get("start", ""),
                    "end": (sec.get("time") or {}).get("end", ""),
                    "start_date": sec.get("start_date", ""),
                    "end_date": sec.get("end_date", ""),
                })
    return out


def course_num(course: str) -> int | None:
    parts = course.split()
    if len(parts) < 2:
        return None
    m = _NUM_RE.search(parts[1])
    return int(m.group(1)) if m else None


def is_grad(course: str) -> bool:
    n = course_num(course)
    return n is not None and n >= GRAD_THRESHOLD


def subject_of(course: str) -> str:
    return course.split()[0] if course else ""


def basic_totals(secs: list[dict[str, Any]]) -> dict[str, int]:
    buildings = {s["building"] for s in secs}
    rooms = {(s["building"], s["room"]) for s in secs}
    courses = {s["course"] for s in secs}
    subjects = {subject_of(s["course"]) for s in secs}
    titles = {s["title"] for s in secs}
    grad = sum(1 for s in secs if is_grad(s["course"]))
    one_off = sum(1 for s in secs if s["start_date"] and s["start_date"] == s["end_date"])
    patterns = {(s["course"], s["building"], s["room"], s["days"], s["start"], s["end"]) for s in secs}
    return {
        "buildings": len(buildings),
        "rooms": len(rooms),
        "sections": len(secs),
        "courses": len(courses),
        "subjects": len(subjects),
        "titles": len(titles),
        "grad_sections": grad,
        "ug_sections": len(secs) - grad,
        "one_off_sections": one_off,
        "meeting_patterns": len(patterns),
    }


def delta_row(old: int, new: int) -> dict[str, Any]:
    d = new - old
    pct = (d / old * 100) if old else None
    return {"old": old, "new": new, "delta": d, "pct": round(pct, 2) if pct is not None else None}


def totals_diff(old: list[dict], new: list[dict]) -> dict[str, Any]:
    o, n = basic_totals(old), basic_totals(new)
    return {k: delta_row(o[k], n[k]) for k in o}


def counts_by(secs: list[dict], key) -> Counter:
    c: Counter = Counter()
    for s in secs:
        c[key(s)] += 1
    return c


def grad_counts_by(secs: list[dict], key) -> Counter:
    c: Counter = Counter()
    for s in secs:
        if is_grad(s["course"]):
            c[key(s)] += 1
    return c


def diff_counters(old: Counter, new: Counter) -> list[dict[str, Any]]:
    keys = set(old) | set(new)
    rows = []
    for k in keys:
        o, n = old.get(k, 0), new.get(k, 0)
        rows.append({"key": k, "old": o, "new": n, "delta": n - o})
    rows.sort(key=lambda r: (-abs(r["delta"]), r["key"] if isinstance(r["key"], str) else ""))
    return rows


def building_diff(old: list[dict], new: list[dict]) -> dict[str, Any]:
    old_sec = counts_by(old, lambda s: s["building"])
    new_sec = counts_by(new, lambda s: s["building"])
    old_rooms = defaultdict(set)
    new_rooms = defaultdict(set)
    for s in old:
        old_rooms[s["building"]].add(s["room"])
    for s in new:
        new_rooms[s["building"]].add(s["room"])
    keys = set(old_sec) | set(new_sec)
    rows = []
    for b in keys:
        rows.append({
            "building": b,
            "old_sections": old_sec.get(b, 0),
            "new_sections": new_sec.get(b, 0),
            "section_delta": new_sec.get(b, 0) - old_sec.get(b, 0),
            "old_rooms": len(old_rooms.get(b, set())),
            "new_rooms": len(new_rooms.get(b, set())),
            "room_delta": len(new_rooms.get(b, set())) - len(old_rooms.get(b, set())),
        })
    rows.sort(key=lambda r: -abs(r["section_delta"]))
    return {
        "added": sorted(set(new_sec) - set(old_sec)),
        "removed": sorted(set(old_sec) - set(new_sec)),
        "rows": rows,
    }


def room_diff(old: list[dict], new: list[dict]) -> dict[str, Any]:
    key = lambda s: f"{s['building']} {s['room']}"
    o, n = counts_by(old, key), counts_by(new, key)
    added = sorted(set(n) - set(o))
    removed = sorted(set(o) - set(n))
    changes = diff_counters(o, n)
    return {"added": added, "removed": removed, "changes": changes}


def subject_diff(old: list[dict], new: list[dict]) -> list[dict[str, Any]]:
    key = lambda s: subject_of(s["course"])
    o, n = counts_by(old, key), counts_by(new, key)
    og, ng = grad_counts_by(old, key), grad_counts_by(new, key)
    keys = set(o) | set(n)
    rows = []
    for k in keys:
        rows.append({
            "subject": k,
            "old": o.get(k, 0),
            "new": n.get(k, 0),
            "delta": n.get(k, 0) - o.get(k, 0),
            "old_grad": og.get(k, 0),
            "new_grad": ng.get(k, 0),
            "grad_delta": ng.get(k, 0) - og.get(k, 0),
        })
    rows.sort(key=lambda r: -abs(r["delta"]))
    return rows


def course_diff(old: list[dict], new: list[dict]) -> dict[str, Any]:
    key = lambda s: s["course"]
    o, n = counts_by(old, key), counts_by(new, key)
    added = sorted(set(n) - set(o))
    removed = sorted(set(o) - set(n))
    changes = diff_counters(o, n)
    grad_added = [c for c in added if is_grad(c)]
    return {
        "added_count": len(added),
        "removed_count": len(removed),
        "added": added,
        "removed": removed,
        "grad_added": grad_added,
        "changes": changes,
    }


def career_diff(old: list[dict], new: list[dict]) -> dict[str, Any]:
    def split(secs):
        g = sum(1 for s in secs if is_grad(s["course"]))
        return g, len(secs) - g
    og, ou = split(old)
    ng, nu = split(new)
    grad_by_bldg_old = grad_counts_by(old, lambda s: s["building"])
    grad_by_bldg_new = grad_counts_by(new, lambda s: s["building"])
    return {
        "grad": delta_row(og, ng),
        "ug": delta_row(ou, nu),
        "grad_by_building": diff_counters(grad_by_bldg_old, grad_by_bldg_new),
    }


def build_report(old_path: Path, new_path: Path) -> dict[str, Any]:
    old = load_sections(old_path)
    new = load_sections(new_path)
    return {
        "sources": {"old": str(old_path), "new": str(new_path)},
        "totals": totals_diff(old, new),
        "buildings": building_diff(old, new),
        "rooms": room_diff(old, new),
        "subjects": subject_diff(old, new),
        "courses": course_diff(old, new),
        "careers": career_diff(old, new),
    }


def _fmt_delta(row: dict[str, Any]) -> str:
    pct = f" ({row['pct']:+.1f}%)" if row.get("pct") is not None else ""
    return f"{row['old']:>8} -> {row['new']:>8}  delta {row['delta']:+d}{pct}"


def print_summary(report: dict[str, Any], top: int) -> None:
    print("=" * 70)
    print("TOTALS")
    print("=" * 70)
    for k, v in report["totals"].items():
        print(f"  {k:20s} {_fmt_delta(v)}")

    print("\n" + "=" * 70)
    print("CAREERS (UG vs GR)")
    print("=" * 70)
    print(f"  grad   {_fmt_delta(report['careers']['grad'])}")
    print(f"  ug     {_fmt_delta(report['careers']['ug'])}")
    print(f"  top grad-delta buildings:")
    for r in report["careers"]["grad_by_building"][:top]:
        print(f"    {r['key']:10s} {r['old']:>5} -> {r['new']:>5}  {r['delta']:+d}")

    b = report["buildings"]
    print("\n" + "=" * 70)
    print(f"BUILDINGS  added={b['added']}  removed={b['removed']}")
    print("=" * 70)
    print(f"  {'building':12s} {'old':>6} {'new':>6} {'dsec':>7} {'oldR':>5} {'newR':>5} {'dR':>4}")
    for r in b["rows"][:top]:
        print(f"  {r['building']:12s} {r['old_sections']:>6} {r['new_sections']:>6} "
              f"{r['section_delta']:>+7} {r['old_rooms']:>5} {r['new_rooms']:>5} {r['room_delta']:>+4}")

    rm = report["rooms"]
    print("\n" + "=" * 70)
    print(f"ROOMS  added={len(rm['added'])}  removed={len(rm['removed'])}")
    print("=" * 70)
    print(f"  top delta rooms:")
    for r in rm["changes"][:top]:
        print(f"    {r['key']:20s} {r['old']:>5} -> {r['new']:>5}  {r['delta']:+d}")

    print("\n" + "=" * 70)
    print("SUBJECTS (top by |delta|)")
    print("=" * 70)
    print(f"  {'subj':8s} {'old':>6} {'new':>6} {'delta':>7} {'dgrad':>7}")
    for r in report["subjects"][:top]:
        print(f"  {r['subject']:8s} {r['old']:>6} {r['new']:>6} {r['delta']:>+7} {r['grad_delta']:>+7}")

    c = report["courses"]
    print("\n" + "=" * 70)
    print(f"COURSES  added={c['added_count']}  removed={c['removed_count']}  grad_added={len(c['grad_added'])}")
    print("=" * 70)
    print(f"  top delta courses:")
    for r in c["changes"][:top]:
        print(f"    {r['key']:14s} {r['old']:>5} -> {r['new']:>5}  {r['delta']:+d}")
    if c["grad_added"]:
        sample = ", ".join(c["grad_added"][:20])
        more = "" if len(c["grad_added"]) <= 20 else f" (+{len(c['grad_added']) - 20} more)"
        print(f"  grad courses added: {sample}{more}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old", required=True, type=Path)
    ap.add_argument("--new", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    report = build_report(args.old, args.new)
    print_summary(report, args.top)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, default=list))
        print(f"\nFull report written to {args.out}")


if __name__ == "__main__":
    main()
