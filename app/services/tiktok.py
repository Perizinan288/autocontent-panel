import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TIKTOK_API_URL = "https://open.tiktokapis.com/v2"


async def get_auth_url(client_key: str, redirect_uri: str) -> str:
    scopes = "user.info.basic,video.publish,video.upload"
    return (
        f"https://www.tiktok.com/v2/auth/authorize/?"
        f"client_key={client_key}&redirect_uri={redirect_uri}"
        f"&response_type=code&scope={scopes}"
    )


async def exchange_code(client_key: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TIKTOK_API_URL}/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        return response.json()


async def refresh_access_token(client_key: str, client_secret: str, refresh_token_str: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TIKTOK_API_URL}/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "refresh_token": refresh_token_str,
                "grant_type": "refresh_token",
            },
        )
        return response.json()


async def upload_video(
    access_token: str,
    file_path: str,
    title: str,
    description: str = "",
    privacy_level: str = "PUBLIC_TO_EVERYONE",
) -> dict:
    try:
        with open(file_path, "rb") as f:
            video_data = f.read()

        video_size = len(video_data)

        async with httpx.AsyncClient(timeout=600.0) as client:
            init_response = await client.post(
                f"{TIKTOK_API_URL}/post/publish/inbox/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": video_size,
                        "chunk_size": video_size,
                        "total_chunk_count": 1,
                    },
                },
            )
            init_data = init_response.json()

            if init_data.get("error", {}).get("code") != "ok":
                return {"error": init_data.get("error", {}).get("message", "Init failed")}

            upload_url = init_data.get("data", {}).get("upload_url")
            if not upload_url:
                return {"error": "Failed to get upload URL"}

            upload_response = await client.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
                    "Content-Type": "video/mp4",
                },
                content=video_data,
            )

            publish_id = init_data.get("data", {}).get("publish_id", "")

            return {
                "publish_id": publish_id,
                "status": "uploaded",
                "message": "Video uploaded to TikTok inbox",
            }
    except Exception as e:
        logger.error(f"TikTok upload error: {e}")
        return {"error": str(e)}


async def get_user_info(access_token: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TIKTOK_API_URL}/user/info/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "display_name,avatar_url,follower_count,video_count"},
            )
            data = response.json()
            user_data = data.get("data", {}).get("user", {})
            return {
                "display_name": user_data.get("display_name", ""),
                "avatar_url": user_data.get("avatar_url", ""),
                "followers": user_data.get("follower_count", 0),
                "videos": user_data.get("video_count", 0),
            }
    except Exception as e:
        logger.error(f"TikTok user info error: {e}")
    return {}
