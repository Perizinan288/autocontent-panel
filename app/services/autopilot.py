import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import aiosqlite

from app.database import DB_PATH
from app.services.ai_generator import generate_content
from app.services.image_generator import fetch_image

logger = logging.getLogger(__name__)


async def get_autopilot_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM autopilot_settings WHERE id = 1")
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return {
        "id": 1,
        "is_active": 0,
        "niche": "",
        "platforms": "all",
        "post_frequency": 1,
        "post_time": "09:00",
        "language": "id",
        "tone": "engaging",
        "content_type": "short",
        "auto_image": 1,
        "auto_upload": 1,
        "last_run": None,
        "total_generated": 0,
        "total_posted": 0,
    }


async def save_autopilot_settings(data: dict) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id FROM autopilot_settings WHERE id = 1")
        exists = await cursor.fetchone()

        if exists:
            await db.execute(
                """UPDATE autopilot_settings SET
                    is_active = ?, niche = ?, platforms = ?,
                    post_frequency = ?, post_time = ?, language = ?,
                    tone = ?, content_type = ?, auto_image = ?, auto_upload = ?
                WHERE id = 1""",
                (
                    data.get("is_active", 0),
                    data.get("niche", ""),
                    data.get("platforms", "all"),
                    data.get("post_frequency", 1),
                    data.get("post_time", "09:00"),
                    data.get("language", "id"),
                    data.get("tone", "engaging"),
                    data.get("content_type", "short"),
                    data.get("auto_image", 1),
                    data.get("auto_upload", 1),
                ),
            )
        else:
            await db.execute(
                """INSERT INTO autopilot_settings
                    (id, is_active, niche, platforms, post_frequency, post_time,
                     language, tone, content_type, auto_image, auto_upload)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("is_active", 0),
                    data.get("niche", ""),
                    data.get("platforms", "all"),
                    data.get("post_frequency", 1),
                    data.get("post_time", "09:00"),
                    data.get("language", "id"),
                    data.get("tone", "engaging"),
                    data.get("content_type", "short"),
                    data.get("auto_image", 1),
                    data.get("auto_upload", 1),
                ),
            )
        await db.commit()

    return await get_autopilot_settings()


async def get_autopilot_log() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM autopilot_log ORDER BY created_at DESC LIMIT 50"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def run_autopilot_cycle() -> dict:
    settings = await get_autopilot_settings()

    if not settings.get("is_active"):
        return {"status": "inactive", "message": "Autopilot tidak aktif"}

    niche = settings.get("niche", "")
    if not niche:
        return {"status": "error", "message": "Niche belum diatur"}

    results = {"generated": 0, "images": 0, "uploaded": 0, "errors": []}

    try:
        count = settings.get("post_frequency", 1)
        contents = await generate_content(
            niche=niche,
            platform=settings.get("platforms", "all"),
            content_type=settings.get("content_type", "short"),
            language=settings.get("language", "id"),
            tone=settings.get("tone", "engaging"),
            count=count,
        )

        if not contents:
            results["errors"].append("Gagal generate konten")
            await _log_event("error", "Gagal generate konten", niche)
            return {"status": "error", "results": results}

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            for item in contents:
                title = item.get("title", f"Konten {niche}")
                description = item.get("description", "")
                caption = item.get("caption", "")
                hashtags = item.get("hashtags", "")
                script = item.get("script", "")

                image_path = ""
                if settings.get("auto_image", 1):
                    try:
                        img = await fetch_image(f"{niche} {title}")
                        if img:
                            image_path = img
                            results["images"] += 1
                    except Exception as e:
                        logger.error(f"Image fetch error: {e}")
                        results["errors"].append(f"Gagal ambil gambar: {str(e)}")

                cursor = await db.execute(
                    """INSERT INTO contents
                        (title, description, caption, hashtags, script, platform, content_type, status, file_path, thumbnail_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        title, description, caption, hashtags, script,
                        settings.get("platforms", "all"),
                        settings.get("content_type", "short"),
                        "draft",
                        image_path,
                        image_path,
                    ),
                )
                content_id = cursor.lastrowid
                results["generated"] += 1

                if settings.get("auto_upload", 1):
                    target_platforms = _get_target_platforms(settings.get("platforms", "all"))
                    for platform in target_platforms:
                        cred_cursor = await db.execute(
                            "SELECT credentials FROM platform_credentials WHERE platform = ? AND is_connected = 1",
                            (platform,),
                        )
                        cred_row = await cred_cursor.fetchone()
                        if cred_row:
                            try:
                                await _upload_to_platform(platform, content_id, dict(item), image_path, json.loads(cred_row["credentials"]))
                                results["uploaded"] += 1
                                await _log_event("uploaded", f"Uploaded ke {platform}: {title}", niche)
                            except Exception as e:
                                logger.error(f"Upload to {platform} failed: {e}")
                                results["errors"].append(f"Upload {platform} gagal: {str(e)}")

                await _log_event("generated", f"Generated: {title}", niche)

            await db.execute(
                "UPDATE autopilot_settings SET last_run = ?, total_generated = total_generated + ?, total_posted = total_posted + ? WHERE id = 1",
                (datetime.now().isoformat(), results["generated"], results["uploaded"]),
            )
            await db.commit()

    except Exception as e:
        logger.error(f"Autopilot cycle error: {e}")
        results["errors"].append(str(e))
        await _log_event("error", f"Error: {str(e)}", niche)

    return {"status": "ok", "results": results}


def _get_target_platforms(platforms_str: str) -> List[str]:
    if platforms_str == "all":
        return ["youtube", "instagram", "facebook", "tiktok"]
    return [p.strip() for p in platforms_str.split(",") if p.strip()]


async def _upload_to_platform(platform: str, content_id: int, content: dict, file_path: str, creds: dict):
    from app.services import facebook, instagram, tiktok, youtube

    caption = content.get("caption", "")
    hashtags = content.get("hashtags", "")
    full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption
    title = content.get("title", "")

    if platform == "youtube" and creds.get("access_token"):
        tags = [t.strip().lstrip("#") for t in hashtags.split("#") if t.strip()]
        await youtube.upload_video(
            access_token=creds["access_token"],
            file_path=file_path,
            title=title,
            description=f"{content.get('description', '')}\n\n{hashtags}",
            tags=tags,
        )
    elif platform == "instagram" and creds.get("access_token"):
        await instagram.publish_photo(
            access_token=creds["access_token"],
            ig_user_id=creds.get("ig_user_id", ""),
            image_url=file_path,
            caption=full_caption,
        )
    elif platform == "facebook" and creds.get("page_access_token"):
        await facebook.publish_post(
            page_access_token=creds["page_access_token"],
            page_id=creds.get("page_id", ""),
            message=full_caption,
        )
    elif platform == "tiktok" and creds.get("access_token"):
        await tiktok.upload_video(
            access_token=creds["access_token"],
            file_path=file_path,
            title=title,
            description=full_caption,
        )


async def _log_event(event_type: str, message: str, niche: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO autopilot_log (event_type, message, niche) VALUES (?, ?, ?)",
                (event_type, message, niche),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Log error: {e}")


async def check_and_run_autopilot():
    try:
        settings = await get_autopilot_settings()
        if not settings.get("is_active"):
            return

        post_time = settings.get("post_time", "09:00")
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        if current_time != post_time:
            return

        last_run = settings.get("last_run")
        if last_run:
            last_run_date = last_run[:10]
            today = now.strftime("%Y-%m-%d")
            if last_run_date == today:
                return

        logger.info("Running autopilot cycle...")
        result = await run_autopilot_cycle()
        logger.info(f"Autopilot result: {result}")
    except Exception as e:
        logger.error(f"Autopilot check error: {e}")
