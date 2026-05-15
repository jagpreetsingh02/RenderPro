import subprocess
import shutil
import sys
import os

print("Checking ffmpeg...", flush=True)

ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    print("System ffmpeg not found.", flush=True)
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"imageio-ffmpeg found at: {ffmpeg}", flush=True)
    except ImportError:
        print("imageio-ffmpeg not found.", flush=True)
        ffmpeg = None

if ffmpeg:
    print(f"Running version check on {ffmpeg}", flush=True)
    try:
        subprocess.run([ffmpeg, "-version"], check=True)
        print("ffmpeg version check passed.", flush=True)
    except Exception as e:
        print(f"ffmpeg failed: {e}", flush=True)
else:
    print("No ffmpeg found!", flush=True)

print("Test complete.", flush=True)
