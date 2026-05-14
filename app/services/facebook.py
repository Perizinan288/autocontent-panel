import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


async def publish_post(
    page_access_token: str,
    page_id: str,
    message: str,
    link: str = "",
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            data = {
                "message": message,
                "access_token": page_access_token,
            }
            if link:
                data["link"] = link

            response = await client.post(
                f"{GRAPH_API_URL}/{page_id}/feed",
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            return {
                "post_id": result.get("id"),
                "status": "published",
            }
    except Exception as e:
        logger.error(f"Facebook post error: {e}")
        return {"error": str(e)}


async def publish_photo(
    page_access_token: str,
    page_id: str,
    photo_url: str,
    caption: str = "",
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GRAPH_API_URL}/{page_id}/photos",
                data={
                    "url": photo_url,
                    "caption": caption,
                    "access_token": page_access_token,
                },
            )
            response.raise_for_status()
            result = response.json()
            return {
                "post_id": result.get("id"),
                "status": "published",
            }
    except Exception as e:
        logger.error(f"Facebook photo error: {e}")
        return {"error": str(e)}


async def publish_video(
    page_access_token: str,
    page_id: str,
    video_url: str = "",
    video_file_path: str = "",
    title: str = "",
    description: str = "",
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            if video_file_path:
                with open(video_file_path, "rb") as f:
                    response = await client.post(
                        f"{GRAPH_API_URL}/{page_id}/videos",
                        data={
                            "title": title,
                            "description": description,
                            "access_token": page_access_token,
                        },
                        files={"source": ("video.mp4", f, "video/mp4")},
                    )
            else:
                response = await client.post(
                    f"{GRAPH_API_URL}/{page_id}/videos",
                    data={
                        "file_url": video_url,
                        "title": title,
                        "description": description,
                        "access_token": page_access_token,
                    },
                )
            response.raise_for_status()
            result = response.json()
            return {
                "video_id": result.get("id"),
                "status": "published",
            }
    except Exception as e:
        logger.error(f"Facebook video error: {e}")
        return {"error": str(e)}


async def publish_reel(
    page_access_token: str,
    page_id: str,
    video_url: str,
    description: str = "",
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            init_response = await client.post(
                f"{GRAPH_API_URL}/{page_id}/video_reels",
                data={
                    "upload_phase": "start",
                    "access_token": page_access_token,
                },
            )
            init_response.raise_for_status()
            video_id = init_response.json().get("video_id")

            upload_response = await client.post(
                f"{GRAPH_API_URL}/{video_id}",
                data={
                    "upload_phase": "finish",
                    "video_state": "PUBLISHED",
                    "description": description,
                    "video_url": video_url,
                    "access_token": page_access_token,
                },
            )
            upload_response.raise_for_status()
            return {
                "video_id": video_id,
                "status": "published",
            }
    except Exception as e:
        logger.error(f"Facebook reel error: {e}")
        return {"error": str(e)}


async def get_page_info(page_access_token: str, page_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_URL}/{page_id}",
                params={
                    "fields": "id,name,fan_count,followers_count",
                    "access_token": page_access_token,
                },
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Facebook page info error: {e}")
        return {}
