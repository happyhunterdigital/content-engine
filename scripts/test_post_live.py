import os, requests, json
page_id = os.getenv("FB_PAGE_ID_HAPPYHUNTER")
token = os.getenv("FB_TOKEN_HAPPYHUNTER")
ig_id = os.getenv("IG_USER_ID_HAPPYHUNTER")
print(f"page_id={page_id} ig_id={ig_id} token_len={len(token) if token else 0}")
try:
    r = requests.post(f"https://graph.facebook.com/v26.0/{page_id}/subscribed_apps", data={"access_token": token}, timeout=15)
    print(f"subscribed_apps: {r.status_code} {r.text[:400]}")
except Exception as e:
    print(f"subscribed failed: {e}")
img_url = "https://picsum.photos/seed/happyhunter-test/1200/630"
try:
    r = requests.post(f"https://graph.facebook.com/v26.0/{page_id}/photos", data={"url": img_url, "caption": "Test post from content-engine - Happy Hunter Digital AI visibility audit live. https://www.happyhunterdigital.com/audit", "access_token": token}, timeout=30)
    print(f"FB photo: {r.status_code} {r.text[:600]}")
except Exception as e:
    print(f"FB photo exception: {e}")
if ig_id and token:
    try:
        r = requests.post(f"https://graph.facebook.com/v26.0/{ig_id}/media", data={"image_url": img_url, "caption": "Test post - Happy Hunter Digital. Get your free AI visibility audit - link in bio.", "access_token": token}, timeout=30)
        print(f"IG container: {r.status_code} {r.text[:600]}")
        j=r.json() if r.status_code==200 else {}
        cid=j.get("id")
        if cid:
            import time
            for attempt in range(5):
                time.sleep(10)
                r2=requests.post(f"https://graph.facebook.com/v26.0/{ig_id}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=30)
                print(f"IG publish attempt {attempt+1}: {r2.status_code} {r2.text[:600]}")
                if r2.status_code==200:
                    break
    except Exception as e:
        print(f"IG exception: {e}")
else:
    print("IG skipped - missing ID/token")

# LinkedIn test
linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
linkedin_urn = os.getenv("LINKEDIN_PERSON_URN")
if linkedin_token and linkedin_urn:
    try:
        headers = {"Authorization": f"Bearer {linkedin_token}", "Content-Type": "application/json"}
        payload = {"author": linkedin_urn, "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": "Test post from content-engine - GEO visibility check. Get your free audit: https://www.happyhunterdigital.com/audit"}, "shareMediaCategory": "NONE"}}, "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
        r = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload, timeout=30)
        print(f"LinkedIn: {r.status_code} {r.text[:600]}")
    except Exception as e:
        print(f"LinkedIn exception: {e}")
else:
    print("LinkedIn skipped - missing token/URN")

# X test
x_api_key = os.getenv("X_API_KEY")
x_api_secret = os.getenv("X_API_SECRET")
x_access = os.getenv("X_ACCESS_TOKEN")
x_access_secret = os.getenv("X_ACCESS_SECRET")
if all([x_api_key, x_api_secret, x_access, x_access_secret]):
    try:
        from requests_oauthlib import OAuth1Session
        oauth = OAuth1Session(x_api_key, client_secret=x_api_secret, resource_owner_key=x_access, resource_owner_secret=x_access_secret)
        r = oauth.post("https://api.x.com/2/tweets", json={"text": "Test post from content-engine - AI visibility audit live. Get your free scan: https://www.happyhunterdigital.com/audit"})
        print(f"X response: {r.status_code} {r.text[:500]}")
    except Exception as e:
        print(f"X exception: {e}")
else:
    print("X skipped - missing credentials")
