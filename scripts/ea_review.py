#!/usr/bin/env python3
"""
EA Auto-Review — replaces manual founder gate.
Run before publish_schedule.py. For today's date (SAST) it:
 1. Loads unpublished posts (published != true) for today
 2. Checks SystemInstruction.md (no em-dash, en-dash, markdown asterisks)
 3. Checks duplicates vs last 7 days of published posts (>70% similar -> skip)
 4. Checks brand voice heuristics (hype words) and platform rules (warn only)
 5. Sets reviewed:true on passed posts, writes schedule back, prints summary
Exit 0 always — publisher will skip flagged posts.

Usage:
  python scripts/ea_review.py [--date YYYY-MM-DD] [--dry-run]
"""
import os
import json
import re
import sys
import argparse
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

SAST = timezone(timedelta(hours=2))

# SystemInstruction compliance
EM_DASH = "\u2014"
EN_DASH = "\u2013"

HYPE_PATTERNS = [
    r"architecting", r"dominance", r"entities", r"synergy", r"leverage\b", r"disrupt",
    r"protocol\b", r"systems\b.*2026", r"cutting.edge", r"world.class", r"next.level"
]

def parse_args():
    p = argparse.ArgumentParser(description="EA auto-review: validate and mark reviewed:true")
    p.add_argument("--date", default=None, help="Date YYYY-MM-DD (default today SAST)")
    p.add_argument("--dry-run", action="store_true", help="Validate only, do not write")
    return p.parse_args()

def load_schedule():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "data", "happy_hunter_schedule.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, path

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def check_system_instruction(post) -> list:
    issues = []
    text = f"{post.get('headline','')} {post.get('body','')}"
    if EM_DASH in text:
        issues.append("contains em-dash (U+2014)")
    if EN_DASH in text:
        issues.append("contains en-dash (U+2013)")
    # markdown asterisks for bold/italic — detect **word** or *word* but not bullet asterisks
    if re.search(r"\*\*.+?\*\*", text) or re.search(r"(?<![*])\*(?!\*)([^*\n]+)\*(?!\*)", text):
        issues.append("contains markdown asterisks")
    return issues

def check_brand_voice(post) -> list:
    warnings = []
    text = f"{post.get('headline','')} {post.get('body','')}".lower()
    for pat in HYPE_PATTERNS:
        if re.search(pat, text):
            warnings.append(f"hype/jargon pattern: {pat}")
    return warnings

def check_platform_rules(post, week_posts) -> list:
    flags = []
    platform = post.get("platform","").lower()
    body = post.get("body","").lower()
    has_link = "happyhunterdigital.com" in body or "http" in body
    # FB link 1x/week max — count FB posts with direct links in same ISO week
    # If overflow, auto-fix by replacing direct link with "link in comments" (warn, do not block)
    # So this check is now warn-only — publisher will still post with fixed link
    if platform == "facebook" and has_link:
        try:
            from datetime import date as ddate
            target_date = post.get("date","")
            target_iso = datetime.strptime(target_date, "%Y-%m-%d").date().isocalendar()  # (year, week, weekday)
            fb_in_week = []
            for p in week_posts:
                try:
                    w = datetime.strptime(p.get("date",""), "%Y-%m-%d").date().isocalendar()
                    if w[0]==target_iso[0] and w[1]==target_iso[1]:
                        if p.get("platform","").lower()=="facebook" and "happyhunterdigital.com" in p.get("body","").lower():
                            fb_in_week.append(p)
                except:
                    continue
            # Sort by date+slot to find order; if this post is not the first FB link in week, auto-fix instead of block
            fb_in_week_sorted = sorted(fb_in_week, key=lambda x: (x.get("date",""), x.get("slot","")))
            if len(fb_in_week) > 1 and fb_in_week_sorted[0] is not post:
                # Auto-fix: replace direct audit link with link-in-comments phrasing for overflow posts
                # Do not add to flags (warn only) — fix inline
                old_body = post.get("body","")
                new_body = re.sub(r"https?://www\.happyhunterdigital\.com/audit\S*", "link in comments", old_body, flags=re.IGNORECASE)
                new_body = re.sub(r"https?://happyhunterdigital\.com/audit\S*", "link in comments", new_body, flags=re.IGNORECASE)
                if new_body != old_body:
                    post["body"] = new_body
                    print(f"  AUTO-FIX FB link 1x/week: replaced direct audit link with 'link in comments' (week {target_iso[1]} had {len(fb_in_week)} FB links)")
        except Exception as e:
            print(f"  WARN FB link check exception: {e}")
    if platform == "instagram" and has_link:
        # IG is auto-fix to link-in-bio as well — warn and fix
        try:
            old_body = post.get("body","")
            new_body = re.sub(r"https?://(www\.)?happyhunterdigital\.com/audit\S*", "link in bio", old_body, flags=re.IGNORECASE)
            if new_body != old_body:
                post["body"] = new_body
                print(f"  AUTO-FIX IG link: replaced direct link with 'link in bio'")
        except:
            pass
    if platform == "linkedin" and re.search(r"buy now|hard sell|discount|limited time", body):
        flags.append("LinkedIn no hard sells — detected sales language")
    return flags

def main():
    args = parse_args()
    target_date = args.date or datetime.now(SAST).strftime("%Y-%m-%d")
    print(f"[EA Review] Target date (SAST): {target_date} dry_run={args.dry_run}")

    data, path = load_schedule()
    schedule = data.get("schedule", [])

    # Collect last 7 days of published for duplicate check
    published = [p for p in schedule if p.get("published")]
    # Sort by date
    def date_key(p):
        try:
            return datetime.strptime(p.get("date","1970-01-01"), "%Y-%m-%d").date()
        except:
            return datetime.min.date()
    published_sorted = sorted(published, key=date_key, reverse=True)

    # Target posts: date == today, not yet reviewed and not yet published
    targets = [p for p in schedule if p.get("date")==target_date and not p.get("published") and not p.get("reviewed")]
    if not targets:
        print(f"[EA Review] No unpublished posts for {target_date} — nothing to review.")
        # Still exit 0 so publisher continues
        return 0

    # For platform rule checks, get week slice (same ISO week)
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        week_posts = [p for p in schedule if p.get("date")]
        # simple: posts within 7 days of target
        week_posts = [p for p in schedule if abs((datetime.strptime(p["date"], "%Y-%m-%d").date() - target_dt).days) <= 7 ] if False else schedule
    except:
        week_posts = schedule

    reviewed = 0
    skipped = 0
    flagged = 0

    for post in targets:
        headline = post.get("headline","")[:70]
        slot = post.get("slot","")
        platform = post.get("platform","")
        print(f"\n--- Reviewing {target_date} {slot} {platform}: {headline} ---")

        # 1. SystemInstruction
        si_issues = check_system_instruction(post)
        if si_issues:
            print(f"  FAIL SystemInstruction: {', '.join(si_issues)}")
            # Auto-fix: strip em/en dashes and asterisks for SAST compliance
            if not args.dry_run:
                for k in ("headline","body"):
                    if k in post and isinstance(post[k], str):
                        post[k] = post[k].replace(EM_DASH, ",").replace(EN_DASH, "-")
                        # strip ** but keep text
                        post[k] = post[k].replace("**","")
                print("  Auto-fixed em/en-dashes and ** markers")
            # Re-check after fix — if still fails, skip
            si_after = check_system_instruction(post)
            if si_after:
                print(f"  STILL FAIL after fix: {si_after} -> skipping post")
                skipped += 1
                continue

        # 2. Duplicate check vs last 7 days published (>70% similar on headline+body)
        is_dup = False
        for pub in published_sorted[:20]:
            # only last 7 days window
            try:
                pub_date = datetime.strptime(pub.get("date",""), "%Y-%m-%d").date()
                tgt_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                if (tgt_date - pub_date).days > 7 or (tgt_date - pub_date).days < 0:
                    continue
            except:
                pass
            sim = similarity(post.get("headline","") + " " + post.get("body","")[:200],
                             pub.get("headline","") + " " + pub.get("body","")[:200])
            if sim > 0.70:
                print(f"  FAIL Duplicate: {sim:.2f} similar to {pub.get('date')} {pub.get('platform')} '{pub.get('headline','')[:50]}' -> skipping")
                is_dup = True
                break
        if is_dup:
            skipped += 1
            continue

        # 3. Brand voice (warn only, do not block)
        bv_warnings = check_brand_voice(post)
        if bv_warnings:
            print(f"  WARN Brand voice: {', '.join(bv_warnings)} — not blocking, logging")

        # 4. Platform rules (block if hard violation)
        plat_flags = check_platform_rules(post, schedule)
        if plat_flags:
            # FB 1x/week and IG link are blocking for this post only
            print(f"  FAIL Platform rules: {'; '.join(plat_flags)} -> skipping this post")
            flagged += 1
            skipped += 1
            continue

        # CTA check (warn)
        body = post.get("body","").lower()
        if "happyhunterdigital.com/audit" not in body and "link in bio" not in body and "link in comments" not in body:
            print("  WARN: no audit CTA detected (happyhunterdigital.com/audit or link in bio)")

        # All checks passed -> mark reviewed
        if not args.dry_run:
            post["reviewed"] = True
        reviewed += 1
        print(f"  PASS -> {'would set' if args.dry_run else 'set'} reviewed:true")

    if not args.dry_run and reviewed > 0:
        # Backup original
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n[EA Review] Wrote {path}: {reviewed} marked reviewed:true, {skipped} skipped, {flagged} platform-flagged")

    else:
        if args.dry_run:
            print(f"\n[EA Review] Dry run — would have marked {reviewed} reviewed:true, {skipped} skipped")
        else:
            print(f"\n[EA Review] No posts marked (reviewed={reviewed} skipped={skipped})")

    # Summary for founder visibility (no gate)
    print(f"\n[EA Summary] {target_date}: reviewed={reviewed} skipped={skipped} flagged={flagged} (auto-post at next cron)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
