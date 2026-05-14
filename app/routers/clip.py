import os

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.config import settings
from app.database import get_db
from app.models import ClipRequest
from app.services.video_clipper import (
    add_text_overlay,
    auto_clip_video,
    create_clip,
    generate_thumbnail,
    get_video_info,
)

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("/upload")
async def upload_source_video(file: UploadFile):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        f.write(content)

    info = get_video_info(file_path)
    return {
        "file_path": file_path,
        "file_name": file.filename,
        "info": info,
    }


@router.post("/auto")
async def auto_clip(data: ClipRequest, db: aiosqlite.Connection = Depends(get_db)):
    if not os.path.exists(data.source_file):
        raise HTTPException(status_code=404, detail="Source file not found")

    clips = auto_clip_video(
        source_file=data.source_file,
        max_duration=data.max_duration,
        min_duration=data.min_duration,
    )

    for clip in clips:
        await db.execute(
            """INSERT INTO clips (source_file, clip_file, start_time, end_time, duration, status)
               VALUES (?, ?, ?, ?, ?, 'completed')""",
            (data.source_file, clip["file_path"], clip["start_time"], clip["end_time"], clip["duration"]),
        )
    await db.commit()

    return {"clips": clips, "total": len(clips)}


@router.post("/manual")
async def manual_clip(
    source_file: str,
    start_time: float,
    end_time: float,
    vertical: bool = True,
    db: aiosqlite.Connection = Depends(get_db),
):
    if not os.path.exists(source_file):
        raise HTTPException(status_code=404, detail="Source file not found")

    output_path = create_clip(source_file, start_time, end_time, vertical=vertical)
    if not output_path:
        raise HTTPException(status_code=500, detail="Failed to create clip")

    await db.execute(
        """INSERT INTO clips (source_file, clip_file, start_time, end_time, duration, status)
           VALUES (?, ?, ?, ?, ?, 'completed')""",
        (source_file, output_path, start_time, end_time, end_time - start_time),
    )
    await db.commit()

    return {"clip_path": output_path, "duration": end_time - start_time}


@router.post("/overlay")
async def add_overlay(
    input_file: str,
    text: str,
    position: str = "bottom",
    font_size: int = 42,
):
    if not os.path.exists(input_file):
        raise HTTPException(status_code=404, detail="Input file not found")

    output_path = add_text_overlay(input_file, text, position, font_size)
    if not output_path:
        raise HTTPException(status_code=500, detail="Failed to add overlay")

    return {"output_path": output_path}


@router.post("/thumbnail")
async def create_thumbnail(video_file: str, timestamp: float = 1.0):
    if not os.path.exists(video_file):
        raise HTTPException(status_code=404, detail="Video file not found")

    output_path = generate_thumbnail(video_file, timestamp)
    if not output_path:
        raise HTTPException(status_code=500, detail="Failed to generate thumbnail")

    return {"thumbnail_path": output_path}


@router.get("/info")
async def video_info(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return get_video_info(file_path)


@router.get("")
async def list_clips(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM clips ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return {"items": [dict(row) for row in rows]}
