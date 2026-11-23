"""FFmpeg composition for the optional Minute Dose end card."""
from __future__ import annotations

import json
import math
import subprocess
import tempfile
from pathlib import Path

from . import config
from .media import NO_WINDOW

DURATION = 2.7
LOGO = Path(__file__).resolve().parents[1] / "web" / "brand" / "minute-dose-logo.jpg"
SOUND = Path(__file__).resolve().parents[1] / "web" / "brand" / "minute-dose-reveal.wav"


def probe(path: Path) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                        "-of", "json", str(path)], capture_output=True, text=True, timeout=30,
                       creationflags=NO_WINDOW)
    if p.returncode:
        raise RuntimeError(f"Could not inspect video: {p.stderr[-600:]}")
    data = json.loads(p.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError("The rendered clip has no video stream.")
    duration = float((data.get("format") or {}).get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Could not read the rendered clip duration.")
    return {"width": int(video["width"]), "height": int(video["height"]), "duration": duration,
            "audio": any(s.get("codec_type") == "audio" for s in data.get("streams", []))}


def _command(video: Path, output: Path, duration: float, sound: bool, animated: bool = True) -> None:
    if not LOGO.is_file():
        raise FileNotFoundError(f"Minute Dose logo is missing: {LOGO}")
    info = probe(video)
    w, h, content = info["width"], info["height"], info["duration"]
    outro = max(2.5, min(4.0, float(duration)))
    if sound and not SOUND.is_file():
        raise FileNotFoundError(f"Minute Dose reveal sound is missing: {SOUND}")
    size = max(2, int(min(w * 0.72, h * 0.36)) // 2 * 2)
    reveal = 0.55 if animated else 0.01
    fade_start = max(0, outro - 0.25)
    graph = (f"[0:v]setpts=PTS-STARTPTS,format=yuv420p[v0];"
             f"color=c=black:s={w}x{h}:r={config.OUT_FPS}:d={outro},format=rgba[bg];"
             f"[1:v]scale={size}:{size}:force_original_aspect_ratio=decrease,format=rgba,"
             f"fade=t=in:st=0.25:d={reveal}:alpha=1,fade=t=out:st={fade_start:.3f}:d=0.25:alpha=1[logo];"
             f"[logo]split[main][blur];[blur]gblur=sigma=24,colorchannelmixer=aa=0.28[glow];"
             f"[bg][glow]overlay=(W-w)/2:(H-h)/2:shortest=1[g];"
             f"[g][main]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[ident];"
             f"[v0][ident]concat=n=2:v=1:a=0[vout];")
    inputs = ["-i", str(video), "-loop", "1", "-framerate", str(config.OUT_FPS), "-t", f"{outro:.3f}", "-i", str(LOGO)]
    if info["audio"]:
        if sound:
            inputs += ["-i", str(SOUND)]
            graph += (f"[0:a]afade=t=out:st={max(0,content-0.35):.3f}:d=0.35[a0];"
                      f"[2:a]volume=0.48,afade=t=out:st={outro-0.35:.3f}:d=0.35[a1];"
                      "[a0][a1]concat=n=2:v=0:a=1[aout]")
        else:
            graph += (f"[0:a]afade=t=out:st={max(0,content-0.35):.3f}:d=0.35[a0];"
                      f"anullsrc=r=48000:cl=stereo,atrim=duration={outro:.3f}[a1];[a0][a1]concat=n=2:v=0:a=1[aout]")
    elif sound:
        inputs += ["-i", str(SOUND)]
        graph += f"anullsrc=r=48000:cl=stereo,atrim=duration={content:.3f}[a0];[2:a]volume=0.48[a1];[a0][a1]concat=n=2:v=0:a=1[aout]"
    else:
        inputs += ["-f", "lavfi", "-t", f"{content+outro:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        graph += "[2:a]anull[aout]"
    maps = ["-map", "[vout]", "-map", "[aout]"]
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, *maps,
           "-c:v", "libx264", "-crf", "21", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(output)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=NO_WINDOW)
    if p.returncode:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Outro export failed: {p.stderr[-900:]}")


def append(video: Path, duration: float = DURATION, sound: bool = True, animated: bool = True) -> None:
    """Append ident in-place through a sibling temp file; keep original intact on failure."""
    video = Path(video)
    with tempfile.TemporaryDirectory(prefix="fpout") as tmp:
        result = Path(tmp) / "final.mp4"
        _command(video, result, duration, sound, animated)
        if not result.is_file() or result.stat().st_size < 1024:
            raise RuntimeError("The outro export did not produce a playable video.")
        result.replace(video)


def preview() -> Path:
    """Build and cache the vertical preview from the same composition used for exports."""
    cache = config.TMP_DIR / "minute-dose-outro-preview.mp4"
    if cache.is_file() and cache.stat().st_size > 1024:
        return cache
    config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fp-preview") as tmp:
        src = Path(tmp) / "black.mp4"
        rendered = Path(tmp) / "rendered.mp4"
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                            f"color=c=black:s={config.OUT_W}x{config.OUT_H}:r={config.OUT_FPS}:d=0.05",
                            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.05", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", str(src)], capture_output=True, text=True,
                           timeout=60, creationflags=NO_WINDOW)
        if p.returncode:
            raise RuntimeError(f"Could not create outro preview: {p.stderr[-500:]}")
        _command(src, rendered, DURATION, True, True)
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "0.05", "-i", str(rendered), "-t",
                            f"{DURATION:.3f}", "-c:v", "libx264", "-crf", "21", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(cache)],
                           capture_output=True, text=True, timeout=120, creationflags=NO_WINDOW)
        if p.returncode:
            cache.unlink(missing_ok=True)
            raise RuntimeError(f"Could not finish outro preview: {p.stderr[-500:]}")
    return cache
