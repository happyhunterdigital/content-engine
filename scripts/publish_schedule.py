import os
import json
import argparse
import re
import textwrap
from datetime import datetime, timezone, timedelta
import requests
from PIL import Image, ImageDraw, ImageFont

SAST = timezone(timedelta(hours=2))

def parse_args():
    parser = argparse.ArgumentParser(description="Publish scheduled content for August 2026 with automated visual & carousel rendering.")
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
    if "08" in s or "am" in s or "morn" in s:
        return "morning"
    elif "12" in s or "13" in s or "midday" in s:
        return "midday"
    elif "18" in s or "pm" in s or "eve" in s:
        return "evening"
    return s

def generate_carousel_slides(body_text, brand_name):
    """Parse SLIDE 1, SLIDE 2 etc. from text and generate high-end PNG slide images."""
    slides = []
    caption = body_text
    
    # Extract slides using regex (e.g. SLIDE 1 (cover): "..." or SLIDE 2: "...")
    slide_matches = re.split(r'(SLIDE\s+\d+[^:\n]*:)', body_text, flags=re.IGNORECASE)
    
    parsed_slides = []
    if len(slide_matches) > 1:
        # slide_matches[0] might be empty or caption intro
        for i in range(1, len(slide_matches), 2):
            header = slide_matches[i].strip()
            content = slide_matches[i+1].strip() if i+1 < len(slide_matches) else ""
            # Clean up trailing caption if present
            if "Caption:" in content:
                parts = content.split("Caption:")
                content = parts[0].strip()
                caption = "Caption: " + parts[1].strip()
            parsed_slides.append((header, content))
    
    if not parsed_slides:
        # Fallback if no explicit SLIDE tags found
        parsed_slides = [("SLIDE 1", body_text)]
        
    os.makedirs("output_slides", exist_ok=True)
    slide_image_paths = []
    
    for idx, (header, text) in enumerate(parsed_slides, start=1):
        # Create 1080x1080 square image
        img = Image.new("RGB", (1080, 1080), color=(15, 23, 42)) # Slate dark modern background
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("arial.ttf", 46)
            font_body = ImageFont.truetype("arial.ttf", 40)
            font_footer = ImageFont.truetype("arial.ttf", 26)
        except:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_footer = ImageFont.load_default()
            
        # Header accent bar & brand
        draw.rectangle([(80, 80), (160, 92)], fill=(212, 160, 23)) # Gold accent
        draw.text((185, 76), brand_name.upper(), fill=(212, 160, 23), font=font_footer)
        
        # Slide Header / Title
        draw.text((80, 180), header.upper(), fill=(255, 255, 255), font=font_title)
        
        # Wrapped Body text
        clean_text = text.strip('"\'')
        wrapped_lines = textwrap.wrap(clean_text, width=32)
        y_text = 320
        for line in wrapped_lines:
            draw.text((80, y_text), line, fill=(226, 232, 240), font=font_body)
            y_text += 58
            
        # Footer
        draw.text((80, 980), f"Slide {idx} of {len(parsed_slides)}  •  Swipe for more", fill=(148, 163, 184), font=font_footer)
        
        path = os.path.abspath(f"output_slides/slide_{idx}.png")
        img.save(path)
        slide_image_paths.append(path)
        
    return slide_image_paths, caption

def publish_post(brand_name, post, dry_run=False):
    is_carousel = post.get("format") == "carousel" or "SLIDE 1" in post.get("body", "")
    
    slide_paths = []
    caption_text = f"{post['headline']}\n\n{post['body']}\n\n{' '.join(post.get('hashtags', []))}"
    
    if is_carousel:
        slide_paths, extracted_caption = generate_carousel_slides(post['body'], brand_name)
        if extracted_caption.startswith("Caption:"):
            caption_text = f"{post['headline']}\n\n{extracted_caption}\n\n{' '.join(post.get('hashtags', []))}"
            
    print(f"\n--- PUBLISHING FOR: {brand_name} ---")
    print(f"Date: {post['date']} | Slot: {post['slot']} | Platform: {post['platform']} | Pillar: {post['pillar']}")
    print(f"Format: {post.get('format', 'post')} (Carousel slides generated: {len(slide_paths)})")
    print(f"Caption / Content:\n{caption_text}\n----------------------------------------")
    
    if dry_run:
        print("[Dry Run] Skipped actual API publishing. Slide images saved locally.")
        return True
        
    # Retrieve Facebook credentials
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
        # Multi-photo carousel upload
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
            # Publish feed post attaching the uploaded photo IDs
            url = f"https://graph.facebook.com/v26.0/{page_env}/feed"
            payload = {
                "message": caption_text,
                "access_token": token_env
            }
            for idx, fbid in enumerate(media_fbids):
                payload[f"attached_media[{idx}]"] = json.dumps({"media_fbid": fbid})
                
            resp = requests.post(url, data=payload, timeout=30)
            if resp.status_code == 200:
                print(f"Successfully published visual carousel to Facebook Page for {brand_name}.")
            else:
                print(f"Failed publishing carousel post. Status: {resp.status_code}, Details: {resp.text}")
        else:
            print("Failed to upload carousel slide images, posting text fallback.")
            requests.post(f"https://graph.facebook.com/v26.0/{page_env}/feed", data={"message": caption_text, "access_token": token_env}, timeout=30)
    else:
        # Standard text or single photo post
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
