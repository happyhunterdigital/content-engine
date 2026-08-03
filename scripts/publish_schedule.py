import os
import json
import argparse
from datetime import datetime, timezone, timedelta
import requests

SAST = timezone(timedelta(hours=2))

def parse_args():
    parser = argparse.ArgumentParser(description="Publish scheduled content for August 2026 based on calendar/PDFs.")
    parser.add_argument("--brand", default="all", help="Brand name or 'all'")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (defaults to today in SAST)")
    parser.add_argument("--slot", default="all", help="Time slot: Morning, Midday, Evening, or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Print post details without publishing")
    return parser.parse_args()

def load_schedules():
    schedules = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), "data")
    
    hh_path = os.path.join(data_dir, "happy_hunter_schedule.json")
    if os.path.exists(hh_path):
        with open(hh_path, "r", encoding="utf-8") as f:
            schedules.append(json.load(f))
            
    wellth_path = os.path.join(data_dir, "wellth_schedule.json")
    if os.path.exists(wellth_path):
        with open(wellth_path, "r", encoding="utf-8") as f:
            schedules.append(json.load(f))

    ludo_path = os.path.join(data_dir, "ludo_league_schedule.json")
    if os.path.exists(ludo_path):
        with open(ludo_path, "r", encoding="utf-8") as f:
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

def publish_post(brand_name, post, dry_run=False):
    hashtags_str = " ".join(post.get("hashtags", []))
    formatted_content = f"{post['headline']}\n\n{post['body']}\n\n{hashtags_str}"
    
    print(f"\n--- PUBLISHING FOR: {brand_name} ---")
    print(f"Date: {post['date']} | Slot: {post['slot']} | Platform: {post['platform']} | Pillar: {post['pillar']}")
    if post.get("occasion"):
        print(f"Occasion: {post['occasion']}")
    print(f"Content:\n{formatted_content}\n----------------------------------------")
    
    if dry_run:
        print("[Dry Run] Skipped actual API publishing.")
        return True
        
    # If Facebook/Instagram token is available, publish to Facebook graph API
    if "Happy Hunter" in brand_name:
        page_env = os.getenv("FB_PAGE_ID_HAPPYHUNTER")
        token_env = os.getenv("FB_TOKEN_HAPPYHUNTER")
    elif "Ludo" in brand_name:
        page_env = os.getenv("FB_PAGE_ID_LUDOLEAGUE")
        token_env = os.getenv("FB_TOKEN_LUDOLEAGUE")
    else:
        page_env = os.getenv("FB_PAGE_ID_IWS")
        token_env = os.getenv("FB_TOKEN_IWS")
    
    if page_env and token_env:
        url = f"https://graph.facebook.com/v26.0/{page_env}/feed"
        payload = {"message": formatted_content, "access_token": token_env}
        response = requests.post(url, data=payload, timeout=30)
        if response.status_code == 200:
            print(f"Successfully published to Facebook Page for {brand_name}.")
        else:
            print(f"Failed to publish to Facebook. Status: {response.status_code}, Details: {response.text}")
    else:
        print(f"No Facebook credentials found for {brand_name}. Logged post successfully.")
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
