# OpenMontage Handoff

This folder receives finished videos from OpenMontage for publishing via content-engine.

## Source
- OpenMontage project: OpenMontage/projects/q3-animated-explainer/
- Render: enders/the-invisibility-tax.mp4
- Export bundle: exports/video/output.mp4

## Current handoff files (copied 2026-08-23)
- assets/videos/the-invisibility-tax.mp4 (2.2 MB) - main render, audit CTA embedded
- assets/videos/q3-output.mp4 (duplicate of export bundle)

## How OpenMontage hands off to content-engine
1. OpenMontage finishes render -> projects/<id>/renders/final.mp4 + exports/video/output.mp4 + exports/metadata/*
2. Copy mp4 to content-engine/assets/videos/ (done by agent or manual copy)
3. Schedule a video post in data/happy_hunter_schedule.json with:
   {
     "format": "video",
     "platform": "Facebook" | "Instagram",
     "headline": "...",
     "body": "... https://www.happyhunterdigital.com/audit ...",
     "video_path": "assets/videos/the-invisibility-tax.mp4",
     "hashtags": [...]
   }
4. content-engine scripts/publish_schedule.py uploads via Facebook Graph /{page_id}/videos (Facebook) or Instagram Content Publishing API (Instagram reels). See publish_schedule.py:publish_post() video handling.
5. GitHub Actions daily_post.yml will pick up video posts when scheduled date matches; requires secrets FB_PAGE_ID_HAPPYHUNTER / FB_TOKEN_HAPPYHUNTER (and IG_USER_ID for Instagram when added).

## CTA
All video descriptions now use: https://www.happyhunterdigital.com/audit (replaces old assets/...pdf?fbclid=... link)
