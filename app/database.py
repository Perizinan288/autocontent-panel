import aiosqlite

DB_PATH = "autocontent.db"


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                caption TEXT DEFAULT '',
                hashtags TEXT DEFAULT '',
                script TEXT DEFAULT '',
                platform TEXT DEFAULT 'all',
                content_type TEXT DEFAULT 'video',
                status TEXT DEFAULT 'draft',
                file_path TEXT DEFAULT '',
                thumbnail_path TEXT DEFAULT '',
                scheduled_at TEXT DEFAULT '',
                published_at TEXT DEFAULT '',
                youtube_url TEXT DEFAULT '',
                instagram_url TEXT DEFAULT '',
                facebook_url TEXT DEFAULT '',
                tiktok_url TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                source_file TEXT NOT NULL,
                clip_file TEXT DEFAULT '',
                start_time REAL DEFAULT 0,
                end_time REAL DEFAULT 0,
                duration REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (content_id) REFERENCES contents(id)
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error_message TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (content_id) REFERENCES contents(id)
            );

            CREATE TABLE IF NOT EXISTS platform_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL UNIQUE,
                credentials TEXT DEFAULT '{}',
                is_connected INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS generation_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                niche TEXT DEFAULT '',
                prompt_template TEXT NOT NULL,
                platform TEXT DEFAULT 'all',
                content_type TEXT DEFAULT 'short',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS autopilot_settings (
                id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 0,
                niche TEXT DEFAULT '',
                platforms TEXT DEFAULT 'all',
                post_frequency INTEGER DEFAULT 1,
                post_time TEXT DEFAULT '09:00',
                language TEXT DEFAULT 'id',
                tone TEXT DEFAULT 'engaging',
                content_type TEXT DEFAULT 'short',
                auto_image INTEGER DEFAULT 1,
                auto_upload INTEGER DEFAULT 1,
                last_run TEXT DEFAULT NULL,
                total_generated INTEGER DEFAULT 0,
                total_posted INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS autopilot_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT DEFAULT 'info',
                message TEXT DEFAULT '',
                niche TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()
