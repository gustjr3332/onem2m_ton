"""PolaGrid 팀 소개 영상(30초, 1920x1080): Nano Banana 장면 이미지 + Gemini TTS + 시연 영상 클립을 한 번에 합친다.
구성: 0–8 개인 소개 → 8–14 원리 → 14–20 기술 → 20–30 시연(04_PolaGrid_시연영상.mp4 25.0–33.6초 + 마지막 장면 정지).
사용: GEMINI_API_KEY 설정 후 python make_intro.py [--preview 초,초,...]
생성한 이미지·음성은 intro_gen/ 에 캐시되어 재실행 시 다시 만들지 않는다(다시 만들려면 해당 파일 삭제)."""
import hashlib
import io
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
GEN = HERE / "intro_gen"
ASSETS = HERE.parents[1] / "docs" / "제출용_AI공모전자료"   # 영상 원본·결과물 위치(스크립트는 archive로 이동)
SRC_CLIP = ASSETS / "04_PolaGrid_시연영상.mp4"
OUT = ASSETS / "PolaGrid_소개영상.mp4"
W, H, FPS, TOTAL = 1920, 1080, 30, 30.0
SR = 24000                                   # Gemini TTS 출력: 24kHz 16bit mono PCM
IMAGE_MODEL, TTS_MODEL, VOICE = "gemini-3-pro-image", "gemini-3.8-flash-lite-tts", "Charon"   # Charon: 남성, Informative
NAVY, INK, BAR, CREAM = (31, 78, 121), (27, 42, 58), (20, 32, 46), (251, 248, 241)

STYLE = ("Flat vector illustration, clean editorial infographic style, warm cream background (#FBF8F1), "
         "navy (#1F4E79) and soft sand-yellow (#F6D39A) palette, gentle afternoon sunlight, minimal detail, "
         "16:9 wide composition. Absolutely no text, letters, numbers or logos anywhere in the image.")
IMAGES = {
    "intro": "A young university student maker seen from behind, sitting at a tidy desk by a sunny window, "
             "working on a small prototype: a square frame holding a round polarizing film with a tiny servo motor and an "
             "Arduino-like board with wires. The person and desk occupy the right 55% of the frame; the left 45% is empty "
             "cream wall space.",
    "polar_open": "Close-up diagram-like scene: a soft glowing sun light source on the left shining through two round, "
                  "slightly transparent grey polarizing film discs stacked one behind the other, both with fine parallel lines "
                  "pointing the same direction. Plenty of bright warm light passes through and lights up a white sheet of "
                  "paper on the right.",
    "polar_cross": "Same diagram-like scene: a soft glowing sun light source on the left shining through two round grey "
                   "polarizing film discs stacked one behind the other, but the front disc has its fine lines rotated 90 degrees "
                   "relative to the back disc, so the overlapping area looks dark, and only dim light reaches the white sheet "
                   "of paper on the right.",
    "tech": "Inside a bright study room: a window covered on the inside by a neat 4 by 3 grid of square polarizing film "
            "panels, each with a tiny motor at its edge. The top-right two panels are rotated and darker, the rest are "
            "clear so the sky outside is visible. A small light sensor sits on the desk below and a smartphone on the desk "
            "shows a simple grid control screen.",
    "building": "A modern school building facade on a sunny afternoon, seen from outside at a slight angle. Its many "
                "windows are each divided into small square cells; scattered clusters of cells facing the sun are darker "
                "while most remain clear, forming a subtle pattern across thousands of cells.",
}
# (시작, 길이, 대사, 자막) — 대사는 TTS 발음용이라 영문은 한글로 적는다
SEGS = [
    (0.0, 8.0, "안녕하세요, 세종대학교 지능아이오티융합전공 이현석입니다. 1인 기획 서비스 폴라그리드를 소개합니다.", None),
    (8.0, 6.0, "편광판 두 장 중 한 장을 돌리면, 통과하는 빛이 줄어듭니다.", "편광판 한 장을 돌리면 → 통과하는 빛이 각도만큼 줄어든다"),
    (14.0, 6.0, "창을 칸으로 나누고, AI가 해 위치와 밝기로 칸마다 각도를 정합니다.", "창을 칸으로 나누고, AI가 해 위치·밝기로 칸마다 각도를 정한다"),
    (20.0, 10.0, "눈부심을 만드는 칸만 돌려, 창밖은 보이고 눈부심만 줄입니다. 폴라그리드였습니다.", None),
]
CLIP_FROM, CLIP_TO = 25.0, 33.6              # 원본 33.65초부터 페이드아웃, 이후는 다음 장 표지
XF = 0.4                                     # 장면 전환 크로스페이드(초)


@lru_cache(None)
def client():
    from google import genai
    return genai.Client()


def gen_image(name, prompt):
    path = GEN / f"{name}.png"
    if not path.exists():
        from google.genai import errors, types
        try:
            r = client().models.generate_content(
                model=IMAGE_MODEL, contents=f"{prompt}\n\n{STYLE}",
                config=types.GenerateContentConfig(response_modalities=["IMAGE"],
                                                   image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K")))
        except errors.APIError as e:                       # 무료 등급은 이미지 모델 할당량 0 → 자리표시 이미지로 계속
            print(f"image {name}: 생성 실패({e.code}) → 자리표시. Gemini 앱에서 만든 이미지를 {path.name} 로 넣으면 대체됨", flush=True)
            return placeholder(name)
        data = next(p.inline_data.data for p in r.candidates[0].content.parts if p.inline_data)
        path.write_bytes(data)
        print("image", name, flush=True)
    return cover(Image.open(path).convert("RGB"))


def gen_tts(i, text):
    key = hashlib.md5(f"{TTS_MODEL}|{VOICE}|{text}".encode()).hexdigest()[:8]   # 모델·보이스·대사가 바뀌면 새로 생성
    path = GEN / f"tts_{i}_{VOICE}_{key}.pcm"
    if not path.exists():
        from google.genai import types
        r = client().models.generate_content(
            model=TTS_MODEL, contents=text,                       # 스타일 지시문을 붙이면 그 문장까지 읽어 버림
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)))))
        path.write_bytes(r.candidates[0].content.parts[0].inline_data.data)
        print("tts", i, flush=True)
    data = path.read_bytes()
    if data[:4] == b"RIFF":                                  # lite 모델은 WAV 헤더째로 준다: 헤더를 소리로 읽으면 구간마다 '틱'
        with wave.open(io.BytesIO(data)) as w:
            assert w.getframerate() == SR and w.getnchannels() == 1, (w.getframerate(), w.getnchannels())
            data = w.readframes(w.getnframes())
    pcm = np.frombuffer(data, dtype=np.int16)
    loud = np.flatnonzero(np.abs(pcm) > 500)                # 앞뒤 무음 제거(말소리 앞뒤 여유는 남김)
    if len(loud):
        pcm = pcm[max(0, loud[0] - int(0.06 * SR)):loud[-1] + int(0.15 * SR)]
    return pcm


def fade(pcm, t_in=0.01, t_out=0.06):
    """잘린 경계가 0이 아니면 '틱' 소리가 나므로 양 끝을 짧게 페이드."""
    x = pcm.astype(np.float32)
    n_in, n_out = int(t_in * SR), int(t_out * SR)
    x[:n_in] *= np.linspace(0, 1, n_in)
    x[-n_out:] *= np.linspace(1, 0, n_out)
    return x.astype(np.int16)


def placeholder(name):
    img = Image.new("RGB", (W, H), (236, 230, 216))
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, W - 60, H - 60], outline=(180, 170, 150), width=4)
    d.text((W / 2, H / 2), f"이미지 자리: {name}.png", font=font(56, True), fill=(150, 140, 120), anchor="mm")
    return img


def cover(img, w=W, h=H):
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


@lru_cache(None)
def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf", size)


def kenburns(img, p, z0=1.0, z1=1.06):
    z = z0 + (z1 - z0) * p
    cw, ch = W / z, H / z
    x, y = (W - cw) / 2, (H - ch) / 2
    return img.resize((W, H), Image.BICUBIC, box=(x, y, x + cw, y + ch))


def caption(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 96, W, H], fill=BAR)
    d.text((W / 2, H - 48), text, font=font(33), fill=(255, 255, 255), anchor="mm")
    return img


@lru_cache(None)
def mark(name, height):
    im = Image.open(GEN / name)
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


def fade_in(t, start, dur=0.6):
    return min(1.0, max(0.0, (t - start) / dur))


def paste(over, im, xy, a):
    if a > 0:
        layer = im.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
        over.alpha_composite(layer, xy)


def intro_overlay(img, t):
    """세종대 부속기관 조합(교표 + 세종대학교 + 소속) → 이름 → 서비스명 순서로 등장."""
    a, b, c = fade_in(t, 0.3), fade_in(t, 1.8), fade_in(t, 4.2)
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    d.rounded_rectangle([90, 220, 880, 860], 28, fill=(255, 255, 255, int(240 * a)))
    paste(over, mark("mark_seal.png", 150), (150, 275), a)
    paste(over, mark("mark_logotype.png", 50), (334, 298), a)
    d.text((336, 366), "지능IoT융합전공", font=font(36), fill=(*INK, int(255 * a)), anchor="lt")
    d.line([(150, 465), (820, 465)], fill=(*NAVY, int(90 * a)), width=2)
    d.text((150, 495), "이현석", font=font(64, True), fill=(*INK, int(255 * b)), anchor="lt")
    d.text((152, 615), "1인 기획 서비스", font=font(32), fill=(*INK, int(255 * c)), anchor="lt")
    d.text((148, 655), "PolaGrid", font=font(92, True), fill=(*NAVY, int(255 * c)), anchor="lt")
    d.text((152, 785), "눈부심만 골라 줄이는 AI 편광 창", font=font(32), fill=(*INK, int(255 * c)), anchor="lt")
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def speed(pcm, rate):
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
           "-filter:a", f"atempo={rate:.4f}", "-f", "s16le", "-"]
    return np.frombuffer(subprocess.run(cmd, input=pcm.tobytes(), capture_output=True, check=True).stdout, dtype=np.int16)


def build_audio():
    track = np.zeros(int(TOTAL * SR), dtype=np.int16)
    lead = 0.25
    for i, (start, dur, text, _) in enumerate(SEGS):
        pcm = gen_tts(i, text)
        fit = dur - lead - 0.3
        if len(pcm) / SR > fit:                            # 구간보다 길면 피치 유지한 채 빠르게(최대 1.25배)
            rate = len(pcm) / SR / fit
            if rate > 1.25:
                sys.exit(f"구간 {i} 음성 {len(pcm) / SR:.1f}초: 1.25배로도 {dur}초에 안 들어감 → 대사를 줄일 것")
            pcm = speed(pcm, rate)
        print(f"구간 {i}: 음성 {len(pcm) / SR:.1f}초 / {dur}초", flush=True)
        s = int((start + lead) * SR)
        track[s:s + len(pcm)] = fade(pcm)
    path = GEN / "narration.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(track.tobytes())
    return path


def load_clip():
    n = int((CLIP_TO - CLIP_FROM) * FPS)
    gen = imageio_ffmpeg.read_frames(str(SRC_CLIP), input_params=["-ss", str(CLIP_FROM)])
    sw, sh = next(gen)["size"]
    frames = []
    for raw in gen:
        frames.append(Image.frombytes("RGB", (sw, sh), raw).resize((W, H), Image.LANCZOS))
        if len(frames) >= n:
            break
    gen.close()
    return frames


def scene_frame(t, imgs, clip):
    """구간별 프레임(전환 효과 전)."""
    if t < 8.0:
        return intro_overlay(kenburns(imgs["intro"], t / 8.0), t)
    if t < 14.0:
        lt = t - 8.0
        a = min(1.0, max(0.0, (lt - 2.0) / 2.0))          # 2~4초에 평행 → 직교로 전환
        img = Image.blend(imgs["polar_open"], imgs["polar_cross"], a)
        return caption(kenburns(img, lt / 6.0), SEGS[1][3])
    if t < 20.0:
        lt = t - 14.0
        a = min(1.0, max(0.0, (lt - 2.8) / 0.6))
        img = Image.blend(kenburns(imgs["tech"], lt / 6.0), kenburns(imgs["building"], lt / 6.0, 1.08, 1.0), a)
        return caption(img, SEGS[2][3])
    return clip[min(int((t - 20.0) * FPS), len(clip) - 1)]   # 클립이 끝나면 마지막(해결) 장면 정지


def frame(t, imgs, clip):
    img = scene_frame(t, imgs, clip)
    for b in (8.0, 14.0, 20.0):
        if b <= t < b + XF:
            img = Image.blend(scene_frame(b - 1e-3, imgs, clip), img, (t - b) / XF)
    if t > TOTAL - 0.5:
        img = Image.blend(img, Image.new("RGB", (W, H), CREAM), (t - (TOTAL - 0.5)) / 0.5)
    return img


def main():
    GEN.mkdir(exist_ok=True)
    imgs = {k: gen_image(k, v) for k, v in IMAGES.items()}
    clip = load_clip()
    if "--preview" in sys.argv:
        for s in sys.argv[sys.argv.index("--preview") + 1].split(","):
            frame(float(s), imgs, clip).save(GEN / f"preview_{s}.png")
        return
    audio = build_audio()
    w = imageio_ffmpeg.write_frames(str(OUT), (W, H), fps=FPS, codec="libx264", pix_fmt_out="yuv420p", quality=8,
                                    audio_path=str(audio), audio_codec="aac", macro_block_size=8)
    w.send(None)
    for i in range(int(TOTAL * FPS)):
        w.send(np.asarray(frame(i / FPS, imgs, clip)).tobytes())
    w.close()
    print("saved", OUT)


if __name__ == "__main__":
    main()
