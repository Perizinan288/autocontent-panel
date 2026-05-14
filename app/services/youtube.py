import json
import logging

import httpx

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"


async def get_auth_url(client_id: str, redirect_uri: str) -> str:
    scopes = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"
    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&redirect_uri={redirect_uri}"
        f"&response_type=code&scope={scopes}"
        f"&access_type=offline&prompt=consent"
    )


async def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        return response.json()


async def refresh_token(client_id: str, client_secret: str, refresh_token_str: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
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
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "public",
    is_short: bool = True,
) -> dict:
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if is_short:
        metadata["snippet"]["title"] = f"{title[:90]} #Shorts"

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            init_response = await client.post(
                f"{YOUTUBE_UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(metadata),
            )
            init_response.raise_for_status()

            upload_url = init_response.headers.get("Location")
            if not upload_url:
                return {"error": "Failed to get upload URL"}

            with open(file_path, "rb") as f:
                video_data = f.read()

            upload_response = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/*",
                },
                content=video_data,
            )
            upload_response.raise_for_status()
            result = upload_response.json()

            return {
                "video_id": result.get("id"),
                "url": f"https://youtube.com/watch?v={result.get('id')}",
                "status": "uploaded",
            }
    except Exception as e:
        logger.error(f"YouTube upload error: {e}")
        return {"error": str(e)}


async def get_channel_info(access_token: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_URL}/channels?part=snippet,statistics&mine=true",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("items"):
                channel = data["items"][0]
                return {
                    "id": channel["id"],
                    "title": channel["snippet"]["title"],
                    "subscribers": channel["statistics"].get("subscriberCount", "0"),
                    "videos": channel["statistics"].get("videoCount", "0"),
                }
    except Exception as e:
        logger.error(f"YouTube channel info error: {e}")
    return {}
