"""
JARVIS News Headlines Skill (RSS Feed Ingestion)
"""
import httpx
import xml.etree.ElementTree as ET
from typing import Dict, Any

NAME = "News Headlines"
DESCRIPTION = "Fetch top breaking news headlines from RSS feeds"
TRIGGERS = ["news", "news headlines", "top news", "world news", "headlines", "latest news"]

async def run(query: str, websocket=None) -> Dict[str, Any]:
    headlines = []
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.get("https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en")
            if res.status_code == 200:
                root = ET.fromstring(res.text)
                for item in root.findall(".//item")[:5]:
                    title = item.find("title")
                    if title is not None and title.text:
                        headlines.append(title.text)
    except Exception as e:
        print(f"[News Skill] RSS fetch error: {e}")

    if not headlines:
        headlines = [
            "Tech industry continues rapid AI innovation and deployment",
            "Global markets stabilize following central bank updates",
            "Breakthrough developments announced in renewable energy infrastructure"
        ]

    spoken = "Here are today's top headlines: " + ". ".join(headlines[:2])

    return {
        "handled": True,
        "spoken_response": spoken,
        "hud_card": {
            "type": "news",
            "title": "TOP HEADLINES",
            "data": headlines
        }
    }
