"""Write the CapCut edit plan for 'Atomic bomb': video cuts with subtle zoom keyframes, title text, word-timed
captions, sound-effect cues and music beds, all on the voiceover's clock. Outputs video/edit_plan.json (for
building the CapCut timeline) and video/edit-plan.md (to read). Every text item is measured to fit the frame."""
import json
import os

from PIL import ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS, W, H = 30, 1920, 1080
SAFE_W = W * 0.86  # action-safe width for text
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
TOTAL = 176.1

shots = json.load(open(f"{ROOT}/visuals/shot_prompts.json"))
words = json.load(open(f"{ROOT}/voiceover/words.json"))


def fits(text, size):
    return ImageFont.truetype(FONT, size).getlength(text) <= SAFE_W


def snap(t):
    return round(t * FPS) / FPS


# --- video: one image per shot, cut on the voice, alternating super-subtle zoom in / zoom out ---
video = []
for i, s in enumerate(shots):
    start = snap(s["start_sec"])
    end = snap(shots[i + 1]["start_sec"]) if i + 1 < len(shots) else TOTAL
    amount = 1.03 if end - start >= 1.5 else 1.015  # short shots move even less
    zoom = (1.0, amount) if i % 2 == 0 else (amount, 1.0)
    video.append({"shot": s["shot"], "image": s["image_file"], "clip": f"clips/clip{s['shot']:02d}.mp4",
                  "start": start, "end": end,
                  "keyframes": [{"t": start, "scale": zoom[0]}, {"t": end, "scale": zoom[1]}],
                  "anchor": "center", "easing": "linear"})

# --- title text: the on-screen words, top centre (shot 34 sits inside its speech bubble) ---
titles = []
for v, s in zip(video, shots):
    if not s["overlay_text"]:
        continue
    size = 100
    assert fits(s["overlay_text"], size), s["overlay_text"]
    item = {"shot": s["shot"], "text": s["overlay_text"], "start": round(v["start"] + 0.1, 2), "end": v["end"],
            "font_px": size, "weight": "extra bold", "fade_in": 0.2}
    if s["shot"] == 34:
        item.update(color="black", stroke=None, center_px=[1375, 335], note="inside the empty speech bubble")
    else:
        item.update(color="white", stroke={"color": "black", "px": 5}, shadow=True, center_px=[960, 140])
    titles.append(item)

# --- captions: short word-timed chunks at the bottom, max ~30 characters, break on punctuation ---
def join(ws):
    return " ".join(x["w"] for x in ws).replace(" -", "-")


phrases, cur = [], []
for i, w in enumerate(words):  # a phrase ends at punctuation or a pause
    cur.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    if not nxt or w["w"][-1] in ".,?!" or nxt["s"] - w["e"] > 0.35:
        phrases.append(cur)
        cur = []
captions = []
for ph in phrases:  # long phrases split into balanced parts of at most ~30 characters
    parts = -(-len(join(ph)) // 34)
    target = len(join(ph)) / parts
    chunk = []
    for w in ph:
        no_break = w["w"].startswith("-") or (chunk and chunk[-1]["w"] == "Tsutomu" and w["w"].startswith("Yamaguchi"))
        if chunk and len(join(chunk)) >= target and parts > 1 and not no_break:
            captions.append({"text": join(chunk), "start": chunk[0]["s"], "word_end": chunk[-1]["e"]})
            chunk, parts = [], parts - 1
        chunk.append(w)
    captions.append({"text": join(chunk), "start": chunk[0]["s"], "word_end": chunk[-1]["e"]})
for i, c in enumerate(captions):
    nxt = captions[i + 1]["start"] if i + 1 < len(captions) else TOTAL
    c["end"] = round(min(nxt, c["word_end"] + 0.6), 2)
    c["end"] = max(c["end"], round(c["start"] + 0.5, 2)) if c["end"] - c["start"] < 0.5 and nxt - c["start"] >= 0.5 else c["end"]
    del c["word_end"]
    assert fits(c["text"], 64), c["text"]
CAPTION_STYLE = {"font_px": 64, "weight": "extra bold", "color": "white", "stroke": {"color": "black", "px": 4},
                 "center_px": [960, 960], "max_width_px": int(SAFE_W)}

# --- sound effects: (time, length, what, search words, level dB) anchored to the spoken words ---
SFX = [
    (0.0, 2.5, "deep distant boom under the opening flash", "boom, distant explosion, sub drop", -10),
    (4.7, 2.0, "train whistle and chug on 'train'", "train whistle, steam train", -14),
    (7.6, 2.0, "explosion impact on 'hit by a second one'", "explosion, impact", -8),
    (9.7, 1.0, "calendar page flip", "page flip, paper whoosh", -12),
    (11.25, 0.8, "rubber stamp thud", "stamp, thud", -10),
    (13.4, 1.5, "soft reveal chime on his name", "chime, reveal, ding", -16),
    (15.4, 3.5, "shipyard ambience: metal clanks, gulls", "shipyard, metal clank, harbor", -20),
    (19.0, 2.4, "pencil scribbling", "pencil writing, scribble", -16),
    (22.5, 0.5, "map pin pop on 'Nagasaki'", "pop, bubble pop", -14),
    (24.0, 1.0, "whoosh as he sets off", "whoosh", -16),
    (29.4, 3.5, "clock ticking on 'August 6th'", "clock tick", -18),
    (33.9, 2.0, "dreamy shimmer for the thought bubble", "shimmer, magic chime", -18),
    (38.1, 2.3, "morning birds", "birds morning", -20),
    (40.8, 3.0, "distant propeller plane on 'heard a plane'", "propeller plane, plane flyby", -16),
    (43.4, 4.4, "wind, parachute flutter", "wind, cloth flutter", -20),
    (47.9, 0.9, "single heartbeat in the silence after 'Then,'", "heartbeat", -12),
    (48.8, 3.0, "huge flash impact with high ring on 'a flash'", "explosion big, cinematic impact", -6),
    (54.6, 2.5, "shockwave whoosh and rumble", "shockwave, rumble, heavy whoosh", -8),
    (59.0, 2.2, "ear ringing on 'eardrums burst'", "tinnitus, ear ringing", -14),
    (65.4, 4.2, "low rumble under the mushroom cloud", "low rumble, distant thunder", -12),
    (69.6, 2.6, "night crickets in the shelter", "crickets night", -20),
    (75.2, 2.3, "steam train whistle and chuff", "steam train", -14),
    (77.5, 2.0, "train brakes hiss arriving", "train brakes, steam hiss", -14),
    (85.0, 2.3, "ominous low stinger on 'Surely, the worst was over'", "ominous stinger, dark hit", -12),
    (87.3, 1.0, "office door opening", "door open", -16),
    (105.7, 2.2, "heartbeat and rising tone on 'at that exact moment'", "heartbeat, riser", -12),
    (107.9, 3.0, "huge flash impact with high ring (same as Hiroshima)", "explosion big, cinematic impact", -6),
    (112.4, 4.0, "low rumble", "low rumble", -12),
    (118.1, 2.0, "debris settling, cough", "debris, rubble", -16),
    (121.0, 5.0, "slow clock ticking through the fever week", "clock tick", -20),
    (130.5, 4.5, "time-passing whoosh", "whoosh, time lapse", -16),
    (140.5, 1.0, "soft chime on '2009'", "chime", -16),
    (146.9, 1.0, "spotlight switching on", "spotlight switch, clunk", -14),
    (150.8, 4.0, "crowd murmur, then light applause", "crowd, applause", -20),
    (158.0, 0.5, "soft boom on 'Twice.'", "boom soft", -12),
    (158.3, 0.6, "second soft boom", "boom soft", -12),
    (164.3, 3.3, "rain on the unlucky man", "rain", -18),
    (167.6, 1.5, "sparkle on 'luckiest'", "sparkle", -16),
    (171.3, 0.5, "pop as the comment icon appears", "pop", -14),
    (172.46, 0.5, "mouse click on 'subscribe'", "mouse click", -12),
]
sfx = [{"start": t, "length": d, "what": what, "search": [k.strip() for k in kw.split(",")], "level_db": db}
       for t, d, what, kw, db in SFX]

# --- music: beds under the voice; silence before each flash so the impact lands ---
music = [
    {"start": 0.0, "end": 47.9, "mood": "tense, mysterious documentary underscore (piano + low strings)",
     "search": ["documentary tension", "mystery piano", "suspense"], "level_db": -22, "fade_in": 1.0,
     "out": "hard cut at 47.9 on 'Then,'"},
    {"start": 51.2, "end": 105.7, "mood": "dark, somber ambient drone / strings",
     "search": ["dark ambient", "somber strings", "drone"], "level_db": -24, "fade_in": 2.0,
     "out": "hard cut at 105.7 on 'And at that exact moment'"},
    {"start": 111.3, "end": 126.9, "mood": "same somber bed as above, continued",
     "search": ["dark ambient", "somber strings"], "level_db": -24, "fade_in": 1.5, "out": "2 s crossfade"},
    {"start": 126.9, "end": TOTAL, "mood": "warm, hopeful, reflective piano",
     "search": ["hopeful piano", "emotional", "reflective"], "level_db": -22, "fade_in": 2.0,
     "out": "2 s fade out at the end"},
]

plan = {"project": "Atomic bomb", "fps": FPS, "canvas": [W, H], "duration": TOTAL,
        "voiceover": {"file": "voiceover/the-man-who-survived-two-atomic-bombs-full.mp3", "start": 0.0,
                      "level_db": 0},
        "video": video, "titles": titles, "captions": captions, "caption_style": CAPTION_STYLE,
        "sfx": sfx, "music": music,
        "rules": ["Clips sit end to end from 0:00 with no gaps or overlaps; no transitions that overlap clips.",
                  "Zoom keyframes stay inside each clip; scale changes no more than 3% per clip.",
                  "Voice peaks stay on top: music -22 to -24 dB, effects as listed, mix peak below -0.5 dBFS.",
                  "All text inside 86% of frame width; titles top centre, captions bottom centre."]}
json.dump(plan, open(f"{ROOT}/video/edit_plan.json", "w"), indent=1, ensure_ascii=False)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


with open(f"{ROOT}/video/edit-plan.md", "w") as f:
    f.write("# Edit plan — 'Atomic bomb'\n\nEverything is timed to `voiceover/the-man-who-survived-two-atomic-bombs-full.mp3` "
            "(2:56.1, 30 fps). Machine-readable version: `video/edit_plan.json`.\n\n")
    f.write("## Video (53 shots, subtle zoom)\n\n| Shot | Start | End | Zoom |\n|---|---|---|---|\n")
    for v in video:
        a, b = v["keyframes"][0]["scale"], v["keyframes"][1]["scale"]
        f.write(f"| {v['shot']} | {mmss(v['start'])} | {mmss(v['end'])} | {a*100:.1f}% → {b*100:.1f}% |\n")
    f.write("\n## Title text (top centre, white, black outline; checked to fit)\n\n| Shot | Start | End | Text |\n|---|---|---|---|\n")
    for t in titles:
        f.write(f"| {t['shot']} | {mmss(t['start'])} | {mmss(t['end'])} | **{t['text']}**{' (in speech bubble)' if t['shot'] == 34 else ''} |\n")
    f.write(f"\n## Captions\n\n{len(captions)} word-timed captions, bottom centre, 64 px, max 86% width — see `edit_plan.json`.\n")
    f.write("\n## Sound effects\n\n| Time | What | Level |\n|---|---|---|\n")
    for x in sfx:
        f.write(f"| {mmss(x['start'])} | {x['what']} | {x['level_db']} dB |\n")
    f.write("\n## Music\n\n| From | To | Mood | Level | Ending |\n|---|---|---|---|---|\n")
    for m in music:
        f.write(f"| {mmss(m['start'])} | {mmss(m['end'])} | {m['mood']} | {m['level_db']} dB | {m['out']} |\n")
print(len(video), "shots,", len(titles), "titles,", len(captions), "captions,", len(sfx), "sfx,", len(music), "music beds")
