import os
import json
import sys
import argparse
import requests
from openai import OpenAI

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-account content generator.")
    parser.add_argument("--brand", required=True, help="Brand or account identifier")
    parser.add_argument("--webhook", required=True, help="Target webhook environment variable name")
    parser.add_argument("--focus", required=True, help="Core content topic focus")
    return parser.parse_args()

def generate_brand_content(brand_name, focus_topic):
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    
    prompt = (
        f"Generate a high-converting daily post for {brand_name}. "
        f"The primary focus is: {focus_topic}. "
        f"Keep the tone authoritative, practical, and tailored to this specific brand audience. "
        f"Return strictly valid JSON with keys: 'headline', 'body', and 'hashtags'."
    )
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a specialized content generator outputting strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def publish_content(webhook_url, content, brand_name):
    formatted_post = f"{content['headline']}\n\n{content['body']}\n\n{' '.join(content['hashtags'])}"
    
    payload = {
        "account": brand_name,
        "content": formatted_post,
        "source": "OpenCode Multi-Account Engine"
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"Successfully published content for {brand_name}.")
    else:
        print(f"Failed publishing for {brand_name}. Status code: {response.status_code}")

def main():
    args = parse_args()
    webhook_url = os.getenv(args.webhook)
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable is missing.")
    if not webhook_url:
        raise ValueError(f"Webhook URL environment variable '{args.webhook}' is missing.")
        
    content = generate_brand_content(args.brand, args.focus)
    publish_content(webhook_url, content, args.brand)

if __name__ == "__main__":
    main()
