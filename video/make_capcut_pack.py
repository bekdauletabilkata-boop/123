"""Build a CapCut import pack: one still-video clip per shot with its exact duration baked in, plus the
voiceover, captions and text overlay list. Laid end to end from 0:00, the clips line up with the voiceover.
usage: python3 video/make_capcut_pack.py <output dir>"""
import json
import os
import shutil
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
VO = f"{ROOT}/voiceover/the-man-who-survived-two-atomic-bombs-full.mp3"
OUT = sys.argv[1]
PACK = f"{OUT}/CapCut import - The Man Who Survived Two Atomic Bombs"

shots = json.load(open(f"{ROOT}/visuals/shot_prompts.json"))
audio_len = float(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VO]))
total_frames = round(audio_len * FPS)


def frame(t):
    return min(round(t * FPS), total_frames)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def make_clip(i):
    s = shots[i]
    f0 = frame(s["start_sec"])
    f1 = frame(shots[i + 1]["start_sec"]) if i + 1 < len(shots) else total_frames
    out = f"{PACK}/clips/clip{s['shot']:02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", f"{ROOT}/{s['image_file']}",
                    "-frames:v", str(f1 - f0), "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                    "-tune", "stillimage", "-crf", "16", "-pix_fmt", "yuv420p", out], check=True)
    return s, f0, f1


shutil.rmtree(PACK, ignore_errors=True)
os.makedirs(f"{PACK}/clips")
with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(make_clip, range(len(shots))))
assert sum(f1 - f0 for _, f0, f1 in rows) == total_frames

shutil.copy(VO, f"{PACK}/voiceover.mp3")
shutil.copy(f"{ROOT}/voiceover/captions.srt", f"{PACK}/captions.srt")

with open(f"{PACK}/timeline.txt", "w") as f:
    f.write("Clip order and timing (30 fps). Each clip already has this exact length.\n\n")
    for s, f0, f1 in rows:
        line = f"clip{s['shot']:02d}.mp4  {mmss(f0 / FPS)} - {mmss(f1 / FPS)}  ({(f1 - f0) / FPS:.2f}s)"
        if s["overlay_text"]:
            line += f"   TEXT: {s['overlay_text']}"
        f.write(line + "\n")

with open(f"{PACK}/HOW TO IMPORT.txt", "w") as f:
    f.write("""HOW TO IMPORT INTO CAPCUT
1. Unzip this file first (CapCut can't open a .zip). On a phone, unzip it in the Files app.
2. New project. Import everything in the "clips" folder plus voiceover.mp3.
3. Select clip01 to clip53 in order (desktop: sort the media panel by name, click clip01, shift-click clip53;
   phone: tap them in order 01, 02, 03 ...) and add them to the timeline starting at 0:00.
   They sit end to end and run exactly 2:56.1.
4. Put voiceover.mp3 on the audio track at 0:00. The pictures now change exactly with the narration.
5. Optional: Captions > Import captions > captions.srt (desktop) for the narration subtitles.
6. Optional: add the on-screen words from timeline.txt (lines marked TEXT) as text layers.
Don't change clip lengths or add transitions that overlap clips, or the pictures drift off the voice.
""")

zpath = f"{OUT}/capcut-import-pack.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
    for dirpath, _, files in os.walk(PACK):
        for name in sorted(files):
            full = os.path.join(dirpath, name)
            z.write(full, os.path.relpath(full, OUT))
print("done", zpath, total_frames, "frames")
