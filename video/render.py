"""Render one MP4: each shot image held from its start to the next shot's start, slow zoom, overlay text,
over the voiceover. Frame-exact cuts at 30 fps so nothing drifts against the audio."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/user/123"
FPS = 30
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
VO = f"{ROOT}/voiceover/the-man-who-survived-two-atomic-bombs-full.mp3"
OUT = f"{ROOT}/video/the-man-who-survived-two-atomic-bombs-draft.mp4"
WORK = sys.argv[1]
IN_BUBBLE = {34: (1375, 335)}  # shot -> centre of its speech bubble, in output pixels

shots = json.load(open(f"{ROOT}/visuals/shot_prompts.json"))
audio_len = float(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VO]))
total_frames = round(audio_len * FPS)


def frame(t):
    return min(round(t * FPS), total_frames)


def render(i):
    s = shots[i]
    f0 = frame(s["start_sec"])
    f1 = frame(shots[i + 1]["start_sec"]) if i + 1 < len(shots) else total_frames
    n = f1 - f0
    # upscale first so the slow zoom moves smoothly instead of stepping a pixel at a time
    vf = (f"scale=3840:2160,zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={n}:s=1920x1080:fps={FPS}")
    if s["overlay_text"]:
        txt = f"{WORK}/text{s['shot']:02d}.txt"
        open(txt, "w").write(s["overlay_text"])
        if s["shot"] in IN_BUBBLE:  # the image has an empty speech bubble waiting for this word
            cx, cy = IN_BUBBLE[s["shot"]]
            style = f"fontsize=88:fontcolor=black:x={cx}-text_w/2:y={cy}-text_h/2"
        else:
            style = ("fontsize=100:fontcolor=white:borderw=5:bordercolor=black:shadowcolor=black@0.45:"
                     "shadowx=4:shadowy=5:x=(w-text_w)/2:y=h*0.07")
        vf += f",drawtext=fontfile={FONT}:textfile={txt}:{style}:alpha='min(1,t/0.25)'"
    out = f"{WORK}/clip{s['shot']:02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{ROOT}/{s['image_file']}", "-vf", vf,
                    "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-r", str(FPS), out], check=True)
    return out, n


with ThreadPoolExecutor(4) as ex:
    results = list(ex.map(render, range(len(shots))))
assert sum(n for _, n in results) == total_frames, (sum(n for _, n in results), total_frames)

with open(f"{WORK}/list.txt", "w") as f:
    for out, _ in results:
        f.write(f"file '{out}'\n")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/list.txt", "-i", VO,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", OUT], check=True)
print("done", OUT, total_frames, "frames")
