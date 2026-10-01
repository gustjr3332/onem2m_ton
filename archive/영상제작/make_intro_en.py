"""PolaGrid 팀 소개 영상 영어판(oneM2M 공모전용). make_intro.py와 같은 그림·시연 클립·TTS(모델·보이스)를 쓰고,
대사는 한국어판 대사(+시연 클립에 박힌 자막)를 영어로 옮겨 30초를 채운다. 화면 글자와 자막도 모두 영어.
사용: GEMINI_API_KEY 설정 후 python make_intro_en.py [--preview 초,초,...]"""
import re
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import make_intro as ko
from make_intro import (BAR, CREAM, FPS, GEN, INK, NAVY, SR, TOTAL, W, H, XF, fade, fade_in, font, gen_image,
                        gen_tts, kenburns, mark, paste, speed)

OUT = ko.ASSETS / "PolaGrid_introduce_EN.mp4"
# (시작, 길이, 영어 대사) — 20초 구간은 한국어 대사 앞에 시연 클립 자막("AI가 해 위치·칸별 조도·책상 조도로 어느 칸이 눈부심을 만드는지 찾는다")을 옮겨 붙임
SEGS = [
    (0.0, 8.0, "Hi, I'm Hyunseok Lee, an Intelligent IoT Convergence major at Sejong University. Let me introduce PolaGrid, a service I planned on my own."),
    (8.0, 6.0, "Stack two polarizing films and rotate one of them, and less light passes through."),
    (14.0, 6.0, "We split the window into small cells, and AI sets each cell's angle from the sun's position and brightness."),
    (20.0, 10.0, "AI uses the sun's position and light readings to find the glare cells. Only those cells rotate, so you keep the view and lose the glare. This was PolaGrid."),
]
LEAD, TAIL = 0.25, 0.3
MAX_RATE, MIN_RATE = 1.25, 0.9                     # 구간에 맞출 때 허용 배속(느리게는 0.9배까지 늘려 빈 시간을 줄임)


def build_audio():
    """구간마다 음성을 넣고, 자막 타이밍용 (시작, 끝)을 돌려준다."""
    track = np.zeros(int(TOTAL * SR), dtype=np.int16)
    spans = []
    for i, (start, dur, text) in enumerate(SEGS):
        pcm = gen_tts(f"en{i}", text)
        fit = dur - LEAD - TAIL
        rate = len(pcm) / SR / fit
        if rate > MAX_RATE:
            sys.exit(f"구간 {i} 음성 {len(pcm) / SR:.1f}초: {MAX_RATE}배로도 {dur}초에 안 들어감 → 대사를 줄일 것")
        if rate > 1.0 or rate < MIN_RATE:
            pcm = speed(pcm, min(max(rate, MIN_RATE), MAX_RATE))
        s = int((start + LEAD) * SR)
        track[s:s + len(pcm)] = fade(pcm)
        spans.append((start + LEAD, start + LEAD + len(pcm) / SR))
        print(f"구간 {i}: 음성 {len(pcm) / SR:.1f}초 / {dur}초 (원본 대비 {rate:.2f}배)", flush=True)
    path = GEN / "narration_en.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(track.tobytes())
    return path, spans


def cues(spans):
    """대사를 문장 단위 자막으로 나누고, 글자 수 비율로 말하는 시간에 배분. 구간 끝까지 마지막 자막 유지."""
    out = []
    for (start, dur, text), (a, b) in zip(SEGS, spans):
        parts = [s for s in re.split(r"(?<=[.!?])\s+", text) if s]
        total = sum(len(s) for s in parts)
        t = a
        for k, s in enumerate(parts):
            end = start + dur if k == len(parts) - 1 else t + (b - a) * len(s) / total
            out.append((start if k == 0 else t, end, s))
            t = end
    return out


def subtitle(img, text):
    """화면 아래 자막 바. 한 줄에 안 들어가면 두 줄로."""
    d = ImageDraw.Draw(img)
    f = font(34)
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=f) > W - 160 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    lines.append(cur)
    h = 96 if len(lines) == 1 else 140
    d.rectangle([0, H - h, W, H], fill=BAR)
    for k, ln in enumerate(lines):
        y = H - h / 2 + (k - (len(lines) - 1) / 2) * 44
        d.text((W / 2, y), ln, font=f, fill=(255, 255, 255), anchor="mm")
    return img


def intro_overlay(img, t):
    """세종대 교표 + 영문 로고타입 + 소속 → 이름 → 서비스명."""
    a, b, c = fade_in(t, 0.3), fade_in(t, 1.8), fade_in(t, 4.2)
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    d.rounded_rectangle([90, 200, 900, 840], 28, fill=(255, 255, 255, int(240 * a)))
    paste(over, mark("mark_seal.png", 150), (150, 255), a)
    paste(over, mark("mark_logotype_en.png", 36), (332, 292), a)
    d.text((332, 348), "Intelligent IoT Convergence", font=font(32), fill=(*INK, int(255 * a)), anchor="lt")
    d.line([(150, 445), (840, 445)], fill=(*NAVY, int(90 * a)), width=2)
    d.text((150, 470), "Hyunseok Lee", font=font(60, True), fill=(*INK, int(255 * b)), anchor="lt")
    d.text((152, 585), "A solo-planned service", font=font(32), fill=(*INK, int(255 * c)), anchor="lt")
    d.text((148, 625), "PolaGrid", font=font(92, True), fill=(*NAVY, int(255 * c)), anchor="lt")
    d.text((152, 752), "AI polarizing window that cuts only the glare", font=font(30), fill=(*INK, int(255 * c)), anchor="lt")
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


# 시연 클립 위쪽에 박힌 한국어 문구("눈부심 해결 · 방은 그대로 밝음", 원본 1280x720 기준 중앙 640,40)를 영어로 덮는다
LABEL_BOX = tuple(int(v * 1.5) for v in (420, 22, 860, 60))


def clip_frame(frame_img):
    img = frame_img.copy()
    region = np.asarray(img.crop(LABEL_BOX).convert("L"))
    vis = min(1.0, (region < 150).sum() / 900)               # 원래 문구가 보이는 정도(페이드 반영)
    d = ImageDraw.Draw(img)
    d.rectangle(LABEL_BOX, fill=CREAM)
    if vis > 0.02:
        col = tuple(int(CREAM[k] + (NAVY[k] - CREAM[k]) * vis) for k in range(3))
        d.text((W / 2, 60), "Glare fixed · Room stays bright", font=font(30, True), fill=col, anchor="mm")
    return img


def scene_frame(t, imgs, clip):
    if t < 8.0:
        return intro_overlay(kenburns(imgs["intro"], t / 8.0), t)
    if t < 14.0:
        lt = t - 8.0
        a = min(1.0, max(0.0, (lt - 2.0) / 2.0))
        return kenburns(Image.blend(imgs["polar_open"], imgs["polar_cross"], a), lt / 6.0)
    if t < 20.0:
        lt = t - 14.0
        a = min(1.0, max(0.0, (lt - 2.8) / 0.6))
        return Image.blend(kenburns(imgs["tech"], lt / 6.0), kenburns(imgs["building"], lt / 6.0, 1.08, 1.0), a)
    return clip_frame(clip[min(int((t - 20.0) * FPS), len(clip) - 1)])


def frame(t, imgs, clip, cue_list):
    img = scene_frame(t, imgs, clip)
    for b in (8.0, 14.0, 20.0):
        if b <= t < b + XF:
            img = Image.blend(scene_frame(b - 1e-3, imgs, clip), img, (t - b) / XF)
    text = next((s for a, e, s in cue_list if a <= t < e), None)
    if text:                                                 # 시연 클립의 한국어 자막 바도 이 자막이 덮는다
        img = subtitle(img, text)
    if t > TOTAL - 0.5:
        img = Image.blend(img, Image.new("RGB", (W, H), CREAM), (t - (TOTAL - 0.5)) / 0.5)
    return img


def main():
    imgs = {k: gen_image(k, v) for k, v in ko.IMAGES.items()}
    clip = ko.load_clip()
    audio, spans = build_audio()
    cue_list = cues(spans)
    for a, e, s in cue_list:
        print(f"  {a:5.2f}–{e:5.2f}  {s}")
    if "--preview" in sys.argv:
        for s in sys.argv[sys.argv.index("--preview") + 1].split(","):
            frame(float(s), imgs, clip, cue_list).save(GEN / f"preview_en_{s}.png")
        return
    w = imageio_ffmpeg.write_frames(str(OUT), (W, H), fps=FPS, codec="libx264", pix_fmt_out="yuv420p", quality=8,
                                    audio_path=str(audio), audio_codec="aac", macro_block_size=8)
    w.send(None)
    for i in range(int(TOTAL * FPS)):
        w.send(np.asarray(frame(i / FPS, imgs, clip, cue_list)).tobytes())
    w.close()
    print("saved", OUT)


if __name__ == "__main__":
    main()
