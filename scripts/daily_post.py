import os
import json
import argparse
import requests
import fal_client
from openai import OpenAI

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-page Facebook Video Publisher via Seedance 2.0.")
    parser.add_argument("--brand", required=True, help="Brand or account identifier")
    parser.add_argument("--page_id_env", required=True, help="Env variable name for Facebook Page ID")
    parser.add_argument("--token_env", required=True, help="Env variable name for Facebook Page Access Token")
    parser.add_argument("--focus", required=True, help="Core content focus topic")
    return parser.parse_args()

def generate_post_and_video_prompt(brand_name, focus_topic):
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    
    prompt = (
        f"Generate a high-converting social media post for {brand_name}. "
        f"Topic focus: {focus_topic}. "
        f"Also write a vivid visual video prompt for Seedance 2.0 to generate a cinematic clip matching this brand. "
        f"Avoid generating text or logos in the video prompt. "
        f"Return strictly valid JSON with keys: 'headline', 'body', 'hashtags', and 'video_prompt'."
    )
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You output strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def generate_seedance_video(video_prompt):
    print(f"Submitting prompt to Seedance 2.0 via fal-client: '{video_prompt}'")
    
    # fal-client automatically picks up FAL_KEY from the environment
    result = fal_client.subscribe(
        "bytedance/seedance-2.0/text-to-video",
        arguments={
            "prompt": video_prompt,
            "resolution": "720p",
            "duration": "5",
            "aspect_ratio": "16:9",
            "generate_audio": True
        }
    )
    
    video_url = result.get("video", {}).get("url")
    if not video_url:
        raise RuntimeError(f"Seedance API failed to return video URL. Output: {result}")
        
    print(f"Seedance 2.0 video generated successfully: {video_url}")
    return video_url

def publish_video_to_facebook(page_id, page_token, content, video_url, brand_name):
    formatted_post = f"{content['headline']}\n\n{content['body']}\n\n{' '.join(content['hashtags'])}"
    
    url = f"https://graph.facebook.com/v26.0/{page_id}/videos"
    payload = {
        "description": formatted_post,
        "file_url": video_url,
        "access_token": page_token
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print(f"Successfully published Seedance 2.0 Video Post for {brand_name}.")
    else:
        print(f"Failed publishing video for {brand_name}. Status: {response.status_code}, Response: {response.text}")

def main():
    args = parse_args()
    page_id = os.getenv(args.page_id_env)
    page_token = os.getenv(args.token_env)
    
    if not DEEPSEEK_API_KEY or not os.getenv("FAL_KEY"):
        raise ValueError("Missing DEEPSEEK_API_KEY or FAL_KEY environment variable.")
    if not page_id or not page_token:
        raise ValueError(f"Missing Facebook credentials for {args.brand}.")
        
    content = generate_post_and_video_prompt(args.brand, args.focus)
    video_url = generate_seedance_video(content["video_prompt"])
    publish_video_to_facebook(page_id, page_token, content, video_url, args.brand)

if __name__ == "__main__":
    main()
