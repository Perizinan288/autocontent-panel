import os

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.config import settings
from app.database import get_db
from app.models import ContentCreate, ContentUpdate

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("")
async def list_contents(
    status: str = "",
    platform: str = "",
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM contents WHERE 1=1"
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if platform:
        query += " AND (platform = ? OR platform = 'all')"
        params.append(platform)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    count_cursor = await db.execute("SELECT COUNT(*) FROM contents")
    total = (await count_cursor.fetchone())[0]

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{content_id}")
async def get_content(content_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    return dict(row)


@router.post("")
async def create_content(data: ContentCreate, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute(
        """INSERT INTO contents (title, description, caption, hashtags, script, platform, content_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (data.title, data.description, data.caption, data.hashtags, data.script, data.platform, data.content_type),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "message": "Content created"}


@router.put("/{content_id}")
async def update_content(content_id: int, data: ContentUpdate, db: aiosqlite.Connection = Depends(get_db)):
    updates = []
    params = []
    for field, value in data.model_dump(exclude_none=True).items():
        updates.append(f"{field} = ?")
        params.append(value)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = datetime('now')")
    params.append(content_id)

    await db.execute(
        f"UPDATE contents SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    await db.commit()
    return {"message": "Content updated"}


@router.delete("/{content_id}")
async def delete_content(content_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT file_path FROM contents WHERE id = ?", (content_id,))
    row = await cursor.fetchone()
    if row and row["file_path"] and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])

    await db.execute("DELETE FROM clips WHERE content_id = ?", (content_id,))
    await db.execute("DELETE FROM schedules WHERE content_id = ?", (content_id,))
    await db.execute("DELETE FROM contents WHERE id = ?", (content_id,))
    await db.commit()
    return {"message": "Content deleted"}


@router.post("/{content_id}/upload")
async def upload_file(content_id: int, file: UploadFile, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT id FROM contents WHERE id = ?", (content_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Content not found")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{content_id}_{file.filename}")

    with open(file_path, "wb") as f:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        f.write(content)

    await db.execute(
        "UPDATE contents SET file_path = ?, updated_at = datetime('now') WHERE id = ?",
        (file_path, content_id),
    )
    await db.commit()
    return {"message": "File uploaded", "file_path": file_path}


@router.get("/stats/summary")
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    total = (await (await db.execute("SELECT COUNT(*) FROM contents")).fetchone())[0]
    published = (await (await db.execute("SELECT COUNT(*) FROM contents WHERE status = 'published'")).fetchone())[0]
    draft = (await (await db.execute("SELECT COUNT(*) FROM contents WHERE status = 'draft'")).fetchone())[0]
    scheduled = (await (await db.execute("SELECT COUNT(*) FROM schedules WHERE status = 'pending'")).fetchone())[0]

    return {
        "total_contents": total,
        "published": published,
        "drafts": draft,
        "scheduled": scheduled,
    }
