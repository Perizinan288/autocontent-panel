# AutoContent Panel - imgbb.vip

Panel otomasi pembuatan dan upload konten untuk **YouTube**, **Instagram**, dan **Facebook**.

## Fitur

- **AI Content Generator** - Generate ide konten, caption, hashtags, dan script video otomatis
- **Video Clipper** - Potong video panjang menjadi clips pendek (Shorts/Reels) otomatis
- **Multi-Platform Upload** - Upload ke YouTube, Instagram, dan Facebook sekaligus
- **Auto Scheduler** - Jadwalkan posting otomatis
- **Template System** - Simpan template konten untuk reuse
- **Dashboard** - Monitor semua konten dan status upload

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: HTML/CSS/JS (Dark Mode Dashboard)
- **Database**: SQLite
- **Video Processing**: FFmpeg
- **AI**: OpenAI API (opsional, ada fallback template)
- **Scheduler**: APScheduler

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Konfigurasi (Opsional)

Buat file `.env`:

```env
OPENAI_API_KEY=sk-xxx                    # Untuk AI content generation
YOUTUBE_CLIENT_ID=xxx                     # Google API Console
YOUTUBE_CLIENT_SECRET=xxx                 # Google API Console
INSTAGRAM_ACCESS_TOKEN=xxx                # Instagram Graph API
INSTAGRAM_BUSINESS_ACCOUNT_ID=xxx         # Instagram Business Account
FACEBOOK_PAGE_ACCESS_TOKEN=xxx            # Facebook Page Token
FACEBOOK_PAGE_ID=xxx                      # Facebook Page ID
```

### 3. Jalankan

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Buka `http://localhost:8000`

## API Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/content` | GET/POST | CRUD konten |
| `/api/generate/content` | POST | Generate ide konten AI |
| `/api/generate/content/save` | POST | Generate & simpan konten |
| `/api/clips/upload` | POST | Upload video sumber |
| `/api/clips/auto` | POST | Auto-clip video |
| `/api/upload/youtube/{id}` | POST | Upload ke YouTube |
| `/api/upload/instagram/{id}` | POST | Upload ke Instagram |
| `/api/upload/facebook/{id}` | POST | Upload ke Facebook |
| `/api/upload/all/{id}` | POST | Upload ke semua platform |
| `/api/schedules` | GET/POST | Kelola jadwal posting |

## Cara Kerja

1. **Generate** - Masukkan niche/topik, AI akan buatkan ide konten lengkap
2. **Edit** - Review dan edit konten sesuai keinginan
3. **Upload Video** - Upload video atau gunakan clipper untuk potong video
4. **Publish** - Upload langsung atau jadwalkan posting otomatis
5. **Monitor** - Pantau status semua konten di dashboard

## Platform Setup

### YouTube
1. Buat project di [Google Cloud Console](https://console.cloud.google.com)
2. Enable YouTube Data API v3
3. Buat OAuth 2.0 credentials
4. Masukkan Client ID & Secret di panel

### Instagram
1. Buat Facebook App di [Meta Developer](https://developers.facebook.com)
2. Setup Instagram Graph API
3. Generate long-lived access token
4. Masukkan token & Business Account ID di panel

### Facebook
1. Buat Facebook App
2. Generate Page Access Token
3. Masukkan token & Page ID di panel

## License

MIT
