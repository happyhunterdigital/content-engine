import os
import json
import argparse
import re
import sys
from datetime import datetime, timezone, timedelta
import requests
from playwright.sync_api import sync_playwright

# Ensure stdout handles UTF-8 clean output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

SAST = timezone(timedelta(hours=2))
LOGO_URL = "https://res.cloudinary.com/dkyg07qvv/image/upload/v1780205914/happyhunterdigital_logo_l61qn8.jpg"

def parse_args():
    parser = argparse.ArgumentParser(description="Publish scheduled content with Playwright HTML/CSS Option 1 slide generation.")
    parser.add_argument("--brand", default="all", help="Brand name or 'all'")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (defaults to today in SAST)")
    parser.add_argument("--slot", default="all", help="Time slot: Morning, Midday, Evening, or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Print post details and generate local slide images without posting")
    return parser.parse_args()

def load_schedules():
    schedules = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), "data")
    
    for filename in ["happy_hunter_schedule.json", "wellth_schedule.json", "ludo_league_schedule.json"]:
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                schedules.append(json.load(f))
    return schedules

def normalize_slot(slot_str):
    s = slot_str.lower()
    if "08" in s or "07" in s or "09" in s or "am" in s or "morn" in s:
        return "morning"
    elif "11" in s or "12" in s or "13" in s or "midday" in s:
        return "midday"
    elif "15" in s or "17" in s or "18" in s or "19" in s or "pm" in s or "eve" in s:
        return "evening"
    return s

def render_html_carousel_slides(body_text, brand_name):
    """Parse SLIDE 1, SLIDE 2 etc. and render 1080x1080 HTML/CSS slides via Playwright Chromium."""
    slide_matches = re.split(r'(SLIDE\s+\d+[^:\n]*:)', body_text, flags=re.IGNORECASE)
    
    parsed_slides = []
    caption = body_text
    
    if len(slide_matches) > 1:
        for i in range(1, len(slide_matches), 2):
            header = slide_matches[i].strip().rstrip(':')
            content = slide_matches[i+1].strip() if i+1 < len(slide_matches) else ""
            if "Caption:" in content or "CAPTION:" in content:
                parts = re.split(r'Caption:', content, flags=re.IGNORECASE)
                content = parts[0].strip()
                caption = "Caption: " + parts[1].strip()
            parsed_slides.append((header, content))
            
    if not parsed_slides:
        parsed_slides = [("SLIDE 1", body_text)]
        
    os.makedirs("output_slides", exist_ok=True)
    slide_image_paths = []
    
    total_slides = len(parsed_slides)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        
        for idx, (title, content) in enumerate(parsed_slides, start=1):
            clean_content = content.strip('"\'')
            
            html_template = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      width: 1080px;
      height: 1080px;
      background-color: #050505;
      color: #FFFFFF;
      font-family: 'Inter', sans-serif;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 80px;
      position: relative;
      overflow: hidden;
    }}
    body::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background-size: 40px 40px;
      background-image: 
        linear-gradient(to right, rgba(234, 179, 8, 0.03) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(234, 179, 8, 0.03) 1px, transparent 1px);
      z-index: 1;
    }}
    .top-bar {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 8px;
      background: linear-gradient(90deg, #EF4444 0%, #EAB308 100%);
      z-index: 10;
    }}
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 10;
    }}
    .brand-group {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .logo {{
      width: 75px;
      height: 75px;
      border-radius: 12px;
      border: 2px solid #EAB308;
      object-fit: cover;
    }}
    .brand-name {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 2px;
      color: #EAB308;
      text-transform: uppercase;
    }}
    .slide-badge {{
      background: rgba(234, 179, 8, 0.12);
      border: 1px solid #EAB308;
      color: #EAB308;
      padding: 10px 22px;
      border-radius: 20px;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 1px;
    }}
    .content {{
      z-index: 10;
      margin-top: 30px;
      margin-bottom: 30px;
      flex-grow: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .slide-title {{
      font-size: 46px;
      font-weight: 900;
      line-height: 1.25;
      color: #FFFFFF;
      margin-bottom: 35px;
      text-transform: uppercase;
      letter-spacing: -0.5px;
    }}
    .slide-title span {{
      color: #EAB308;
    }}
    .slide-body {{
      font-size: 32px;
      font-weight: 500;
      line-height: 1.55;
      color: #E2E8F0;
      white-space: pre-line;
      background: rgba(255, 255, 255, 0.02);
      padding: 30px;
      border-left: 4px solid #EAB308;
      border-radius: 0 12px 12px 0;
    }}
    .footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid rgba(255, 255, 255, 0.12);
      padding-top: 30px;
      z-index: 10;
    }}
    .tagline {{
      font-size: 18px;
      font-weight: 700;
      color: #94A3B8;
      letter-spacing: 1.5px;
    }}
    .swipe-prompt {{
      font-size: 18px;
      font-weight: 800;
      color: #EAB308;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
  </style>
</head>
<body>
  <div class="top-bar"></div>
  
  <div class="header">
    <div class="brand-group">
      <img class="logo" src="{LOGO_URL}" alt="{brand_name}">
      <div class="brand-name">{brand_name}</div>
    </div>
    <div class="slide-badge">SLIDE {idx} / {total_slides}</div>
  </div>

  <div class="content">
    <div class="slide-title">{title}</div>
    <div class="slide-body">{clean_content}</div>
  </div>

  <div class="footer">
    <div class="tagline">DIGITAL ENTITY ARCHITECTURE • SOUTH AFRICA</div>
    <div class="swipe-prompt">SWIPE ➔</div>
  </div>
</body>
</html>"""
            
            page.set_content(html_template, wait_until="networkidle")
            path = os.path.abspath(f"output_slides/slide_{idx}.png")
            page.screenshot(path=path)
            slide_image_paths.append(path)
            
        browser.close()
        
    return slide_image_paths, caption

def publish_post(brand_name, post, dry_run=False):
    format_type = post.get("format", "").lower()
    
    # Check if this post is a video / reel that should be skipped per user instruction
    if format_type in ["video", "reel"] or "[video]" in post.get("body", "").lower() or "[reel]" in post.get("body", "").lower():
        print(f"\n--- SKIPPING VIDEO POST FOR: {brand_name} ---")
        print(f"Date: {post['date']} | Format: {format_type} | Headline: {post['headline']}")
        print("Reason: Video-only post skipped as requested ('Skip videos when you cant create').")
        return True
        
    is_carousel = format_type == "carousel" or "SLIDE 1" in post.get("body", "")
    slide_paths = []
    caption_text = f"{post['headline']}\n\n{post['body']}\n\n{' '.join(post.get('hashtags', []))}"
    
    if is_carousel:
        slide_paths, extracted_caption = render_html_carousel_slides(post['body'], brand_name)
        if extracted_caption.startswith("Caption:"):
            caption_text = f"{post['headline']}\n\n{extracted_caption}\n\n{' '.join(post.get('hashtags', []))}"
            
    print(f"\n--- PUBLISHING FOR: {brand_name} ---")
    print(f"Date: {post['date']} | Slot: {post['slot']} | Platform: {post['platform']} | Pillar: {post['pillar']}")
    print(f"Format: {format_type} (Option 1 HTML Carousel slides: {len(slide_paths)})")
    print(f"Caption / Content:\n{caption_text}\n----------------------------------------")
    
    if dry_run:
        print("[Dry Run] Skipped actual API publishing. Option 1 HTML slide PNGs saved to output_slides/.")
        return True
        
    if "Happy Hunter" in brand_name:
        page_env = os.getenv("FB_PAGE_ID_HAPPYHUNTER")
        token_env = os.getenv("FB_TOKEN_HAPPYHUNTER")
    elif "Ludo" in brand_name:
        page_env = os.getenv("FB_PAGE_ID_LUDOLEAGUE")
        token_env = os.getenv("FB_TOKEN_LUDOLEAGUE")
    else:
        page_env = os.getenv("FB_PAGE_ID_IWS")
        token_env = os.getenv("FB_TOKEN_IWS")
        
    if not page_env or not token_env:
        print(f"No Facebook credentials found for {brand_name}. Logged post successfully.")
        return True
        
    if is_carousel and slide_paths:
        media_fbids = []
        for path in slide_paths:
            url = f"https://graph.facebook.com/v26.0/{page_env}/photos"
            with open(path, "rb") as img_file:
                files = {"source": img_file}
                data = {"published": "false", "access_token": token_env}
                resp = requests.post(url, data=data, files=files, timeout=60)
                if resp.status_code == 200:
                    media_fbids.append(resp.json().get("id"))
                else:
                    print(f"Failed uploading slide photo: {resp.text}")
                    
        if media_fbids:
            url = f"https://graph.facebook.com/v26.0/{page_env}/feed"
            payload = {
                "message": caption_text,
                "access_token": token_env
            }
            for idx, fbid in enumerate(media_fbids):
                payload[f"attached_media[{idx}]"] = json.dumps({"media_fbid": fbid})
                
            resp = requests.post(url, data=payload, timeout=30)
            if resp.status_code == 200:
                print(f"Successfully published Option 1 HTML Carousel to Facebook Page for {brand_name}.")
            else:
                print(f"Failed publishing carousel post. Status: {resp.status_code}, Details: {resp.text}")
        else:
            print("Failed uploading slide images, posting text fallback.")
            requests.post(f"https://graph.facebook.com/v26.0/{page_env}/feed", data={"message": caption_text, "access_token": token_env}, timeout=30)
    else:
        url = f"https://graph.facebook.com/v26.0/{page_env}/feed"
        payload = {"message": caption_text, "access_token": token_env}
        resp = requests.post(url, data=payload, timeout=30)
        if resp.status_code == 200:
            print(f"Successfully published post to Facebook Page for {brand_name}.")
        else:
            print(f"Failed to publish to Facebook. Status: {resp.status_code}, Details: {resp.text}")
            
    return True

def main():
    args = parse_args()
    target_date = args.date or datetime.now(SAST).strftime("%Y-%m-%d")
    print(f"Target publishing date (SAST): {target_date}, Slot: {args.slot}, Brand: {args.brand}")
    
    schedules = load_schedules()
    published_count = 0
    
    for brand_data in schedules:
        brand_name = brand_data["brand"]
        if args.brand != "all" and args.brand.lower() not in brand_name.lower():
            continue
            
        for post in brand_data.get("schedule", []):
            if post["date"] == target_date:
                if args.slot != "all" and normalize_slot(post["slot"]) != normalize_slot(args.slot):
                    continue
                publish_post(brand_name, post, dry_run=args.dry_run)
                published_count += 1
                
    print(f"\nTotal posts matched and processed for {target_date}: {published_count}")

if __name__ == "__main__":
    main()
