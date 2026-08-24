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

# ---------- Instagram helpers (auto via Graph if IG_USER_ID set, else pack) ----------
def get_ig_config(brand_name):
    b = brand_name.lower()
    if "happy hunter" in b:
        return os.getenv("IG_USER_ID_HAPPYHUNTER"), os.getenv("FB_TOKEN_HAPPYHUNTER") or os.getenv("IG_TOKEN_HAPPYHUNTER")
    if "ludo" in b:
        return os.getenv("IG_USER_ID_LUDOLEAGUE"), os.getenv("FB_TOKEN_LUDOLEAGUE")
    if "wellth" in b or "iws" in b:
        return os.getenv("IG_USER_ID_IWS"), os.getenv("FB_TOKEN_IWS")
    return os.getenv("IG_USER_ID"), os.getenv("FB_TOKEN_HAPPYHUNTER")

def host_file_for_ig(local_path, resource_type="image"):
    """
    Upload local file to a public host for Instagram Graph (needs image_url/video_url).
    Tries Cloudinary signed -> Cloudinary unsigned -> 0x0.st -> catbox.
    Returns public URL or None.
    """
    if not os.path.exists(local_path):
        print(f"host_file_for_ig: file not found {local_path}")
        return None
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME") or "dkyg07qvv"
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET")
    print(f"host_file_for_ig: {local_path} ({resource_type}) cloud={cloud_name} key={'set' if api_key else 'missing'} secret={'set' if api_secret else 'missing'} preset={upload_preset or 'none'}")
    # 1) Cloudinary signed (most reliable, uses your dkyg07qvv secrets)
    if api_key and api_secret:
        try:
            import time, hashlib
            timestamp = int(time.time())
            # signature = sha1(sorted_params + api_secret). For timestamp-only, params = timestamp=...
            to_sign = f"timestamp={timestamp}{api_secret}"
            sig = hashlib.sha1(to_sign.encode()).hexdigest()
            url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"
            with open(local_path, "rb") as f:
                files = {"file": f}
                data = {"api_key": api_key, "timestamp": timestamp, "signature": sig}
                resp = requests.post(url, data=data, files=files, timeout=60)
            print(f"Cloudinary signed resp {resp.status_code}: {resp.text[:400]}")
            if resp.status_code == 200:
                surl = resp.json().get("secure_url")
                if surl:
                    print(f"Cloudinary signed hosted: {surl}")
                    return surl
            else:
                print(f"Cloudinary signed upload failed: {resp.status_code} {resp.text[:500]}")
        except Exception as e:
            print(f"Cloudinary signed upload exception: {e}")
    else:
        print("Cloudinary signed skipped (missing API key/secret)")
    # 2) 0x0.st (no auth, 512MB limit, permanent)
    for host_url, field in [("https://0x0.st", "file"), ("https://catbox.moe/user/api.php", "fileToUpload")]:
        try:
            with open(local_path, "rb") as f:
                if "0x0.st" in host_url:
                    files = {"file": f}
                    resp = requests.post(host_url, files=files, timeout=60)
                    txt = resp.text.strip()
                    print(f"{host_url} resp {resp.status_code}: {txt[:300]}")
                    if resp.status_code == 200 and txt.startswith("http"):
                        return txt
                else:
                    files = {"fileToUpload": f}
                    data = {"reqtype": "fileupload"}
                    resp = requests.post(host_url, files=files, data=data, timeout=60)
                    txt = resp.text.strip()
                    print(f"catbox resp {resp.status_code}: {txt[:300]}")
                    if resp.status_code == 200 and txt.startswith("http"):
                        return txt
        except Exception as e:
            print(f"{host_url} upload exception: {e}")
    print(f"host_file_for_ig: all hosts failed for {local_path}")
    return None

def verify_ig_id(ig_user_id, token):
    """Log which IG username an ID maps to — helps confirm happyhunterdigital vs Business opportunities."""
    try:
        r = requests.get(f"https://graph.facebook.com/v26.0/{ig_user_id}", params={"fields": "username,name,profile_picture_url", "access_token": token}, timeout=15)
        if r.status_code == 200:
            j = r.json()
            print(f"IG ID {ig_user_id} -> username @{j.get('username')} name {j.get('name')}")
            return j.get("username")
        else:
            print(f"verify_ig_id failed: {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"verify_ig_id exception: {e}")
    return None

def publish_instagram_carousel_graph(ig_user_id, token, slide_paths, caption):
    verify_ig_id(ig_user_id, token)
    hosted = []
    for p in slide_paths:
        url = host_file_for_ig(p, "image")
        if not url:
            print(f"Failed to host {p} for IG Graph")
            return False
        hosted.append(url)
        print(f"Hosted for IG Graph: {url}")
    children = []
    for url in hosted:
        r = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media", data={"image_url": url, "is_carousel_item": "true", "access_token": token}, timeout=60)
        if r.status_code != 200:
            print(f"IG carousel item failed: {r.text}")
            return False
        children.append(r.json().get("id"))
    r = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media", data={"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption, "access_token": token}, timeout=60)
    if r.status_code != 200:
        print(f"IG carousel container failed: {r.text}")
        return False
    cid = r.json().get("id")
    r = requests.post(f"https://graph.facebook.com/v26.0/{ig_user_id}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=60)
    if r.status_code == 200:
        print(f"Successfully published Instagram CAROUSEL {cid} -> {r.json()}")
        return True
    print(f"IG carousel publish failed: {r.text}")
    return False

def write_instagram_pack(brand_name, post, slide_paths, caption, hosted_urls=None):
    """Write Instagram manual pack: caption.txt, links.txt, hosted URLs. No IG API needed."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pack_root = os.path.join(repo_root, "instagram_pack", post["date"])
    safe_slot = re.sub(r'[^0-9a-zA-Z]+', '-', post["slot"])
    safe_headline = re.sub(r'[^A-Za-z0-9]+', '-', post["headline"])[:40].strip('-')
    pack_dir = os.path.join(pack_root, f"{post['platform']}_{safe_slot}_{safe_headline}")
    os.makedirs(pack_dir, exist_ok=True)
    # Clean caption: paragraphs, bold highlights (Unicode bold via ** removed -> uppercase), no AI markers
    clean_caption = caption.replace("**", "").replace("*", "").strip()
    # Write caption
    with open(os.path.join(pack_dir, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(clean_caption + "\n")
    # Write links
    with open(os.path.join(pack_dir, "links.txt"), "w", encoding="utf-8") as f:
        f.write(f"Brand: {brand_name}\nDate: {post['date']} Slot: {post['slot']} Platform: {post['platform']}\n")
        f.write(f"Headline: {post['headline']}\n")
        if hosted_urls:
            f.write("\nHosted image URLs (Cloudinary/catbox):\n")
            for i, u in enumerate(hosted_urls, 1):
                f.write(f"Slide {i}: {u}\n")
        f.write("\nLocal slides:\n")
        for p in slide_paths:
            f.write(f"{p}\n")
        f.write(f"\nCaption preview:\n{clean_caption[:500]}\n")
    # Copy slides into pack for easy download
    for p in slide_paths:
        try:
            import shutil
            shutil.copy(p, os.path.join(pack_dir, os.path.basename(p)))
        except: pass
    print(f"Instagram pack written: {pack_dir}")
    if hosted_urls:
        print("Hosted URLs:")
        for u in hosted_urls:
            print(f"  {u}")
    return pack_dir

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
        # Instagram Reels -> pack mode (no IG_USER_ID needed)
        if platform.lower() in ["instagram", "tiktok"]:
            print(f"Instagram/TikTok Reel: generating manual pack (no IG API needed).")
            hosted_video = None if dry_run else host_file_for_ig(video_path, "video")
            if hosted_video:
                print(f"Hosted video for manual IG post: {hosted_video}")
            pack_dir = write_instagram_pack(brand_name, post, [video_path], caption_text, [hosted_video] if hosted_video else [])
            print(f"Reel pack ready at {pack_dir} — download artifact or copy caption.txt to Instagram app.")
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
    
    # Route Instagram vs Facebook BEFORE generic Facebook handling — try Graph auto, fallback to pack
    if platform.lower() in ["instagram", "tiktok"]:
        if is_carousel and slide_paths:
            print(f"\n--- INSTAGRAM CAROUSEL FOR: {brand_name} ---")
            print(f"Date: {post['date']} | Slot: {post['slot']} | Pillar: {post['pillar']}")
            print(f"Caption:\n{caption_text}\nSlides: {len(slide_paths)}")
            print("----------------------------------------")
            if dry_run:
                print(f"[Dry Run] Would publish Instagram carousel ({len(slide_paths)} slides) for {brand_name}")
                write_instagram_pack(brand_name, post, slide_paths, caption_text, [])
                return True
            ig_user_id, ig_token = get_ig_config(brand_name)
            if ig_user_id and ig_token:
                print(f"IG_USER_ID found ({ig_user_id[:6]}...), attempting Graph auto-publish to Instagram...")
                if publish_instagram_carousel_graph(ig_user_id, ig_token, slide_paths, caption_text):
                    # also write pack as backup
                    try:
                        hosted = []
                        for p in slide_paths:
                            u = host_file_for_ig(p, "image")
                            hosted.append(u or "(local only)")
                        write_instagram_pack(brand_name, post, slide_paths, caption_text, hosted)
                    except: pass
                    return True
                print("Graph publish failed, falling back to pack mode.")
            # Host slides to Cloudinary (or catbox fallback) for public URLs
            hosted = []
            for p in slide_paths:
                url = host_file_for_ig(p, "image")
                if url:
                    hosted.append(url)
                    print(f"Hosted for IG: {url}")
                else:
                    print(f"Warning: failed to host {p} — pack will still contain local copy.")
                    hosted.append("(local only)")
            pack_dir = write_instagram_pack(brand_name, post, slide_paths, caption_text, hosted)
            print(f"Instagram pack ready. In GitHub Actions download artifact `instagram-pack-{post['date']}` or grab from {pack_dir}")
            print(f"To post: open Instagram app → New Post → Carousel → select {len(slide_paths)} slides from {pack_dir} → Paste caption.txt → Publish. Link in bio CTA is audit.")
            return True
        elif is_carousel:
            pass
        else:
            print(f"\n--- INSTAGRAM POST FOR: {brand_name} ---")
            print(f"Format {format_type} on Instagram requires image/carousel/reel. Logging pack for manual handling.")
            print(f"Caption:\n{caption_text}\n----------------------------------------")
            if dry_run:
                print("[Dry Run] Instagram text post — pack logged.")
                write_instagram_pack(brand_name, post, slide_paths, caption_text, [])
                return True
            write_instagram_pack(brand_name, post, slide_paths, caption_text, [])
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
