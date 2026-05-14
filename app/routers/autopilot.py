from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter

from app.services.autopilot import (
    get_autopilot_log,
    get_autopilot_settings,
    run_autopilot_cycle,
    save_autopilot_settings,
)

router = APIRouter(prefix="/api/autopilot", tags=["autopilot"])


class AutopilotSettingsUpdate(BaseModel):
    is_active: Optional[int] = None
    niche: Optional[str] = None
    platforms: Optional[str] = None
    post_frequency: Optional[int] = None
    post_time: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    content_type: Optional[str] = None
    auto_image: Optional[int] = None
    auto_upload: Optional[int] = None


@router.get("/settings")
async def get_settings():
    return await get_autopilot_settings()


@router.post("/settings")
async def update_settings(data: AutopilotSettingsUpdate):
    current = await get_autopilot_settings()
    update_data = {}
    for field in [
        "is_active", "niche", "platforms", "post_frequency", "post_time",
        "language", "tone", "content_type", "auto_image", "auto_upload",
    ]:
        val = getattr(data, field, None)
        if val is not None:
            update_data[field] = val
        else:
            update_data[field] = current.get(field)

    return await save_autopilot_settings(update_data)


@router.post("/run")
async def trigger_run():
    result = await run_autopilot_cycle()
    return result


@router.get("/log")
async def get_log():
    logs = await get_autopilot_log()
    return {"items": logs}
