"""End-card composition checks for vertical, landscape and square clips."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from studio import outro, render  # noqa: E402


def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height", "-of", "json", str(path)], text=True))


def main():
    with tempfile.TemporaryDirectory(prefix="minute-dose-outro-") as td:
        root = Path(td)
        for w, h, label in ((1080, 1920, "vertical"), (640, 360, "landscape"), (480, 480, "square")):
            src = root / f"{label}.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                f"testsrc2=size={w}x{h}:rate=24:duration=1.2", "-f", "lavfi", "-i",
                "sine=frequency=440:sample_rate=48000:duration=1.2", "-c:v", "libx264", "-pix_fmt",
                "yuv420p", "-c:a", "aac", "-shortest", str(src)], check=True, timeout=60)
            before = probe(src)
            outro.append(src, sound=True)
            after = probe(src)
            print(f"{label}: before={before['format']['duration']} after={after['format']['duration']}")
            video = next(s for s in after["streams"] if s["codec_type"] == "video")
            audio = next(s for s in after["streams"] if s["codec_type"] == "audio")
            assert (video["width"], video["height"]) == (w, h), (label, video)
            assert abs(float(after["format"]["duration"]) - (float(before["format"]["duration"]) + outro.DURATION)) < 0.15
            assert audio["codec_type"] == "audio"
            print(f"PASS {label}: resolution retained; +{float(after['format']['duration'])-float(before['format']['duration']):.2f}s; audio present")

        silent = root / "silent.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "color=c=blue:s=320x180:r=24:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent)],
            check=True, timeout=60)
        outro.append(silent, sound=False)
        assert any(s["codec_type"] == "audio" for s in probe(silent)["streams"])
        print("PASS silent source: valid output with silent audio bed")

        source = root / "portrait-source.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=240x426:rate=30:duration=1.2", "-f", "lavfi", "-i",
            "sine=frequency=440:sample_rate=48000:duration=1.2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(source)], check=True, timeout=60)
        exported = root / "export"
        rendered = render.render_clip(source, exported, "clip", {"start":0, "end":1.2, "layout":"crop",
            "captions":False, "branded_outro":True, "outro_sound":True}, [], 240, 426)
        actual = probe(exported / rendered["file"])
        dims = next(s for s in actual["streams"] if s["codec_type"] == "video")
        assert (dims["width"], dims["height"]) == (1080, 1920)
        assert abs(float(actual["format"]["duration"]) - 3.9) < 0.15
        print("PASS actual vertical export: 1080x1920, source audio plus synchronized outro")

        preview = outro.preview()
        preview_info = probe(preview)
        assert abs(float(preview_info["format"]["duration"]) - outro.DURATION) < 0.15
        assert (next(s for s in preview_info["streams"] if s["codec_type"] == "video")["width"],
                next(s for s in preview_info["streams"] if s["codec_type"] == "video")["height"]) == (1080, 1920)
        cached_mtime = preview.stat().st_mtime_ns
        assert outro.preview() == preview and preview.stat().st_mtime_ns == cached_mtime
        print("PASS preview: exact outro length and reused cached render")


if __name__ == "__main__":
    main()
