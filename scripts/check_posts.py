import os, requests, json
from datetime import datetime

def check(brand, page_id, token):
    if not page_id or not token:
        print(f"{brand}: missing page_id or token")
        return
    url = f"https://graph.facebook.com/v26.0/{page_id}/posts"
    params = {"access_token": token, "limit": 5, "fields": "message,created_time,id"}
    try:
        r = requests.get(url, params=params, timeout=15)
        print(f"\n--- {brand} FACEBOOK Page {page_id} ---")
        print(f"Status {r.status_code}")
        if r.status_code == 200:
            data = r.json().get("data", [])
            for p in data[:3]:
                msg = (p.get("message") or "")[:120].replace("\n"," / ")
                print(f"{p.get('created_time')} | {p.get('id')} | {msg}")
            if not data:
                print("No posts returned (maybe token lacks pages_read_engagement)")
        else:
            print(r.text[:500])
    except Exception as e:
        print(f"FB check exception: {e}")

def check_ig(ig_id, token):
    if not ig_id or not token:
        print("IG: missing id or token")
        return
    url = f"https://graph.facebook.com/v26.0/{ig_id}/media"
    params = {"access_token": token, "fields": "caption,media_type,timestamp,id", "limit": 5}
    try:
        r = requests.get(url, params=params, timeout=15)
        print(f"\n--- INSTAGRAM {ig_id} ---")
        print(f"Status {r.status_code}")
        if r.status_code == 200:
            data = r.json().get("data", [])
            for m in data[:3]:
                cap = (m.get("caption") or "")[:100].replace("\n"," / ")
                print(f"{m.get('timestamp')} | {m.get('id')} | {m.get('media_type')} | {cap}")
            if not data:
                print("No IG media returned")
        else:
            print(r.text[:500])
    except Exception as e:
        print(f"IG check exception: {e}")

if __name__ == "__main__":
    # Facebook
    check("Happy Hunter", os.getenv("FB_PAGE_ID_HAPPYHUNTER"), os.getenv("FB_TOKEN_HAPPYHUNTER"))
    check("IWS", os.getenv("FB_PAGE_ID_IWS"), os.getenv("FB_TOKEN_IWS"))
    check("Ludo", os.getenv("FB_PAGE_ID_LUDOLEAGUE"), os.getenv("FB_TOKEN_LUDOLEAGUE"))
    # Instagram
    check_ig(os.getenv("IG_USER_ID_HAPPYHUNTER"), os.getenv("FB_TOKEN_HAPPYHUNTER"))
    check_ig(os.getenv("IG_USER_ID_HAPPYHUNTER"), os.getenv("FB_TOKEN_HAPPYHUNTER"))
