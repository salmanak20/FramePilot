# PyInstaller bundle for the Windows, macOS and Linux desktop builds.
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all
from static_ffmpeg import run as static_ffmpeg_run

root = Path(SPECPATH)
ffmpeg, ffprobe = static_ffmpeg_run.get_or_fetch_platform_executables_else_raise()
datas = [(str(root / "web"), "web"), (str(root / "studio" / "fonts"), "studio/fonts")]
binaries = [(ffmpeg, "ffmpeg/bin"), (ffprobe, "ffmpeg/bin")]
hiddenimports = []

for package in (
    "fastapi", "starlette", "uvicorn", "httpx", "sqlalchemy", "numpy", "PIL",
    "soundfile", "sherpa_onnx", "yt_dlp", "multipart", "webview", "static_ffmpeg",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    [str(root / "desktop.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "notebook"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FramePilot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="FramePilot")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="FramePilot.app", icon=None, bundle_identifier="com.salmanak20.framepilot")
