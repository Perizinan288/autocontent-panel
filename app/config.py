from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AutoContent Panel"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite+aiosqlite:///./autocontent.db"
    SECRET_KEY: str = "change-me-in-production"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/auth/youtube/callback"

    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_BUSINESS_ACCOUNT_ID: str = ""

    FACEBOOK_PAGE_ACCESS_TOKEN: str = ""
    FACEBOOK_PAGE_ID: str = ""

    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = "http://localhost:8000/api/auth/tiktok/callback"

    UPLOAD_DIR: str = "./uploads"
    CLIPS_DIR: str = "./clips"
    MAX_UPLOAD_SIZE_MB: int = 500

    SCHEDULER_ENABLED: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
