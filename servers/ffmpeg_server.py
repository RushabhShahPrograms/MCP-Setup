import subprocess
import json
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("FFmpeg")


def _run(cmd: list[str], timeout: int = 180) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, f"'{cmd[0]}' not found. Install FFmpeg: https://ffmpeg.org/download.html"
    except subprocess.TimeoutExpired:
        return False, "Operation timed out."
    except Exception as e:
        return False, str(e)


@mcp.tool()
def get_media_info(file_path: str) -> str:
    """
    Get detailed information about a media file: codec, resolution, duration, bitrate, fps.
    Always call this first before any conversion or compression.
    Example: get_media_info("C:/Videos/clip.mp4")
    """
    if not Path(file_path).exists():
        return f"Error: File not found: {file_path}"

    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        file_path,
    ]
    ok, output = _run(cmd)
    if not ok:
        return f"Error: {output}"

    try:
        data  = json.loads(output)
        fmt   = data.get("format", {})
        streams = data.get("streams", [])

        duration = float(fmt.get("duration", 0))
        size_kb  = int(fmt.get("size", 0)) // 1024
        bitrate  = int(fmt.get("bit_rate", 0)) // 1000

        lines = [
            f"📁 {Path(file_path).name}",
            f"Duration : {duration:.1f}s  |  Size: {size_kb} KB  |  Bitrate: {bitrate} kbps",
        ]

        for s in streams:
            ctype = s.get("codec_type")
            codec = s.get("codec_name", "N/A")
            if ctype == "video":
                w, h      = s.get("width", "?"), s.get("height", "?")
                fps_raw   = s.get("r_frame_rate", "0/1")
                try:
                    n, d = map(int, fps_raw.split("/"))
                    fps  = f"{n/d:.2f}" if d else "N/A"
                except Exception:
                    fps = fps_raw
                lines.append(f"Video    : {codec}  |  {w}x{h}  |  {fps} fps")
            elif ctype == "audio":
                sr = s.get("sample_rate", "N/A")
                ch = s.get("channels", "N/A")
                lines.append(f"Audio    : {codec}  |  {sr} Hz  |  {ch} channels")

        return "\n".join(lines)
    except Exception as e:
        return f"Parse error: {e}\nRaw: {output[:400]}"


@mcp.tool()
def convert_media(
    input_path: str,
    output_path: str,
    video_codec: str = "copy",
    audio_codec: str = "copy",
) -> str:
    """
    Convert a media file to a different format.
    video_codec: 'copy' (no re-encode), 'libx264', 'libx265', 'libvpx-vp9'
    audio_codec: 'copy', 'aac', 'mp3', 'libopus'
    Example: convert_media("input.avi", "output.mp4")
    Example: convert_media("input.mp4", "output.webm", "libvpx-vp9", "libopus")
    """
    if not Path(input_path).exists():
        return f"Error: Input not found: {input_path}"

    cmd = ["ffmpeg", "-i", input_path, "-vcodec", video_codec, "-acodec", audio_codec, "-y", output_path]
    ok, output = _run(cmd)
    if ok and Path(output_path).exists():
        size = Path(output_path).stat().st_size // 1024
        return f"✅ Converted → {output_path} ({size} KB)"
    return f"Error: {output}"


@mcp.tool()
def extract_audio(
    video_path: str,
    output_path: str,
    audio_format: str = "mp3",
    bitrate: str = "192k",
) -> str:
    """
    Extract audio track from a video file.
    audio_format: 'mp3', 'aac', 'wav', 'flac', 'ogg'
    bitrate: '128k', '192k', '256k', '320k'
    Example: extract_audio("movie.mp4", "soundtrack.mp3")
    """
    if not Path(video_path).exists():
        return f"Error: Video not found: {video_path}"

    codec_map = {
        "mp3": "libmp3lame", "aac": "aac", "wav": "pcm_s16le",
        "flac": "flac", "ogg": "libvorbis",
    }
    codec = codec_map.get(audio_format.lower(), "libmp3lame")
    cmd   = ["ffmpeg", "-i", video_path, "-vn", "-acodec", codec, "-b:a", bitrate, "-y", output_path]
    ok, output = _run(cmd)
    if ok and Path(output_path).exists():
        size = Path(output_path).stat().st_size // 1024
        return f"✅ Audio extracted → {output_path} ({size} KB)"
    return f"Error: {output}"


@mcp.tool()
def compress_video(
    input_path: str,
    output_path: str,
    crf: int = 28,
    preset: str = "medium",
) -> str:
    """
    Compress a video using H.264 encoding.
    crf: quality level 0–51 (18=high quality, 28=balanced, 40=small file). Lower = better quality.
    preset: 'ultrafast', 'fast', 'medium', 'slow', 'veryslow'
    Example: compress_video("large.mp4", "small.mp4", crf=26)
    """
    if not Path(input_path).exists():
        return f"Error: Input not found: {input_path}"
    if not (0 <= crf <= 51):
        return "Error: crf must be between 0 and 51."

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vcodec", "libx264", "-crf", str(crf), "-preset", preset,
        "-acodec", "aac", "-b:a", "128k",
        "-y", output_path,
    ]
    ok, output = _run(cmd, timeout=600)
    if ok and Path(output_path).exists():
        orig   = Path(input_path).stat().st_size  // 1024
        compr  = Path(output_path).stat().st_size // 1024
        pct    = (1 - compr / orig) * 100 if orig else 0
        return f"✅ Compressed → {output_path}\n  {orig} KB → {compr} KB  ({pct:.1f}% reduction)"
    return f"Error: {output}"


@mcp.tool()
def trim_media(
    input_path: str,
    output_path: str,
    start_time: str,
    duration: str,
) -> str:
    """
    Trim a media file to keep a specific segment.
    start_time: position to start from, e.g. "00:01:30" or "90" (seconds)
    duration  : how long to keep, e.g.  "00:00:30" or "30" (seconds)
    Example: trim_media("video.mp4", "clip.mp4", "00:01:00", "00:00:30")
    """
    if not Path(input_path).exists():
        return f"Error: Input not found: {input_path}"

    cmd = [
        "ffmpeg", "-ss", start_time, "-i", input_path,
        "-t", duration, "-vcodec", "copy", "-acodec", "copy",
        "-y", output_path,
    ]
    ok, output = _run(cmd)
    if ok:
        return f"✅ Trimmed → {output_path}  (start: {start_time}, duration: {duration})"
    return f"Error: {output}"


@mcp.tool()
def merge_videos(file_paths: list[str], output_path: str) -> str:
    """
    Merge/concatenate multiple video files into one.
    Files should share the same codec and resolution for best results.
    Example: merge_videos(["part1.mp4", "part2.mp4", "part3.mp4"], "merged.mp4")
    """
    missing = [f for f in file_paths if not Path(f).exists()]
    if missing:
        return f"Error: Files not found: {missing}"
    if len(file_paths) < 2:
        return "Error: Provide at least 2 files to merge."

    list_file = Path(output_path).parent / "_concat_list.txt"
    try:
        with open(list_file, "w") as f:
            for fp in file_paths:
                f.write(f"file '{fp}'\n")

        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-y", output_path]
        ok, output = _run(cmd)
    finally:
        list_file.unlink(missing_ok=True)

    if ok and Path(output_path).exists():
        size = Path(output_path).stat().st_size // 1024
        return f"✅ Merged {len(file_paths)} files → {output_path} ({size} KB)"
    return f"Error: {output}"


if __name__ == "__main__":
    mcp.run(transport="stdio")