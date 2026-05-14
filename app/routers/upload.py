import json

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.database import get_db
from app.models import PlatformCredentials
from app.services import facebook, instagram, youtube

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/youtube/{content_id}")
async def upload_to_youtube(content_id: int, privacy: str = "public", db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    content = await cursor.fetchone()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    cred_cursor = await db.execute(
        "SELECT credentials FROM platform_credentials WHERE platform = 'youtube' AND is_connected = 1"
    )
    cred_row = await cred_cursor.fetchone()
    if not cred_row:
        raise HTTPException(status_code=400, detail="YouTube not connected")

    creds = json.loads(cred_row["credentials"])
    tags = [t.strip().lstrip("#") for t in content["hashtags"].split("#") if t.strip()]

    result = await youtube.upload_video(
        access_token=creds["access_token"],
        file_path=content["file_path"],
        title=content["title"],
        description=f"{content['description']}\n\n{content['hashtags']}",
        tags=tags,
        privacy_status=privacy,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    await db.execute(
        "UPDATE contents SET youtube_url = ?, status = 'published', published_at = datetime('now') WHERE id = ?",
        (result.get("url", ""), content_id),
    )
    await db.commit()
    return result


@router.post("/instagram/{content_id}")
async def upload_to_instagram(content_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    content = await cursor.fetchone()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    cred_cursor = await db.execute(
        "SELECT credentials FROM platform_credentials WHERE platform = 'instagram' AND is_connected = 1"
    )
    cred_row = await cred_cursor.fetchone()
    if not cred_row:
        raise HTTPException(status_code=400, detail="Instagram not connected")

    creds = json.loads(cred_row["credentials"])
    full_caption = f"{content['caption']}\n\n{content['hashtags']}" if content['hashtags'] else content['caption']

    if content["content_type"] == "video":
        result = await instagram.publish_reel(
            access_token=creds["access_token"],
            ig_user_id=creds["ig_user_id"],
            video_url=content["file_path"],
            caption=full_caption,
        )
    else:
        result = await instagram.publish_photo(
            access_token=creds["access_token"],
            ig_user_id=creds["ig_user_id"],
            image_url=content["file_path"],
            caption=full_caption,
        )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    await db.execute(
        "UPDATE contents SET instagram_url = ?, status = 'published', published_at = datetime('now') WHERE id = ?",
        (str(result.get("media_id", "")), content_id),
    )
    await db.commit()
    return result


@router.post("/facebook/{content_id}")
async def upload_to_facebook(content_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    content = await cursor.fetchone()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    cred_cursor = await db.execute(
        "SELECT credentials FROM platform_credentials WHERE platform = 'facebook' AND is_connected = 1"
    )
    cred_row = await cred_cursor.fetchone()
    if not cred_row:
        raise HTTPException(status_code=400, detail="Facebook not connected")

    creds = json.loads(cred_row["credentials"])
    full_caption = f"{content['caption']}\n\n{content['hashtags']}" if content['hashtags'] else content['caption']

    if content["content_type"] == "video":
        result = await facebook.publish_video(
            page_access_token=creds["page_access_token"],
            page_id=creds["page_id"],
            video_file_path=content["file_path"],
            title=content["title"],
            description=full_caption,
        )
    else:
        result = await facebook.publish_post(
            page_access_token=creds["page_access_token"],
            page_id=creds["page_id"],
            message=full_caption,
        )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    await db.execute(
        "UPDATE contents SET facebook_url = ?, status = 'published', published_at = datetime('now') WHERE id = ?",
        (str(result.get("post_id", result.get("video_id", ""))), content_id),
    )
    await db.commit()
    return result


@router.post("/all/{content_id}")
async def upload_to_all(content_id: int, db: aiosqlite.Connection = Depends(get_db)):
    results = {}
    errors = []

    try:
        results["youtube"] = await upload_to_youtube(content_id, db=db)
    except HTTPException as e:
        errors.append({"platform": "youtube", "error": e.detail})

    try:
        results["instagram"] = await upload_to_instagram(content_id, db=db)
    except HTTPException as e:
        errors.append({"platform": "instagram", "error": e.detail})

    try:
        results["facebook"] = await upload_to_facebook(content_id, db=db)
    except HTTPException as e:
        errors.append({"platform": "facebook", "error": e.detail})

    return {"results": results, "errors": errors}


@router.get("/platforms")
async def list_platforms(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT platform, is_connected, updated_at FROM platform_credentials")
    rows = await cursor.fetchall()
    platforms = {row["platform"]: {"connected": bool(row["is_connected"]), "updated_at": row["updated_at"]} for row in rows}

    for p in ["youtube", "instagram", "facebook"]:
        if p not in platforms:
            platforms[p] = {"connected": False, "updated_at": None}

    return platforms


@router.post("/platforms/connect")
async def connect_platform(data: PlatformCredentials, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute(
        """INSERT INTO platform_credentials (platform, credentials, is_connected, updated_at)
           VALUES (?, ?, 1, datetime('now'))
           ON CONFLICT(platform) DO UPDATE SET credentials = ?, is_connected = 1, updated_at = datetime('now')""",
        (data.platform, json.dumps(data.credentials), json.dumps(data.credentials)),
    )
    await db.commit()
    return {"message": f"{data.platform} connected"}


@router.post("/platforms/disconnect/{platform}")
async def disconnect_platform(platform: str, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute(
        "UPDATE platform_credentials SET is_connected = 0, updated_at = datetime('now') WHERE platform = ?",
        (platform,),
    )
    await db.commit()
    return {"message": f"{platform} disconnected"}


@router.get("/auth/youtube")
async def youtube_auth_url():
    if not settings.YOUTUBE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="YouTube Client ID not configured")
    url = await youtube.get_auth_url(settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_REDIRECT_URI)
    return {"auth_url": url}


@router.get("/auth/youtube/callback")
async def youtube_auth_callback(code: str, db: aiosqlite.Connection = Depends(get_db)):
    tokens = await youtube.exchange_code(
        settings.YOUTUBE_CLIENT_ID,
        settings.YOUTUBE_CLIENT_SECRET,
        code,
        settings.YOUTUBE_REDIRECT_URI,
    )
    if "error" in tokens:
        raise HTTPException(status_code=400, detail=tokens["error_description"])

    channel_info = await youtube.get_channel_info(tokens["access_token"])

    creds = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "channel_id": channel_info.get("id", ""),
        "channel_title": channel_info.get("title", ""),
    }

    await db.execute(
        """INSERT INTO platform_credentials (platform, credentials, is_connected, updated_at)
           VALUES ('youtube', ?, 1, datetime('now'))
           ON CONFLICT(platform) DO UPDATE SET credentials = ?, is_connected = 1, updated_at = datetime('now')""",
        (json.dumps(creds), json.dumps(creds)),
    )
    await db.commit()

    return {"message": "YouTube connected", "channel": channel_info}
