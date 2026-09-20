#!/usr/bin/env python3
"""
Morning Briefing — 07:00 SAST daily email of work done.
Generates markdown + HTML from traceable sources only, no invented stats.

Sources (traceable):
- content-engine/data/happy_hunter_schedule.json : published/reviewed per date
- content-engine git log --since=yesterday
- executive-assistant git log (if repo present as sibling)
- Future MCP: Firestore leads, WhatsApp sessions -> currently marked [NEEDS MCP]

Output:
- Writes briefing to output/morning-brief-YYYY-MM-DD.md (and .html)
- Prints to stdout for email action to capture
- Returns summary dict for email subject

Usage:
  python scripts/morning_briefing.py [--date YYYY-MM-DD] [--write] -- email capture
"""
import os
import json
import subprocess
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAST = timezone(timedelta(hours=2))

def run_git_log(repo_root: Path, since: str, until: str = None):
    try:
        cmd = ["git", "log", "--oneline", "--pretty=format:%h %ad %s", "--date=short", f"--since={since}"]
        if until:
            cmd.append(f"--until={until}")
        r = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            return lines
    except Exception as e:
        return [f"(git log failed: {e})"]
    return []

def load_schedule():
    base = Path(__file__).resolve().parents[1]
    path = base / "data" / "happy_hunter_schedule.json"
    if not path.exists():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data, path

def briefing_for(date_str: str):
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    yesterday = (target - timedelta(days=1)).isoformat()
    tomorrow = (target + timedelta(days=1)).isoformat()

    data, _ = load_schedule()
    schedule = data.get("schedule", []) if data else []

    # Buckets
    published_yesterday = [p for p in schedule if p.get("date")==yesterday and p.get("published")]
    published_today = [p for p in schedule if p.get("date")==date_str and p.get("published")]
    reviewed_today = [p for p in schedule if p.get("date")==date_str and p.get("reviewed")]
    due_today_unpublished = [p for p in schedule if p.get("date")==date_str and not p.get("published")]
    due_tomorrow = [p for p in schedule if p.get("date")==tomorrow and not p.get("published")]
    # Overdue: date < today, not published, reviewed (should have been published but missed) or not reviewed
    overdue = [p for p in schedule if p.get("date") < date_str and not p.get("published") and p.get("date") >= "2026-09-01"]

    # Git logs
    repo_ce = Path(__file__).resolve().parents[1]
    repo_ea = repo_ce.parent / "executive-assistant"
    ce_log = run_git_log(repo_ce, since=yesterday)
    ea_log = run_git_log(repo_ea, since=yesterday) if repo_ea.exists() else ["(executive-assistant repo not found as sibling — run locally only)"]

    # Counts
    total_published = sum(1 for p in schedule if p.get("published"))
    total_reviewed = sum(1 for p in schedule if p.get("reviewed"))

    # Build markdown
    md = []
    md.append(f"# Morning Briefing — {date_str} (07:00 SAST)")
    md.append(f"_For Thabo Motsumi, Happy Hunter Digital — auto-generated, every number traceable_")
    md.append("")
    md.append(f"**What ran overnight:** EA auto-review at 05:00 UTC + publisher crons at 06:00/11:00/16:00 UTC.")
    md.append("")
    md.append(f"## 1) Work done yesterday ({yesterday})")
    if published_yesterday:
        md.append(f"**Published {len(published_yesterday)} posts** (verified from `data/happy_hunter_schedule.json`):")
        md.append("| Date | Slot | Platform | Headline | Published At (SAST) |")
        md.append("|------|------|----------|----------|---------------------|")
        for p in sorted(published_yesterday, key=lambda x: x.get("slot","")):
            md.append(f"| {p.get('date')} | {p.get('slot')} | {p.get('platform')} | {p.get('headline','')[:50]} | {str(p.get('published_at','-'))[:19]} |")
    else:
        md.append(f"**No posts published yesterday** — either none scheduled or all were `reviewed: false` and correctly skipped (e.g., 2026-09-20 gap before fix).")
    if ce_log:
        md.append("")
        md.append(f"**Content-engine commits since {yesterday}:**")
        for l in ce_log[:8]:
            md.append(f"- {l}")
        if len(ce_log) > 8:
            md.append(f"- ... and {len(ce_log)-8} more")
    else:
        md.append("- No commits since yesterday")
    if ea_log and ea_log[0].startswith("("):
        md.append(f"- {ea_log[0]}")
    elif ea_log:
        md.append("")
        md.append(f"**EA repo commits since {yesterday}:**")
        for l in ea_log[:5]:
            md.append(f"- {l}")

    md.append("")
    md.append(f"## 2) Today ({date_str}) — due")
    if due_today_unpublished:
        md.append(f"**{len(due_today_unpublished)} posts scheduled, not yet published** (EA will auto-review at next 05:00 UTC, then publisher):")
        md.append("| Slot | Platform | Headline | Reviewed |")
        md.append("|------|----------|----------|----------|")
        for p in sorted(due_today_unpublished, key=lambda x: x.get("slot","")):
            md.append(f"| {p.get('slot')} | {p.get('platform')} | {p.get('headline','')[:50]} | {p.get('reviewed')} |")
    else:
        if published_today:
            md.append(f"**All {len(published_today)} posts for today already published** (caught up).")
            for p in published_today:
                md.append(f"- {p.get('slot')} {p.get('platform')}: {p.get('headline','')[:60]} — {p.get('published_at','-')[:19]}")
        else:
            md.append(f"**No posts scheduled for today** — gap in `happy_hunter_schedule.json` or outside campaign window.")

    md.append("")
    md.append(f"## 3) Tomorrow ({tomorrow}) — preview")
    if due_tomorrow:
        for p in sorted(due_tomorrow, key=lambda x: x.get("slot","")):
            md.append(f"- {p.get('slot')} {p.get('platform')}: {p.get('headline','')[:60]}")
    else:
        md.append("- No posts scheduled")

    md.append("")
    md.append(f"## 4) Flags & overdue")
    if overdue:
        # Show only last 5 overdue not published
        recent_overdue = sorted([p for p in overdue if not p.get("published")], key=lambda x: x.get("date"), reverse=True)[:5]
        md.append(f"**{len([p for p in overdue if not p.get('published')])} overdue un-published posts since 2026-09-01** (oldest first, showing 5 most recent):")
        for p in recent_overdue:
            md.append(f"- {p.get('date')} {p.get('slot')} {p.get('platform')}: {p.get('headline','')[:50]} — reviewed={p.get('reviewed')} published={p.get('published')}")
        md.append("- Action: EA auto-review will catch unreviewed ones at 05:00 UTC; already-reviewed but unpublished indicates publisher failure — check GitHub Actions logs.")
    else:
        md.append("- No overdue")

    md.append("")
    md.append("**Leads / WhatsApp / Chatbot:** `[NEEDS MCP]` — Firestore `leads`, WhatsApp, hunterChat not wired (`executive-assistant/mcp-config.json` empty). Once Gmail/WhatsApp/CRM secrets are added, this section will show overnight scan completions, scores, and follow-up drafts. Currently numbers are not invented.")

    md.append("")
    md.append(f"## 5) Totals (schedule health)")
    md.append(f"- Total schedule entries: {len(schedule)}")
    md.append(f"- Published total: {total_published}")
    md.append(f"- Reviewed total: {total_reviewed}")
    md.append(f"- Overdue un-published: {len([p for p in overdue if not p.get('published')])}")

    md.append("")
    md.append("---")
    md.append(f"_Generated {datetime.now(SAST).isoformat()} SAST by `content-engine/scripts/morning_briefing.py` — sources: `data/happy_hunter_schedule.json`, `git log --since={yesterday}`. Reply to adjust cadence or add recipients._")

    markdown = "\n".join(md)

    # HTML version (simple)
    html = "<html><body style='font-family:Inter,Arial,sans-serif;color:#111;max-width:700px;margin:0 auto;padding:24px'>"
    html += f"<h2 style='color:#0f172a'>Morning Briefing — {date_str} (07:00 SAST)</h2>"
    html += "<p style='color:#475569;font-size:13px'>For Thabo Motsumi, Happy Hunter Digital — auto-generated, every number traceable</p>"
    # Convert markdown tables naively? Keep preformatted for now
    html += "<pre style='white-space:pre-wrap;font-family:monospace;font-size:13px;background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0'>"
    html += markdown.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    html += "</pre></body></html>"

    return {
        "markdown": markdown,
        "html": html,
        "yesterday_published": len(published_yesterday),
        "today_due": len(due_today_unpublished),
        "tomorrow_due": len(due_tomorrow),
        "overdue": len([p for p in overdue if not p.get("published")]),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="Date YYYY-MM-DD (default today SAST)")
    ap.add_argument("--write", action="store_true", help="Write to output/morning-brief-*.md/.html")
    args = ap.parse_args()
    date_str = args.date or datetime.now(SAST).strftime("%Y-%m-%d")
    result = briefing_for(date_str)
    print(result["markdown"])
    if args.write:
        out_dir = Path(__file__).resolve().parents[1] / "output"
        out_dir.mkdir(exist_ok=True)
        (out_dir / f"morning-brief-{date_str}.md").write_text(result["markdown"], encoding="utf-8")
        (out_dir / f"morning-brief-{date_str}.html").write_text(result["html"], encoding="utf-8")
        print(f"\nWrote output/morning-brief-{date_str}.md and .html")
    # Also write to temp for email action to pickup
    Path("/tmp/morning-brief.md").write_text(result["markdown"], encoding="utf-8") if Path("/tmp").exists() else None

if __name__ == "__main__":
    main()
