import os
import json
import argparse
import requests
from openai import OpenAI

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-page Facebook publisher via DeepSeek AI.")
    parser.add_argument("--brand", required=True, help="Brand or account identifier")
    parser.add_argument("--page_id_env", required=True, help="Environment variable name for Facebook Page ID")
    parser.add_argument("--token_env", required=True, help="Environment variable name for Facebook Page Access Token")
    parser.add_argument("--focus", required=True, help="Core content focus topic")
    return parser.parse_args()

def generate_brand_content(brand_name, focus_topic):
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    
    prompt = (
        f"Generate a high-converting, highly engaging daily social media post for {brand_name}. "
        f"The primary topic focus is: {focus_topic}. "
        f"Keep the tone authoritative, clear, punchy, and structured for social media readability. "
        f"Return the output strictly in valid JSON format with keys: 'headline', 'body', and 'hashtags'."
    )
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a specialized content marketer outputting strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def publish_to_facebook(page_id, page_token, content, brand_name):
    hashtags_str = " ".join(content["hashtags"])
    formatted_post = f"{content['headline']}\n\n{content['body']}\n\n{hashtags_str}"
    
    url = f"https://graph.facebook.com/v26.0/{page_id}/feed"
    payload = {
        "message": formatted_post,
        "access_token": page_token
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print(f"Successfully published daily post to Facebook Page for {brand_name}.")
    else:
        print(f"Failed to publish for {brand_name}. Status Code: {response.status_code}, Details: {response.text}")

def main():
    args = parse_args()
    page_id = os.getenv(args.page_id_env)
    page_token = os.getenv(args.token_env)
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("Missing DEEPSEEK_API_KEY secret variable.")
    if not page_id or not page_token:
        raise ValueError(f"Missing Facebook credentials for {args.brand} ({args.page_id_env} or {args.token_env}).")
        
    content = generate_brand_content(args.brand, args.focus)
    publish_to_facebook(page_id, page_token, content, args.brand)

if __name__ == "__main__":
    main()
