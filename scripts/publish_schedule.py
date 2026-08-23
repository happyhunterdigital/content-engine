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

CAROUSEL_CTAS = {
    "instagram": "Get your free AI visibility audit — link in bio.",
    "tiktok": "Get your free AI visibility audit — link in bio.",
    "facebook": "Get your free AI visibility audit: https://www.happyhunterdigital.com/audit",
    "x": "Get your free AI visibility audit: https://www.happyhunterdigital.com/audit",
    "linkedin": "Get your free AI visibility audit: https://www.happyhunterdigital.com/audit",
}

def apply_lead_magnet(platform, text):
    """Replace generic lead-magnet CTA with platform-appropriate link."""
    platform = platform.lower()
    cta = CAROUSEL_CTAS.get(platform, "Get your free AI visibility audit: https://www.happyhunterdigital.com/audit")
    if "[FREE_PDF_CAPTION]" in text:
        text = text.replace("[FREE_PDF_CAPTION]", cta)
    if "[FREE_PDF_LINK]" in text:
        text = text.replace("[FREE_PDF_LINK]", cta)
    # Fallback: make sure it ends with a CTA if not present
    if "happyhunterdigital.com" not in text.lower() and "bio" not in text.lower():
        text = text.strip() + "\n\n" + cta
    return text

OPENMONTAGE_HANDOFF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "OpenMontage", "projects")
# also check local assets/videos handoff
LOCAL_VIDEO_HANDOFF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "videos")

# ---------- Instagram + hosting helpers ----------
def get_ig_config(brand_name):
    """Return (ig_user_id, token) for brand, or (None, None) if not configured."""
    brand = brand_name.lower()
    if "happy hunter" in brand:
        return os.getenv("IG_USER_ID_HAPPYHUNTER"), os.getenv("FB_TOKEN_HAPPYHUNTER") or os.getenv("IG_TOKEN_HAPPYHUNTER")
    if "ludo" in brand:
        return os.getenv("IG_USER_ID_LUDOLEAGUE"), os.getenv("FB_TOKEN_LUDOLEAGUE")
    if "wellth" in brand or "iws" in brand:
        return os.getenv("IG_USER_ID_IWS"), os.getenv("FB_TOKEN_IWS")
    # generic fallback
    return os.getenv("IG_USER_ID"), os.getenv("FB_TOKEN_HAPPYHUNTER")

def host_file_for_ig(local_path, resource_type="image"):
    """
    Upload local file to a public host so Instagram Graph can fetch it via image_url/video_url.
    Tries Cloudinary (if CLOUDINARY_CLOUD_NAME + API key/secret or unsigned preset), else tries catbox.moe.
    Returns public URL or None.
    """
    if not os.path.exists(local_path):
        return None
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME") or "dkyg07qvv"
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET")
    # 1) Try Cloudinary signed upload if creds present
    if api_key and api_secret:
        try:
            import time, hashlib
            timestamp = int(time.time())
            params = f"timestamp={timestamp}"
            sig = hashlib.sha1(f"{params}{api_secret}".encode()).hexdigest()
            url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"
            with open(local_path, "rb") as f:
                files = {"file": f}
                data = {"api_key": api_key, "timestamp": timestamp, "signature": sig}
                if upload_preset:
                    data["upload_preset"] = upload_preset
                resp = requests.post(url, data=data, files=files, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("secure_url")
            else:
                print(f"Cloudinary signed upload failed: {resp.status_code} {resp.text[:300]}")
        except Exception as e:
            print(f"Cloudinary signed upload exception: {e}")
    # 2) Try Cloudinary unsigned if preset provided
    if upload_preset:
        try:
            url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"
            with open(local_path, "rb") as f:
                files = {"file": f}
                data = {"upload_preset": upload_preset}
                resp = requests.post(url, data=data, files=files, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("secure_url")
            else:
                print(f"Cloudinary unsigned upload failed: {resp.status_code} {resp.text[:300]}")
        except Exception as e:
            print(f"Cloudinary unsigned upload exception: {e}")
    # 3) Fallback: catbox.moe (no auth, temporary but public)
    try:
        with open(local_path, "rb") as f:
            files = {"fileToUpload": f, "reqtype": (None, "fileupload")}
            resp = requests.post("https://catbox.moe/user/api.php", files=files, timeout=60)
        if resp.status_code == 200 and resp.text.startswith("http"):
            return resp.text.strip()
        else:
            print(f"catbox upload failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"catbox upload exception: {e}")
    return None

def publish_instagram_carousel(ig_user_id, token, slide_paths, caption, dry_run=False):
    """Publish carousel to Instagram via IG Graph API using hosted image URLs."""
    if dry_run:
        print(f"[Dry Run] Instagram carousel: would create {len(slide_paths)} media containers for IG {ig_user_id}")
        for p in slide_paths:
            print(f"  - {p}")
        print(f"Caption: {caption[:200]}")
        return True
    # Host each slide
    hosted_urls = []
    for p in slide_paths:
        url = host_file_for_ig(p, "image")
        if not url:
            print(f"Failed to host slide {p} for Instagram — aborting carousel. Set CLOUDINARY_* or check hosting.")
            return False
        hosted_urls.append(url)
        print(f"Hosted slide for IG: {url}")
    # Create carousel items
    children_ids = []
    for url in hosted_urls:
        resp = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media",
                             data={"image_url": url, "is_carousel_item": "true", "access_token": token}, timeout=60)
        if resp.status_code != 200:
            print(f"IG carousel item creation failed: {resp.text}")
            return False
        children_ids.append(resp.json().get("id"))
        print(f"IG carousel child id: {children_ids[-1]}")
    # Create carousel container
    resp = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media",
                         data={"media_type": "CAROUSEL", "children": ",".join(children_ids), "caption": caption, "access_token": token}, timeout=60)
    if resp.status_code != 200:
        print(f"IG carousel container failed: {resp.text}")
        return False
    creation_id = resp.json().get("id")
    # Publish
    resp = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media_publish",
                         data={"creation_id": creation_id, "access_token": token}, timeout=60)
    if resp.status_code == 200:
        print(f"Successfully published Instagram CAROUSEL {creation_id} -> {resp.json()}")
        return True
    else:
        print(f"IG carousel publish failed: {resp.text}")
        return False

def publish_instagram_reel(ig_user_id, token, video_path, caption, dry_run=False):
    """Publish Reels to Instagram. Requires public video_url."""
    if dry_run:
        print(f"[Dry Run] Instagram Reel: would host {video_path} and create Reels for IG {ig_user_id}")
        return True
    video_url = host_file_for_ig(video_path, "video")
    if not video_url:
        print(f"Failed to host video {video_path} for Instagram Reel. Need Cloudinary or catbox.")
        return False
    print(f"Hosted video for IG Reel: {video_url}")
    resp = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media",
                         data={"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": token}, timeout=60)
    if resp.status_code != 200:
        print(f"IG Reels creation failed: {resp.text}")
        return False
    creation_id = resp.json().get("id")
    print(f"IG Reels creation_id {creation_id}, polling status...")
    # Poll for FINISHED (IG needs processing)
    import time
    for _ in range(30):
        time.sleep(4)
        r = requests.get(f"https://graph.facebook.com/v26.0/{creation_id}", params={"fields": "status_code", "access_token": token}, timeout=15)
        if r.status_code == 200:
            status = r.json().get("status_code")
            print(f"  status: {status}")
            if status == "FINISHED":
                break
            if status in ("ERROR", "EXPIRED"):
                print(f"IG Reels processing failed: {r.text}")
                return False
        else:
            print(f"Status poll failed: {r.text}")
    # Publish
    resp = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media_publish",
                         data={"creation_id": creation_id, "access_token": token}, timeout=60)
    if resp.status_code == 200:
        print(f"Successfully published Instagram REEL {creation_id} -> {resp.json()}")
        return True
    else:
        print(f"IG Reels publish failed: {resp.text}")
        return False

def resolve_video_path(post):
    """Resolve video file for a video/reel post. Checks post['video_path'], local handoff, and OpenMontage renders."""
    candidates = []
    if post.get("video_path"):
        candidates.append(post["video_path"])
    # common handoff filenames
    candidates.extend([
        os.path.join(LOCAL_VIDEO_HANDOFF_DIR, "the-invisibility-tax.mp4"),
        os.path.join(LOCAL_VIDEO_HANDOFF_DIR, "q3-output.mp4"),
        os.path.abspath(os.path.join(LOCAL_VIDEO_HANDOFF_DIR, "the-invisibility-tax.mp4")),
    ])
    # OpenMontage renders
    for proj in ["q3-animated-explainer"]:
        candidates.extend([
            os.path.join(OPENMONTAGE_HANDOFF_DIR, proj, "renders", "the-invisibility-tax.mp4"),
            os.path.join(OPENMONTAGE_HANDOFF_DIR, proj, "exports", "video", "output.mp4"),
        ])
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
        # also try relative to repo root
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alt = os.path.join(repo_root, c) if not os.path.isabs(c) else c
        if os.path.exists(alt):
            return os.path.abspath(alt)
    return None

def publish_post(brand_name, post, dry_run=False):
    format_type = post.get("format", "").lower()
    platform = post.get("platform", "")
    
    is_video = format_type in ["video", "reel"] or "[video]" in post.get("body", "").lower() or "[reel]" in post.get("body", "").lower()
    if is_video:
        caption_text = apply_lead_magnet(platform, f"{post['headline']}\n\n{post['body']}\n\n{' '.join(post.get('hashtags', []))}")
        video_path = resolve_video_path(post)
        print(f"\n--- VIDEO POST FOR: {brand_name} ---")
        print(f"Date: {post['date']} | Format: {format_type} | Platform: {platform} | Headline: {post['headline']}")
        print(f"Resolved video_path: {video_path}")
        print(f"Caption:\n{caption_text}\n----------------------------------------")
        if not video_path:
            print("WARNING: No video file found. Expected at assets/videos/the-invisibility-tax.mp4 or openmontage handoff. Skipping upload but logging caption.")
            print("Handoff instruction: Copy finished mp4 from OpenMontage/projects/<id>/renders/ to content-engine/assets/videos/ and set post['video_path'].")
            return True
        if dry_run:
            print(f"[Dry Run] Would upload video {video_path} to {platform} (Facebook Graph /videos or Instagram Reel).")
            return True
        # Instagram Reels
        if platform.lower() in ["instagram", "tiktok"]:
            ig_user_id, ig_token = get_ig_config(brand_name)
            if not ig_user_id or not ig_token:
                print(f"IG config missing for {brand_name}: IG_USER_ID_HAPPYHUNTER / FB_TOKEN_HAPPYHUNTER not set. Cannot publish Reel to IG.")
                print(f"Set IG_USER_ID_HAPPYHUNTER (from /{{page_id}}?fields=instagram_business_account) and ensure token has instagram_content_publish.")
                print(f"Video still available locally at {video_path} for manual upload.")
                return True
            publish_instagram_reel(ig_user_id, ig_token, video_path, caption_text, dry_run=False)
            return True
        else:
            # Facebook / LinkedIn / X — Facebook Page video upload (default for Happy Hunter)
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
                print(f"No Facebook credentials for {brand_name}. Logged video post.")
                return True
            url = f"https://graph.facebook.com/v26.0/{page_env}/videos"
            try:
                with open(video_path, "rb") as vf:
                    files = {"source": vf}
                    data = {"description": caption_text, "access_token": token_env}
                    resp = requests.post(url, data=data, files=files, timeout=120)
                if resp.status_code == 200:
                    print(f"Successfully published VIDEO to Facebook Page for {brand_name}: {resp.json()}")
                else:
                    print(f"Failed publishing video. Status: {resp.status_code}, Details: {resp.text}")
            except Exception as e:
                print(f"Exception uploading video: {e}")
            return True
        return True
        
    is_carousel = format_type == "carousel" or "SLIDE 1" in post.get("body", "")
    slide_paths = []
    caption_text = apply_lead_magnet(platform, f"{post['headline']}\n\n{post['body']}\n\n{' '.join(post.get('hashtags', []))}")
    
    if is_carousel:
        slide_paths, extracted_caption = render_html_carousel_slides(post['body'], brand_name)
        if extracted_caption.startswith("Caption:"):
            caption_text = apply_lead_magnet(platform, f"{post['headline']}\n\n{extracted_caption}\n\n{' '.join(post.get('hashtags', []))}")
    
    # Route Instagram vs Facebook BEFORE generic Facebook handling
    if platform.lower() in ["instagram", "tiktok"]:
        # Instagram path: carousel or post
        if is_carousel and slide_paths:
            print(f"\n--- INSTAGRAM CAROUSEL FOR: {brand_name} ---")
            print(f"Date: {post['date']} | Slot: {post['slot']} | Pillar: {post['pillar']}")
            print(f"Caption:\n{caption_text}\nSlides: {len(slide_paths)}")
            print("----------------------------------------")
            if dry_run:
                print(f"[Dry Run] Would publish Instagram carousel ({len(slide_paths)} slides) for {brand_name}")
                return True
            ig_user_id, ig_token = get_ig_config(brand_name)
            if not ig_user_id or not ig_token:
                print(f"IG config missing for {brand_name}: IG_USER_ID_HAPPYHUNTER / FB_TOKEN_HAPPYHUNTER not set.")
                print("Cannot publish to Instagram — set IG_USER_ID_HAPPYHUNTER (from Graph /{page_id}?fields=instagram_business_account) and token with instagram_content_publish.")
                print("Falling back to LOGGING only — slides remain at output_slides/*.png for manual upload.")
                return True
            publish_instagram_carousel(ig_user_id, ig_token, slide_paths, caption_text, dry_run=False)
            return True
        elif is_carousel:
            # Should not happen (slide_paths empty but flagged carousel) — fallback
            pass
        else:
            # Instagram single image / text post — not typical; we fallback to carousel logic or log
            print(f"\n--- INSTAGRAM POST FOR: {brand_name} ---")
            print(f"Format {format_type} on Instagram requires image/carousel/reel. This post is text-only — logging for manual handling.")
            print(f"Caption:\n{caption_text}\n----------------------------------------")
            if dry_run:
                print("[Dry Run] Instagram text post — would need image. Logged.")
                return True
            print("No IG publish for text-only. Convert to carousel or Reels, or post manually.")
            return True
            
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
