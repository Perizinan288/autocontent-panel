import json
import logging
from datetime import datetime

import aiosqlite

from app.database import DB_PATH
from app.services import facebook, instagram, tiktok, youtube

logger = logging.getLogger(__name__)


async def get_platform_credentials(platform: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT credentials FROM platform_credentials WHERE platform = ? AND is_connected = 1",
            (platform,),
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["credentials"])
    return {}


async def process_scheduled_upload(schedule_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT s.*, c.title, c.description, c.caption, c.hashtags, c.file_path, c.content_type
               FROM schedules s
               JOIN contents c ON s.content_id = c.id
               WHERE s.id = ?""",
            (schedule_id,),
        )
        schedule = await cursor.fetchone()

        if not schedule:
            return

        platform = schedule["platform"]
        creds = await get_platform_credentials(platform)

        if not creds:
            await db.execute(
                "UPDATE schedules SET status = 'failed', error_message = 'No credentials configured' WHERE id = ?",
                (schedule_id,),
            )
            await db.commit()
            return

        result = {}
        full_caption = f"{schedule['caption']}\n\n{schedule['hashtags']}" if schedule['hashtags'] else schedule['caption']

        try:
            if platform == "youtube":
                access_token = creds.get("access_token", "")
                tags = [t.strip().lstrip("#") for t in schedule["hashtags"].split("#") if t.strip()]
                result = await youtube.upload_video(
                    access_token=access_token,
                    file_path=schedule["file_path"],
                    title=schedule["title"],
                    description=f"{schedule['description']}\n\n{schedule['hashtags']}",
                    tags=tags,
                )
            elif platform == "instagram":
                access_token = creds.get("access_token", "")
                ig_user_id = creds.get("ig_user_id", "")
                if schedule["content_type"] == "video":
                    result = await instagram.publish_reel(
                        access_token=access_token,
                        ig_user_id=ig_user_id,
                        video_url=schedule["file_path"],
                        caption=full_caption,
                    )
                else:
                    result = await instagram.publish_photo(
                        access_token=access_token,
                        ig_user_id=ig_user_id,
                        image_url=schedule["file_path"],
                        caption=full_caption,
                    )
            elif platform == "facebook":
                page_token = creds.get("page_access_token", "")
                page_id = creds.get("page_id", "")
                if schedule["content_type"] == "video":
                    result = await facebook.publish_video(
                        page_access_token=page_token,
                        page_id=page_id,
                        video_file_path=schedule["file_path"],
                        title=schedule["title"],
                        description=full_caption,
                    )
                else:
                    result = await facebook.publish_post(
                        page_access_token=page_token,
                        page_id=page_id,
                        message=full_caption,
                    )
            elif platform == "tiktok":
                access_token = creds.get("access_token", "")
                result = await tiktok.upload_video(
                    access_token=access_token,
                    file_path=schedule["file_path"],
                    title=schedule["title"],
                    description=full_caption,
                )

            if result.get("error"):
                await db.execute(
                    "UPDATE schedules SET status = 'failed', error_message = ? WHERE id = ?",
                    (result["error"], schedule_id),
                )
            else:
                await db.execute(
                    "UPDATE schedules SET status = 'completed' WHERE id = ?",
                    (schedule_id,),
                )
                url_field = f"{platform}_url"
                url_value = result.get("url", result.get("post_id", result.get("media_id", "")))
                await db.execute(
                    f"UPDATE contents SET {url_field} = ?, published_at = ? WHERE id = ?",
                    (str(url_value), datetime.now().isoformat(), schedule["content_id"]),
                )
            await db.commit()

        except Exception as e:
            logger.error(f"Scheduled upload failed: {e}")
            await db.execute(
                "UPDATE schedules SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), schedule_id),
            )
            await db.commit()


async def check_and_run_schedules():
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id FROM schedules WHERE status = 'pending' AND scheduled_at <= ?",
            (now,),
        )
        rows = await cursor.fetchall()

        for row in rows:
            await process_scheduled_upload(row["id"])
