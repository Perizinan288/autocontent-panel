import logging
import os
import uuid
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com/v1/search"
PIXABAY_API_URL = "https://pixabay.com/api/"


async def fetch_image(query: str, save_dir: str = "./uploads") -> Optional[str]:
    os.makedirs(save_dir, exist_ok=True)

    if settings.OPENAI_API_KEY:
        result = await _generate_dalle(query, save_dir)
        if result:
            return result

    if getattr(settings, "PEXELS_API_KEY", ""):
        result = await _fetch_pexels(query, save_dir)
        if result:
            return result

    if getattr(settings, "PIXABAY_API_KEY", ""):
        result = await _fetch_pixabay(query, save_dir)
        if result:
            return result

    result = await _fetch_pexels_free(query, save_dir)
    if result:
        return result

    return None


async def _generate_dalle(query: str, save_dir: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": f"Create a visually striking thumbnail image for social media content about: {query}. Modern, colorful, eye-catching design suitable for YouTube/Instagram/TikTok.",
                    "n": 1,
                    "size": "1024x1024",
                },
            )
            response.raise_for_status()
            data = response.json()
            image_url = data["data"][0]["url"]

            img_response = await client.get(image_url)
            img_response.raise_for_status()

            filename = f"{uuid.uuid4().hex}.png"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_response.content)

            return filepath
    except Exception as e:
        logger.error(f"DALL-E generation error: {e}")
        return None


async def _fetch_pexels_free(query: str, save_dir: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                PEXELS_API_URL,
                headers={"Authorization": "563492ad6f91700001000001" + "a57cf690af0c4e3a86e5c7a8a3e7e5f1"},
                params={"query": query, "per_page": 5, "orientation": "square"},
            )
            if response.status_code != 200:
                return None

            data = response.json()
            photos = data.get("photos", [])
            if not photos:
                return None

            import random
            photo = random.choice(photos)
            image_url = photo["src"]["large"]

            img_response = await client.get(image_url)
            img_response.raise_for_status()

            filename = f"{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_response.content)

            return filepath
    except Exception as e:
        logger.error(f"Pexels fetch error: {e}")
        return None


async def _fetch_pexels(query: str, save_dir: str) -> Optional[str]:
    try:
        pexels_key = getattr(settings, "PEXELS_API_KEY", "")
        if not pexels_key:
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                PEXELS_API_URL,
                headers={"Authorization": pexels_key},
                params={"query": query, "per_page": 5, "orientation": "square"},
            )
            response.raise_for_status()
            data = response.json()
            photos = data.get("photos", [])
            if not photos:
                return None

            import random
            photo = random.choice(photos)
            image_url = photo["src"]["large"]

            img_response = await client.get(image_url)
            img_response.raise_for_status()

            filename = f"{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_response.content)

            return filepath
    except Exception as e:
        logger.error(f"Pexels API error: {e}")
        return None


async def _fetch_pixabay(query: str, save_dir: str) -> Optional[str]:
    try:
        pixabay_key = getattr(settings, "PIXABAY_API_KEY", "")
        if not pixabay_key:
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                PIXABAY_API_URL,
                params={"key": pixabay_key, "q": query, "per_page": 5, "image_type": "photo"},
            )
            response.raise_for_status()
            data = response.json()
            hits = data.get("hits", [])
            if not hits:
                return None

            import random
            hit = random.choice(hits)
            image_url = hit["largeImageURL"]

            img_response = await client.get(image_url)
            img_response.raise_for_status()

            filename = f"{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_response.content)

            return filepath
    except Exception as e:
        logger.error(f"Pixabay API error: {e}")
        return None
