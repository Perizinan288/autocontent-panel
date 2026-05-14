import json
import logging
import os
import subprocess
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


def ensure_dirs():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CLIPS_DIR, exist_ok=True)


def get_video_info(file_path: str) -> dict:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        streams = data.get("streams", [])

        video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0

        return {
            "duration": duration,
            "width": width,
            "height": height,
            "size_mb": os.path.getsize(file_path) / (1024 * 1024),
            "format": data.get("format", {}).get("format_name", "unknown"),
        }
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {"duration": 0, "width": 0, "height": 0, "size_mb": 0, "format": "unknown"}


def create_clip(
    source_file: str,
    start_time: float,
    end_time: float,
    output_name: str | None = None,
    vertical: bool = True,
) -> str:
    ensure_dirs()

    if not output_name:
        output_name = f"clip_{uuid.uuid4().hex[:8]}.mp4"

    output_path = os.path.join(settings.CLIPS_DIR, output_name)

    filters = []
    if vertical:
        filters.append("crop=ih*9/16:ih:(iw-ih*9/16)/2:0")
        filters.append("scale=1080:1920")

    filter_str = ",".join(filters) if filters else None

    cmd = [
        "ffmpeg",
        "-y",
        "-i", source_file,
        "-ss", str(start_time),
        "-to", str(end_time),
    ]

    if filter_str:
        cmd.extend(["-vf", filter_str])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return output_path
    except Exception as e:
        logger.error(f"Error creating clip: {e}")
        return ""


def auto_clip_video(
    source_file: str,
    max_duration: float = 60.0,
    min_duration: float = 15.0,
    overlap: float = 2.0,
) -> list[dict]:
    ensure_dirs()
    info = get_video_info(source_file)
    total_duration = info["duration"]

    if total_duration <= 0:
        return []

    clips = []
    current_time = 0.0
    clip_index = 0

    while current_time < total_duration:
        end_time = min(current_time + max_duration, total_duration)

        if end_time - current_time < min_duration and clip_index > 0:
            break

        output_name = f"clip_{uuid.uuid4().hex[:8]}_{clip_index:03d}.mp4"
        output_path = create_clip(source_file, current_time, end_time, output_name)

        if output_path:
            clips.append({
                "index": clip_index,
                "start_time": current_time,
                "end_time": end_time,
                "duration": end_time - current_time,
                "file_path": output_path,
                "file_name": output_name,
            })

        current_time = end_time - overlap
        clip_index += 1

    return clips


def add_text_overlay(
    input_file: str,
    text: str,
    position: str = "bottom",
    font_size: int = 42,
    output_name: str | None = None,
) -> str:
    ensure_dirs()

    if not output_name:
        output_name = f"overlay_{uuid.uuid4().hex[:8]}.mp4"

    output_path = os.path.join(settings.CLIPS_DIR, output_name)

    y_pos = {
        "top": "50",
        "center": "(h-text_h)/2",
        "bottom": "h-text_h-80",
    }.get(position, "h-text_h-80")

    escaped_text = text.replace("'", "\\'").replace(":", "\\:")

    filter_str = (
        f"drawtext=text='{escaped_text}'"
        f":fontsize={font_size}"
        f":fontcolor=white"
        f":borderw=3"
        f":bordercolor=black"
        f":x=(w-text_w)/2"
        f":y={y_pos}"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return output_path
    except Exception as e:
        logger.error(f"Error adding text overlay: {e}")
        return ""


def generate_thumbnail(video_file: str, timestamp: float = 1.0, output_name: str | None = None) -> str:
    ensure_dirs()

    if not output_name:
        output_name = f"thumb_{uuid.uuid4().hex[:8]}.jpg"

    output_path = os.path.join(settings.CLIPS_DIR, output_name)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_file,
        "-ss", str(timestamp),
        "-vframes", "1",
        "-q:v", "2",
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return output_path
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return ""
