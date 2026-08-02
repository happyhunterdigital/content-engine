import os
import json
import argparse
import random
import requests
from openai import OpenAI

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Angle rotation keeps posts varied across days without needing external state.
ANGLES = [
    "educational how-to",
    "myth-busting",
    "statistics / data point",
    "common mistake and fix",
    "trend commentary",
    "beginner's quick win",
    "behind-the-scenes insight",
    "controversial-but-true opinion",
]

# Content format specs -> prompt guidance + FB formatting rules.
FORMATS = {
    "post": {
        "description": "a standard single Facebook post",
        "structure": "headline, body (2-4 short paragraphs), hashtags",
        "max_body_words": 120,
    },
    "thread": {
        "description": "a numbered mini-thread presented as one Facebook post (5 short numbered points)",
        "structure": "headline, body (numbered list of 5 punchy points), hashtags",
        "max_body_words": 200,
    },
    "caption": {
        "description": "a short punchy caption suited to a visual post",
        "structure": "headline (hook), body (1-2 sentences), hashtags",
        "max_body_words": 40,
    },
    "ad": {
        "description": "a paid-ad style post with hook, value prop, and clear call-to-action",
        "structure": "headline (hook), body (value prop + CTA), hashtags",
        "max_body_words": 80,
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-page Facebook publisher via DeepSeek AI.")
    parser.add_argument("--brand", required=True, help="Brand or account identifier")
    parser.add_argument("--page_id_env", required=True, help="Environment variable name for Facebook Page ID")
    parser.add_argument("--token_env", required=True, help="Environment variable name for Facebook Page Access Token")
    parser.add_argument("--focus", required=True, help="Core content focus topic")
    parser.add_argument("--format", choices=list(FORMATS.keys()), default="post",
                        help="Content format to generate (default: post)")
    parser.add_argument("--with_image", action="store_true",
                        help="Generate an AI image prompt and attach a free generated image to the post")
    return parser.parse_args()


def _deepseek_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def research_trending_angle(brand_name, focus_topic):
    """Ask DeepSeek to surface a currently-relevant angle within the focus topic.
    Returns a short string describing the trend/angle, or raises on failure."""
    client = _deepseek_client()
    prompt = (
        f"You are a social media strategist for {brand_name}. "
        f"The brand's core focus is: {focus_topic}. "
        f"In 1-2 short sentences, describe ONE specific, currently-relevant sub-topic, question, or trend "
        f"within this focus area that would make a high-engagement Facebook post today. "
        f"Be concrete and specific (not generic). Return plain text only."
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a senior social media strategist. Be concise."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_brand_content(brand_name, focus_topic, content_format, trend_angle=None, writing_angle=None):
    client = _deepseek_client()
    spec = FORMATS[content_format]
    angle = writing_angle or random.choice(ANGLES)
    trend_clause = (
        f"Weave this specific trending angle into the content naturally: \"{trend_angle}\". "
        if trend_angle else ""
    )
    prompt = (
        f"Write {spec['description']} for {brand_name}. "
        f"The primary topic focus is: {focus_topic}. "
        f"Use a {angle} approach. {trend_clause}"
        f"Structure: {spec['structure']}. Keep body under {spec['max_body_words']} words. "
        f"Tone: authoritative, clear, punchy, structured for social media readability. "
        f"Return strictly valid JSON with keys: 'headline', 'body', 'hashtags' (array of strings starting with #)."
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a specialized content marketer outputting strictly valid JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def build_image_prompt(brand_name, focus_topic, headline):
    """Ask DeepSeek for a concise image prompt, used for the free Pollinations API."""
    client = _deepseek_client()
    prompt = (
        f"Write a single-sentence, vivid image-generation prompt for a Facebook banner for {brand_name}. "
        f"Theme: {focus_topic}. Post headline: \"{headline}\". "
        f"Style: clean, modern, professional, no text in image. 30 words max. Plain text only."
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You write concise prompts for image generation models."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_image_url(image_prompt):
    """Free, keyless image via Pollinations. Returns a direct image URL."""
    encoded = requests.utils.quote(image_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true"


def publish_to_facebook(page_id, page_token, content, brand_name, image_url=None):
    hashtags = content.get("hashtags", [])
    hashtags_str = " ".join(hashtags) if isinstance(hashtags, list) else str(hashtags)
    formatted_post = f"{content['headline']}\n\n{content['body']}\n\n{hashtags_str}"

    if image_url:
        # Photo post: upload-by-URL, caption carries the post text.
        url = f"https://graph.facebook.com/v26.0/{page_id}/photos"
        payload = {"url": image_url, "caption": formatted_post, "access_token": page_token}
    else:
        url = f"https://graph.facebook.com/v26.0/{page_id}/feed"
        payload = {"message": formatted_post, "access_token": page_token}

    response = requests.post(url, data=payload, timeout=30)

    if response.status_code == 200:
        print(f"Successfully published post to Facebook Page for {brand_name} (image={'yes' if image_url else 'no'}).")
    else:
        print(f"Failed to publish for {brand_name}. Status: {response.status_code}, Details: {response.text}")


def main():
    args = parse_args()
    page_id = os.getenv(args.page_id_env)
    page_token = os.getenv(args.token_env)

    if not DEEPSEEK_API_KEY:
        raise ValueError("Missing DEEPSEEK_API_KEY secret variable.")
    if not page_id or not page_token:
        raise ValueError(f"Missing Facebook credentials for {args.brand} ({args.page_id_env} or {args.token_env}).")

    trend = None
    try:
        trend = research_trending_angle(args.brand, args.focus)
        print(f"Trend angle for {args.brand}: {trend}")
    except Exception as e:
        print(f"Trend research failed, continuing without it: {e}")

    content = generate_brand_content(args.brand, args.focus, args.format, trend_angle=trend)

    image_url = None
    if args.with_image:
        try:
            img_prompt = build_image_prompt(args.brand, args.focus, content["headline"])
            image_url = generate_image_url(img_prompt)
            print(f"Generated image prompt: {img_prompt}")
        except Exception as e:
            print(f"Image generation failed, posting text-only: {e}")

    publish_to_facebook(page_id, page_token, content, args.brand, image_url=image_url)


if __name__ == "__main__":
    main()
