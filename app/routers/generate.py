import aiosqlite
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import GenerateRequest, TemplateCreate
from app.services.ai_generator import generate_caption, generate_content, generate_hashtags

router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("/content")
async def generate_content_ideas(data: GenerateRequest, db: aiosqlite.Connection = Depends(get_db)):
    results = await generate_content(
        niche=data.niche,
        platform=data.platform,
        content_type=data.content_type,
        language=data.language,
        tone=data.tone,
        count=data.count,
    )
    return {"items": results, "count": len(results)}


@router.post("/content/save")
async def generate_and_save(data: GenerateRequest, db: aiosqlite.Connection = Depends(get_db)):
    results = await generate_content(
        niche=data.niche,
        platform=data.platform,
        content_type=data.content_type,
        language=data.language,
        tone=data.tone,
        count=data.count,
    )

    saved_ids = []
    for item in results:
        cursor = await db.execute(
            """INSERT INTO contents (title, description, caption, hashtags, script, platform, content_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                item.get("title", ""),
                item.get("description", ""),
                item.get("caption", ""),
                item.get("hashtags", ""),
                item.get("script", ""),
                data.platform,
                data.content_type,
            ),
        )
        saved_ids.append(cursor.lastrowid)

    await db.commit()
    return {"saved_ids": saved_ids, "items": results}


@router.post("/hashtags")
async def generate_hashtags_api(niche: str, platform: str = "all", count: int = 15):
    tags = await generate_hashtags(niche, platform, count)
    return {"hashtags": tags}


@router.post("/caption")
async def generate_caption_api(title: str, niche: str, platform: str = "all"):
    caption = await generate_caption(title, niche, platform)
    return {"caption": caption}


@router.get("/templates")
async def list_templates(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM generation_templates ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return {"items": [dict(row) for row in rows]}


@router.post("/templates")
async def create_template(data: TemplateCreate, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute(
        "INSERT INTO generation_templates (name, niche, prompt_template, platform, content_type) VALUES (?, ?, ?, ?, ?)",
        (data.name, data.niche, data.prompt_template, data.platform, data.content_type),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "message": "Template created"}


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM generation_templates WHERE id = ?", (template_id,))
    await db.commit()
    return {"message": "Template deleted"}
