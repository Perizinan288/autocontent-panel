import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PLATFORM_SPECS = {
    "youtube": {"max_title": 100, "max_desc": 5000, "hashtag_count": 15, "format": "YouTube Shorts / Video"},
    "instagram": {"max_title": 0, "max_desc": 2200, "hashtag_count": 30, "format": "Reels / Post"},
    "facebook": {"max_title": 0, "max_desc": 63206, "hashtag_count": 10, "format": "Reels / Post"},
    "all": {"max_title": 100, "max_desc": 2200, "hashtag_count": 10, "format": "Short-form Video"},
}


async def generate_content(
    niche: str,
    platform: str = "all",
    content_type: str = "short",
    language: str = "id",
    tone: str = "engaging",
    count: int = 1,
) -> list[dict]:
    if not settings.OPENAI_API_KEY:
        return _generate_fallback(niche, platform, content_type, language, count)

    specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["all"])
    lang_name = "Bahasa Indonesia" if language == "id" else "English"

    prompt = f"""Kamu adalah content creator profesional. Buatkan {count} ide konten untuk niche "{niche}".

Platform: {specs['format']}
Bahasa: {lang_name}
Tone: {tone}
Tipe konten: {content_type}

Untuk setiap konten, berikan dalam format JSON array:
[{{
    "title": "judul yang menarik (max {specs['max_title']} karakter)",
    "description": "deskripsi lengkap untuk SEO",
    "caption": "caption yang engaging untuk posting",
    "hashtags": "#{niche.replace(' ', '')} #fyp #viral (max {specs['hashtag_count']} hashtag)",
    "script": "script narasi lengkap untuk video (30-60 detik)",
    "hook": "kalimat pembuka yang bikin penonton stay",
    "cta": "call to action di akhir video"
}}]

Pastikan konten yang dihasilkan:
1. Viral-worthy dan engaging
2. Sesuai tren terkini
3. Mudah diproduksi
4. Punya hook yang kuat di 3 detik pertama
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": "Kamu adalah AI content creator profesional."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()
            content_text = data["choices"][0]["message"]["content"]

            start = content_text.find("[")
            end = content_text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(content_text[start:end])

            return json.loads(content_text)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return _generate_fallback(niche, platform, content_type, language, count)


def _generate_fallback(niche: str, platform: str, content_type: str, language: str, count: int) -> list[dict]:
    templates = [
        {
            "title": f"5 Fakta {niche} yang Jarang Orang Tahu!",
            "description": f"Temukan fakta-fakta menarik tentang {niche} yang belum banyak diketahui orang. Video ini akan membuka wawasan kamu!",
            "caption": f"Ternyata {niche} punya rahasia yang bikin kaget! 😱 Cek video lengkapnya!",
            "hashtags": f"#{niche.replace(' ', '')} #fakta #viral #fyp #trending #edukasi #info #faktaunik",
            "script": f"Tahukah kamu? Ada fakta tentang {niche} yang jarang diketahui orang. Nomor 3 pasti bikin kamu kaget! Pertama... Kedua... Ketiga... Keempat... Kelima... Jangan lupa follow untuk fakta menarik lainnya!",
            "hook": f"Stop scroll! Ini fakta {niche} yang belum kamu tahu!",
            "cta": "Follow untuk konten seru lainnya! 🔥",
        },
        {
            "title": f"Tutorial {niche} untuk Pemula - Panduan Lengkap",
            "description": f"Panduan lengkap {niche} untuk pemula. Dari dasar sampai mahir dalam satu video!",
            "caption": f"Mau belajar {niche}? Ini panduan lengkapnya! 📚",
            "hashtags": f"#{niche.replace(' ', '')} #tutorial #belajar #pemula #tips #trik #panduan",
            "script": f"Halo! Di video ini aku akan share tutorial {niche} dari nol. Pertama, kamu perlu... Setelah itu... Dan yang terakhir... Mudah kan? Coba sekarang!",
            "hook": f"3 menit aja bisa mahir {niche}!",
            "cta": "Save video ini biar nggak lupa! 💾",
        },
        {
            "title": f"Kesalahan Fatal dalam {niche} - Jangan Lakukan Ini!",
            "description": f"Hindari kesalahan-kesalahan ini saat melakukan {niche}. Banyak orang masih salah!",
            "caption": f"Kamu masih melakukan kesalahan ini di {niche}? 🚫 Stop sekarang!",
            "hashtags": f"#{niche.replace(' ', '')} #kesalahan #tips #warning #janganlakukan #viral",
            "script": f"Banyak orang masih salah tentang {niche}! Kesalahan pertama... Kedua... Dan yang paling fatal... Jangan sampai kamu melakukan hal yang sama ya!",
            "hook": f"90% orang masih salah tentang {niche}!",
            "cta": "Share ke teman kamu biar mereka nggak salah juga! 🔄",
        },
        {
            "title": f"Review Jujur: {niche} - Worth It atau Nggak?",
            "description": f"Review lengkap dan jujur tentang {niche}. Simak sebelum kamu memutuskan!",
            "caption": f"Review jujur {niche}! Worth it nggak sih? 🤔",
            "hashtags": f"#{niche.replace(' ', '')} #review #honest #worthit #rekomendasi #viral",
            "script": f"Banyak yang tanya soal {niche}, worth it nggak sih? Setelah aku coba sendiri... Kelebihannya... Kekurangannya... Overall, menurutku...",
            "hook": f"Jangan beli {niche} sebelum nonton ini!",
            "cta": "Comment pendapat kamu di bawah! 💬",
        },
        {
            "title": f"Tren {niche} 2024 yang Wajib Kamu Tahu",
            "description": f"Update tren terbaru seputar {niche}. Jangan sampai ketinggalan!",
            "caption": f"Tren {niche} terbaru! Kamu sudah tahu belum? 🔥",
            "hashtags": f"#{niche.replace(' ', '')} #tren #update #terbaru #trending #viral #fyp",
            "script": f"Ini dia tren {niche} yang lagi booming! Pertama... Kedua... Dan yang paling hits... Kamu sudah coba yang mana?",
            "hook": f"Tren {niche} ini lagi viral banget!",
            "cta": "Follow biar selalu update tren terbaru! ⚡",
        },
    ]
    return templates[:count]


async def generate_hashtags(niche: str, platform: str = "all", count: int = 15) -> list[str]:
    base_tags = [
        f"#{niche.replace(' ', '').lower()}",
        "#viral",
        "#fyp",
        "#trending",
        "#konten",
        "#kreator",
        "#indonesia",
        f"#{niche.replace(' ', '').lower()}indonesia",
        "#tips",
        "#edukasi",
        "#info",
        "#tutorial",
        "#review",
        "#rekomendasi",
        "#foryou",
    ]
    return base_tags[:count]


async def generate_caption(title: str, niche: str, platform: str = "all") -> str:
    return f"🔥 {title}\n\n💡 Konten seru tentang {niche}!\n\nJangan lupa Like, Comment, & Share ya! ❤️\n\n#{'#'.join([niche.replace(' ', ''), 'viral', 'fyp', 'trending'])}"
