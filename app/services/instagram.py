import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


async def publish_photo(
    access_token: str,
    ig_user_id: str,
    image_url: str,
    caption: str = "",
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            create_response = await client.post(
                f"{GRAPH_API_URL}/{ig_user_id}/media",
                data={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": access_token,
                },
            )
            create_response.raise_for_status()
            creation_id = create_response.json().get("id")

            publish_response = await client.post(
                f"{GRAPH_API_URL}/{ig_user_id}/media_publish",
                data={
                    "creation_id": creation_id,
                    "access_token": access_token,
                },
            )
            publish_response.raise_for_status()
            result = publish_response.json()
            return {
                "media_id": result.get("id"),
                "status": "published",
            }
    except Exception as e:
        logger.error(f"Instagram photo publish error: {e}")
        return {"error": str(e)}


async def publish_reel(
    access_token: str,
    ig_user_id: str,
    video_url: str,
    caption: str = "",
    share_to_feed: bool = True,
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            create_response = await client.post(
                f"{GRAPH_API_URL}/{ig_user_id}/media",
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "share_to_feed": str(share_to_feed).lower(),
                    "access_token": access_token,
                },
            )
            create_response.raise_for_status()
            creation_id = create_response.json().get("id")

            import asyncio
            for _ in range(30):
                status_response = await client.get(
                    f"{GRAPH_API_URL}/{creation_id}",
                    params={
                        "fields": "status_code",
                        "access_token": access_token,
                    },
                )
                status_data = status_response.json()
                if status_data.get("status_code") == "FINISHED":
                    break
                await asyncio.sleep(10)

            publish_response = await client.post(
                f"{GRAPH_API_URL}/{ig_user_id}/media_publish",
                data={
                    "creation_id": creation_id,
                    "access_token": access_token,
                },
            )
            publish_response.raise_for_status()
            result = publish_response.json()
            return {
                "media_id": result.get("id"),
                "status": "published",
            }
    except Exception as e:
        logger.error(f"Instagram reel publish error: {e}")
        return {"error": str(e)}


async def get_account_info(access_token: str, ig_user_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_URL}/{ig_user_id}",
                params={
                    "fields": "id,username,name,followers_count,media_count",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Instagram account info error: {e}")
        return {}
