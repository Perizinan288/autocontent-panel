from pydantic import BaseModel


class ContentCreate(BaseModel):
    title: str
    description: str = ""
    caption: str = ""
    hashtags: str = ""
    script: str = ""
    platform: str = "all"
    content_type: str = "video"


class ContentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    caption: str | None = None
    hashtags: str | None = None
    script: str | None = None
    platform: str | None = None
    content_type: str | None = None
    status: str | None = None
    scheduled_at: str | None = None


class GenerateRequest(BaseModel):
    niche: str
    platform: str = "all"
    content_type: str = "short"
    language: str = "id"
    tone: str = "engaging"
    count: int = 1


class ClipRequest(BaseModel):
    source_file: str
    clips: list[dict] = []
    auto_detect: bool = False
    max_duration: float = 60.0
    min_duration: float = 15.0


class ScheduleCreate(BaseModel):
    content_id: int
    platform: str
    scheduled_at: str


class PlatformCredentials(BaseModel):
    platform: str
    credentials: dict


class TemplateCreate(BaseModel):
    name: str
    niche: str = ""
    prompt_template: str
    platform: str = "all"
    content_type: str = "short"
