"""
ANTIGRAVITY JARVIS — AI Image Generation
Uses Pollinations (free), OpenAI DALL-E 3, or Stability AI
"""
import os
import asyncio
import httpx
import base64
from typing import Optional

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

async def generate_image_url(prompt: str, width: int = 1280, height: int = 720,
                              style: str = "photorealistic") -> str:
    """
    Returns a URL or base64 data-URI for a generated image.
    Free via Pollinations, premium via DALL-E 3 or Stability AI.
    """
    # Try OpenAI DALL-E 3 first if key present
    if OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "dall-e-3",
                        "prompt": f"{style}: {prompt}",
                        "n": 1,
                        "size": "1792x1024",
                        "quality": "hd"
                    }
                )
                res.raise_for_status()
                return res.json()["data"][0]["url"]
        except Exception as e:
            print(f"[ImageGen] DALL-E 3 failed: {e}")

    # Free fallback — Pollinations image API
    import urllib.parse
    encoded = urllib.parse.quote(f"{style}: {prompt}")
    seed = abs(hash(prompt)) % 99999
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
    return url


async def generate_project_images(domain: str, title: str) -> dict:
    """
    Generate domain-specific images for a project.
    Returns dict of {name: url} for use in generated HTML/CSS.
    """
    prompts = {
        "food_delivery": {
            "hero":      f"Premium food delivery app hero section, gourmet burger, dark background, neon orange lighting, cinematic, 8k",
            "restaurant": "Modern restaurant interior, warm ambient lighting, bokeh, luxurious dining",
            "food1":     "Gourmet burger with fries, professional food photography, dark background",
            "food2":     "Authentic pizza with fresh ingredients, overhead shot, rustic table",
        },
        "ecommerce": {
            "hero":      f"Premium ecommerce store hero, luxury products, dark elegant background, studio lighting",
            "product1":  "Luxury watch product photography, black background, studio lighting, 8k",
            "product2":  "Premium headphones product shot, minimalist white background, shadows",
            "banner":    "Shopping sale banner, bold colors, premium products, lifestyle",
        },
        "portfolio": {
            "hero":      f"Professional developer portfolio hero, dark background, code on screens, neon purple-blue glow",
            "about":     "Creative developer working, dual monitors, dark room, purple ambient light",
            "project1":  "Modern web app dashboard UI, dark theme, data visualization",
            "project2":  "Mobile app design mockup, clean UI, premium feel",
        },
        "hospital": {
            "hero":      "Modern hospital exterior, glass building, daytime, professional, clean",
            "doctor1":   "Professional doctor portrait, white coat, stethoscope, confident smile, studio",
            "doctor2":   "Female doctor, hospital background, professional portrait, warm lighting",
            "lobby":     "Modern hospital lobby, bright, clean, welcoming interior",
        },
        "saas": {
            "hero":      f"SaaS dashboard app hero, dark gradient background, glowing UI, data charts, premium",
            "dashboard": "Analytics dashboard UI screenshot, dark theme, colorful charts, KPIs",
            "team":      "Modern tech startup team, office, collaborative, diverse",
            "feature":   "Cloud software concept, servers, network, dark tech background",
        },
        "fitness": {
            "hero":      "Premium gym interior, modern equipment, dark dramatic lighting, motivational",
            "trainer":   "Athletic personal trainer, gym background, confident pose, professional",
            "workout":   "Intense workout session, action shot, dramatic lighting, fitness",
            "class":     "Group fitness class, modern gym, energetic, wide angle",
        },
        "travel": {
            "hero":      "Luxury travel destination, tropical beach sunset, golden hour, cinematic",
            "hotel":     "5-star luxury hotel room, ocean view, elegant interior, golden light",
            "city":      "Beautiful city skyline at night, lights, aerial view, stunning",
            "adventure": "Adventure travel, mountains, dramatic landscape, wide angle",
        },
        "blog": {
            "hero":      "Modern blog website hero, minimalist workspace, laptop, coffee, bokeh",
            "author":    "Professional blogger portrait, casual style, natural light, warm",
            "post1":     "Technology blog post cover, abstract digital art, vibrant colors",
            "post2":     "Lifestyle blog aesthetic, flat lay, pastel colors, minimalist",
        },
        "education": {
            "hero":      "Modern online education platform hero, students, laptops, bright campus",
            "course1":   "Programming course thumbnail, code on screen, dark background, colorful",
            "course2":   "Design course cover, creative tools, colorful workspace",
            "student":   "Happy student learning online, laptop, home setup, motivated",
        },
        "generic": {
            "hero":      f"{title} application hero section, modern dark tech background, neon accents, cinematic",
            "feature1":  "Modern app feature illustration, clean design, gradient background",
            "feature2":  "Software dashboard concept, data visualization, premium dark UI",
            "team":      "Professional tech team, modern office, collaborative work environment",
        }
    }

    domain_prompts = prompts.get(domain, prompts["generic"])
    results = {}

    # Generate concurrently
    async def gen_one(name: str, prompt: str):
        try:
            url = await generate_image_url(prompt)
            results[name] = url
        except Exception as e:
            print(f"[ImageGen] Failed {name}: {e}")
            # Fallback to Unsplash for zero-cost
            results[name] = _unsplash_fallback(domain, name)

    tasks = [gen_one(name, prompt) for name, prompt in domain_prompts.items()]
    await asyncio.gather(*tasks)
    return results


def _unsplash_fallback(domain: str, name: str) -> str:
    """Emergency fallback — Unsplash random curated images by topic."""
    topics = {
        "food_delivery": "food,restaurant,burger",
        "ecommerce":     "shopping,luxury,products",
        "portfolio":     "technology,coding,developer",
        "hospital":      "hospital,medical,healthcare",
        "saas":          "technology,software,dashboard",
        "fitness":       "gym,fitness,workout",
        "travel":        "travel,beach,hotel",
        "blog":          "writing,coffee,laptop",
        "education":     "education,learning,students",
        "generic":       "technology,modern,business",
    }
    kw = topics.get(domain, "technology")
    seed = abs(hash(name)) % 1000
    return f"https://source.unsplash.com/1280x720/?{kw}&sig={seed}"
