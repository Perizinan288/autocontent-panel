import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import ScheduleCreate

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("")
async def list_schedules(status: str = "", db: aiosqlite.Connection = Depends(get_db)):
    query = """
        SELECT s.*, c.title as content_title, c.platform as content_platform
        FROM schedules s
        JOIN contents c ON s.content_id = c.id
    """
    params: list = []

    if status:
        query += " WHERE s.status = ?"
        params.append(status)

    query += " ORDER BY s.scheduled_at ASC"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return {"items": [dict(row) for row in rows]}


@router.post("")
async def create_schedule(data: ScheduleCreate, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT id FROM contents WHERE id = ?", (data.content_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Content not found")

    cursor = await db.execute(
        "INSERT INTO schedules (content_id, platform, scheduled_at) VALUES (?, ?, ?)",
        (data.content_id, data.platform, data.scheduled_at),
    )
    await db.commit()

    await db.execute(
        "UPDATE contents SET status = 'scheduled', scheduled_at = ? WHERE id = ?",
        (data.scheduled_at, data.content_id),
    )
    await db.commit()

    return {"id": cursor.lastrowid, "message": "Schedule created"}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    await db.commit()
    return {"message": "Schedule deleted"}


@router.post("/{schedule_id}/cancel")
async def cancel_schedule(schedule_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute(
        "UPDATE schedules SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
        (schedule_id,),
    )
    await db.commit()
    return {"message": "Schedule cancelled"}
