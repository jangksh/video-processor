"""
Auto Video Ratio Converter - Folder Watcher
- Drop a video into input_videos/ to auto-convert
- 9:16->16:9 or 16:9->9:16 auto detected
- Results saved to output_videos/
"""

import time
import shutil
import ffmpeg
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INPUT_DIR = Path("input_videos")
OUTPUT_DIR = Path("output_videos")
DONE_DIR = Path("input_videos/done")

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DONE_DIR.mkdir(exist_ok=True)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def get_video_ratio(filepath: str):
    """Return video width and height."""
    probe = ffmpeg.probe(filepath)
    video_stream = next(
        s for s in probe["streams"] if s["codec_type"] == "video"
    )
    w = int(video_stream["width"])
    h = int(video_stream["height"])
    return w, h


def convert(src: Path):
    try:
        w, h = get_video_ratio(str(src))
    except Exception as e:
        print(f"    [ERROR] Failed to read video info: {e}")
        return

    ratio = w / h
    print(f"    Source: {w}x{h} (ratio {ratio:.3f})")

    # portrait -> landscape
    if ratio < 1.0:
        target_w, target_h = 1920, 1080
        direction = "9:16 -> 16:9"
    # landscape -> portrait
    else:
        target_w, target_h = 1080, 1920
        direction = "16:9 -> 9:16"

    print(f"    Convert: {direction}")

    output_path = OUTPUT_DIR / f"{src.stem}_converted.mp4"

    try:
        # blur background overlay
        bg = (
            ffmpeg.input(str(src)).video
            .filter("scale", target_w, target_h, force_original_aspect_ratio="increase")
            .filter("crop", target_w, target_h)
            .filter("boxblur", luma_radius=30, luma_power=3)
        )
        fg = (
            ffmpeg.input(str(src)).video
            .filter("scale", target_w, target_h, force_original_aspect_ratio="decrease")
            .filter("pad", target_w, target_h, "(ow-iw)/2", "(oh-ih)/2", color="black@0")
        )
        audio = ffmpeg.input(str(src)).audio
        (
            ffmpeg.output(
                ffmpeg.overlay(bg, fg), audio, str(output_path),
                vcodec="libx264", acodec="aac", preset="veryfast", crf=23,
                movflags="+faststart"
            )
            .run(overwrite_output=True, quiet=True)
        )
        print(f"    [DONE] -> {output_path.name}")
        # move source to done/
        shutil.move(str(src), str(DONE_DIR / src.name))

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "unknown error"
        print(f"  ❌ ffmpeg 오류:\n{stderr}")


def wait_until_ready(path: Path, timeout=30) -> bool:
    """Wait until file size stops changing."""
    prev_size = -1
    for _ in range(timeout):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == prev_size and size > 0:
            return True
        prev_size = size
        time.sleep(1)
    return False


class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            return
        if path.parent == DONE_DIR:
            return

        print(f"\n[+] New file detected: {path.name}")
        print("    Waiting for file copy...")
        if not wait_until_ready(path):
            print("    [WARN] File ready timeout")
            return

        convert(path)


if __name__ == "__main__":
    print("=" * 50)
    print("[*] Auto Video Ratio Converter Running")
    print(f"    INPUT : {INPUT_DIR.resolve()}")
    print(f"    OUTPUT: {OUTPUT_DIR.resolve()}")
    print(f"    DONE  : {DONE_DIR.resolve()}")
    print("    FORMAT:", ", ".join(VIDEO_EXTENSIONS))
    print("    METHOD: Blur Background")
    print("    Press Ctrl+C to stop")
    print("=" * 50)

    # process existing files
    existing = [
        f for f in INPUT_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if existing:
        print(f"\nProcessing {len(existing)} existing files...")
        for f in existing:
            print(f"\n[+] Processing: {f.name}")
            convert(f)

    observer = Observer()
    observer.schedule(VideoHandler(), str(INPUT_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped.")
    observer.join()
