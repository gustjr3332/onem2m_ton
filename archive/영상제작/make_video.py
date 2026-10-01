"""PolaGrid 시연 영상(모션그래픽) 생성: PIL로 프레임을 그려 ffmpeg(imageio-ffmpeg)로 MP4 인코딩.
구성: 타이틀 → 1. 작동 원리 → 2. 필요한 곳 → 3. 1칸~1,000칸 → 마무리.
사용: python make_video.py [출력.mp4] [--preview 초,초,...]  (preview는 해당 시각 PNG만 저장)"""
import math
import sys
from functools import lru_cache

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

W, H, K, FPS = 1280, 720, 2, 30          # 논리 좌표 1280x720, 2배로 그려 축소(안티앨리어싱)
CREAM, NAVY, SAND, DARK = (251, 248, 241), (31, 78, 121), (246, 211, 154), (38, 62, 92)
SUN, GLARE, GREY, INK = (232, 163, 61), (255, 236, 150), (120, 128, 138), (27, 42, 58)


@lru_cache(None)
def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf", int(size * K))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    """t가 a→b 구간을 지날 때 0→1 (부드럽게)."""
    return ease((t - a) / (b - a))


def mix(c1, c2, a):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


class D:
    """논리 좌표로 그리는 ImageDraw 래퍼."""

    def __init__(self, img):
        self.d = ImageDraw.Draw(img)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1, r=0):
        box = [x0 * K, y0 * K, x1 * K, y1 * K]
        if r:
            self.d.rounded_rectangle(box, r * K, fill=fill, outline=outline, width=int(width * K))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(width * K))

    def line(self, pts, fill, width=2):
        self.d.line([(x * K, y * K) for x, y in pts], fill=fill, width=int(width * K), joint="curve")

    def circle(self, x, y, r, fill=None, outline=None, width=1):
        self.d.ellipse([(x - r) * K, (y - r) * K, (x + r) * K, (y + r) * K], fill=fill, outline=outline, width=int(width * K))

    def poly(self, pts, fill):
        self.d.polygon([(x * K, y * K) for x, y in pts], fill=fill)

    def text(self, x, y, s, size, fill=INK, bold=False, anchor="la"):
        self.d.text((x * K, y * K), s, font=font(size, bold), fill=fill, anchor=anchor)


# ---------- 공통 그림 요소 ----------

def star(o, x, y, r, a):
    """눈부심 표시(빛 번짐). a=0이면 안 보임."""
    if a <= 0.01:
        return
    for k in range(5, 0, -1):
        o.circle(x, y, r * k / 5 * 1.6, fill=GLARE + (int(40 * a),))
    o.circle(x, y, r * 0.45, fill=(255, 250, 220, int(230 * a)))
    for ang in range(0, 360, 45):
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        o.line([(x + dx * r * 0.5, y + dy * r * 0.5), (x + dx * r * 1.5, y + dy * r * 1.5)], (255, 220, 120, int(200 * a)), 2)


def sun(b, o, x, y, r=34):
    for k in range(4, 0, -1):
        o.circle(x, y, r * (1 + k * 0.35), fill=SUN + (28,))
    b.circle(x, y, r, fill=SUN)


def grid(b, x, y, cols, rows, cell, dark, gap=None, frame=True):
    """편광 모듈 격자. dark(c, r) → 0(열림)~1(닫힘). 칸 좌표 dict 반환."""
    gap = gap if gap is not None else max(1, cell * 0.08)
    if frame:
        b.rect(x - gap * 2, y - gap * 2, x + cols * cell + gap * 2, y + rows * cell + gap * 2, outline=NAVY, width=max(2, cell * 0.06))
    centers = {}
    for r in range(rows):
        for c in range(cols):
            x0, y0 = x + c * cell + gap / 2, y + r * cell + gap / 2
            b.rect(x0, y0, x0 + cell - gap, y0 + cell - gap, fill=mix(SAND, DARK, clamp(dark(c, r))))
            centers[(c, r)] = (x0 + (cell - gap) / 2, y0 + (cell - gap) / 2)
    return centers


def beam(o, p0, p1, width, a, color=SUN):
    if a <= 0.01:
        return
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    o.poly([(x0 + nx * width, y0 + ny * width), (x0 - nx * width, y0 - ny * width), (x1, y1)], color + (int(110 * a),))


def person(b, x, y, s=1.0, color=GREY):
    b.circle(x, y, 18 * s, fill=color)
    b.rect(x - 22 * s, y + 24 * s, x + 22 * s, y + 90 * s, fill=color, r=14 * s)


# ---------- 장면 ----------
# 각 장면: (길이초, 그리기함수(b, o, t), 자막함수(t) 또는 None)

def s_title(b, o, t):
    a = ramp(t, 0, 0.8)
    grid(b, 560, 150, 4, 3, 40, lambda c, r: ramp(t, 1.2, 2.2) if (c == 3 and r < 2) else 0)
    b.text(640, 360, "PolaGrid", 72, mix(CREAM, NAVY, a), True, "mm")
    b.text(640, 430, "눈부심만 골라 줄이는 AI 편광 창", 30, mix(CREAM, INK, a), False, "mm")
    b.text(640, 480, "'매일 쓰는 생활 속 AI' AI 활용 아이디어 공모전 · 아이디어 기획 분야", 18, mix(CREAM, GREY, a), False, "mm")


def section(num, title, sub):
    def f(b, o, t):
        a = ramp(t, 0, 0.5)
        b.rect(0, 0, W, H, fill=mix(CREAM, NAVY, a))
        b.text(640, 320, num, 36, mix(NAVY, SAND, a), True, "mm")
        b.text(640, 385, title, 46, mix(NAVY, (255, 255, 255), a), True, "mm")
        b.text(640, 445, sub, 22, mix(NAVY, (205, 218, 232), a), False, "mm")
    return f


def room_side(b, o, t, blinds):
    """옆에서 본 방: 창·해·책상·사람."""
    dim = 0.45 * blinds
    b.rect(0, 0, W, H, fill=mix(CREAM, (70, 78, 92), dim))
    b.line([(0, 560), (W, 560)], NAVY, 3)
    sun(b, o, 140, 140)
    b.rect(330, 180, 342, 470, fill=NAVY)                       # 창
    for i in range(int(blinds * 10)):                           # 블라인드
        b.rect(346, 186 + i * 28, 372, 204 + i * 28, fill=DARK)
    b.rect(620, 500, 920, 514, fill=(140, 110, 80))              # 책상
    b.rect(700, 490, 790, 500, fill=(255, 255, 255))             # 노트
    b.line([(900, 514), (900, 560)], (140, 110, 80), 6)
    person(b, 1010, 370, 1.3)
    return (745, 494)


def s_problem(b, o, t):
    blinds = ramp(t, 5.0, 6.5)
    spot = room_side(b, o, t, blinds)
    grow = ramp(t, 0.3, 1.8)
    a = 1 - blinds
    beam(o, (140, 140), (140 + (spot[0] - 140) * grow, 140 + (spot[1] - 140) * grow), 30, a)
    if t > 1.8:
        g = ramp(t, 1.8, 2.8)
        o.line([spot, (spot[0] + (995 - spot[0]) * g, spot[1] + (360 - spot[1]) * g)], SUN + (int(230 * a),), 6)
        star(o, *spot, 30 + 6 * math.sin(t * 6), a * ramp(t, 1.8, 2.4))
        if t > 2.8 and a > 0.5:
            b.text(1010, 300, "눈이 부셔서 글자가 안 보여요", 18, INK, True, "mm")
    if blinds > 0.5:
        b.text(640, 110, "블라인드를 내리면 → 방 전체가 어두워지고 창밖도 안 보인다", 24, (255, 255, 255), True, "mm")


def cap_problem(t):
    return "오후 창가, 책과 화면에 반사된 햇빛이 눈을 부시게 한다" if t < 5 else "그래서 낮에도 조명을 켜고, 해가 움직일 때마다 다시 조작한다"


def polar_theta(t):
    return 90 * ramp(t, 1.5, 4.5) - 45 * ramp(t, 5.5, 7.0)


def film(img, cx, cy, r, theta, tint):
    """편광 필름(원 안의 평행선)을 회전 각도 theta로 그린다."""
    size = int(2 * r * K)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([0, 0, size - 1, size - 1], fill=tint + (215,), outline=NAVY + (255,), width=int(3 * K))
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    for k in range(-6, 7):
        off = k * r * K / 7
        x0, y0 = size / 2 + off * c, size / 2 + off * s
        d.line([(x0 - s * size, y0 + c * size), (x0 + s * size, y0 - c * size)], fill=NAVY + (200,), width=int(2 * K))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    img.alpha_composite(layer, (int((cx - r) * K), int((cy - r) * K)))


def s_polar(b, o, t, img=None):
    th = polar_theta(t)
    T = math.cos(math.radians(th)) ** 2
    b.circle(120, 330, 40, fill=SUN)
    o.rect(160, 300, 380, 360, fill=SUN + (120,))
    o.rect(380, 306, 600, 354, fill=SUN + (110,))
    o.rect(600, 306, 860, 354, fill=SUN + (int(10 + 150 * T),))
    b.rect(860, 230, 880, 430, fill=mix((70, 70, 80), (255, 245, 205), T))   # 스크린
    b.text(380, 180, "고정 편광판", 20, NAVY, True, "mm")
    b.text(600, 180, "회전 편광판", 20, NAVY, True, "mm")
    b.text(600, 490, f"회전 각도 {th:4.0f}°", 26, INK, True, "mm")
    # 통과량 막대
    b.rect(960, 230, 1180, 270, outline=NAVY, width=2)
    b.rect(962, 232, 962 + 216 * T, 268, fill=SUN)
    b.text(1070, 300, f"통과하는 빛 {T * 100:3.0f}%", 24, INK, True, "mm")
    b.text(1070, 340, "0° 밝음 · 45° 절반 · 90° 거의 막음", 16, GREY, False, "mm")
    return th


def cap_polar(t):
    return "두 장의 편광 필름 중 한 장을 돌리면, 통과하는 빛이 각도에 따라 연속으로 줄어든다" if t < 7.5 else "창을 가리지 않고도 밝기와 반사 눈부심을 조절할 수 있다"


def vignette_draw(b, o, t, spec):
    """정면 창 격자 + 대상물. spec: cols, rows, cell, x, y, targets[(cell,(x,y))], objects(b)."""
    t0 = spec.get("t_fix", 2.2)
    fix = ramp(t, t0, t0 + 1.2)
    scan = spec.get("scan", False)
    culprit = {c for c, _ in spec["targets"]}
    dark = lambda c, r: fix if (c, r) in culprit else 0
    centers = grid(b, spec["x"], spec["y"], spec["cols"], spec["rows"], spec["cell"], dark)
    spec["objects"](b)
    if scan and t < t0:                                         # AI 스캔: 칸을 차례로 훑고 원인 칸 표시
        k = int((t - 1.0) * 10) if t > 1.0 else -1
        keys = sorted(centers)
        if 0 <= k < len(keys):
            cx, cy = centers[keys[k]]
            h = spec["cell"] / 2
            b.rect(cx - h, cy - h, cx + h, cy + h, outline=(0, 170, 200), width=4)
    if t > t0 - 0.6:
        for c in culprit:
            cx, cy = centers[c]
            h = spec["cell"] / 2
            b.rect(cx - h - 2, cy - h - 2, cx + h + 2, cy + h + 2, outline=(0, 170, 200), width=3)
    for c, p in spec["targets"]:
        beam(o, centers[c], p, spec["cell"] * 0.35, 1 - fix)
        star(o, *p, 22, 1 - fix)
    if fix > 0.9:
        b.text(spec.get("okx", 1000), spec.get("oky", 150), spec.get("ok", "눈부심 해결 · 방은 그대로 밝음"), 20, NAVY, True, "mm")


def desk_objects(b):
    b.poly([(470, 430), (1050, 430), (1150, 600), (370, 600)], (190, 160, 125))
    b.rect(640, 460, 760, 510, fill=(255, 255, 255))
    b.rect(820, 400, 960, 480, fill=(60, 70, 80))


S_GRID = dict(cols=4, rows=3, cell=95, x=450, y=90, targets=[((3, 0), (700, 485)), ((3, 1), (890, 445))], objects=desk_objects, scan=True, t_fix=4.2, okx=640, oky=40)


def cap_grid(t):
    if t < 1.0:
        return "PolaGrid: 창 안쪽에 편광 모듈을 격자로 붙이고, 칸마다 작은 모터가 각도를 바꾼다"
    if t < 4.2:
        return "AI가 해 위치·칸별 조도·책상 조도로 어느 칸이 눈부심을 만드는지 찾는다"
    return "그 칸만 돌린다. 나머지 칸은 열려 있어 방은 밝고 창밖도 보인다"


def v_home(b):
    b.rect(620, 500, 980, 516, fill=(140, 110, 80)); b.rect(700, 488, 800, 500, fill=(255, 255, 255))
    person(b, 1060, 400, 1.1)


def v_living(b):
    b.rect(640, 330, 900, 480, fill=(40, 45, 55)); b.rect(760, 480, 780, 520, fill=GREY)
    b.rect(930, 470, 1180, 540, fill=(170, 120, 110), r=16); person(b, 1060, 400, 1.1, (150, 150, 160))


def v_class(b):
    for r in range(2):
        for c in range(4):
            x, y = 560 + c * 170, 440 + r * 120
            b.rect(x, y, x + 120, y + 14, fill=(140, 110, 80)); person(b, x + 60, y - 70, 0.6)


def v_office(b):
    for c in range(4):
        x = 520 + c * 180
        b.rect(x, 360, x + 120, 440, fill=(50, 60, 72)); b.rect(x - 10, 460, x + 140, 474, fill=(150, 150, 150)); person(b, x + 60, 490, 0.7)


def vign(label, need, spec):
    def f(b, o, t):
        b.rect(0, 0, W, H, fill=CREAM)
        b.text(60, 60, label, 34, NAVY, True)
        b.text(60, 110, need, 20, INK)
        vignette_draw(b, o, t, dict(spec, t_fix=2.2, okx=900, oky=660))
    return f


VIGN = [
    ("가정 · 공부방", "오후 햇빛이 노트에 반사 → 해당 칸만 회전",
     dict(cols=3, rows=4, cell=80, x=110, y=200, targets=[((2, 0), (750, 492))], objects=v_home)),
    ("가정 · 거실의 어르신", "TV 화면 반사 → 블라인드를 직접 만지지 않아도 자동 조절",
     dict(cols=3, rows=4, cell=80, x=110, y=200, targets=[((2, 1), (720, 380)), ((2, 2), (820, 420))], objects=v_living)),
    ("학교 · 교실", "자리마다 눈부심이 달라도 칸별로 따로 조절",
     dict(cols=4, rows=5, cell=70, x=80, y=180, targets=[((3, 0), (620, 440)), ((3, 1), (960, 440)), ((2, 2), (790, 560))], objects=v_class)),
    ("사무실 · 도서관", "모니터·열람석 반사를 줄이고 조명·블라인드 조작은 줄인다",
     dict(cols=4, rows=5, cell=70, x=80, y=180, targets=[((3, 0), (580, 400)), ((3, 1), (940, 400)), ((3, 2), (1120, 400))], objects=v_office)),
]


def facade_dark(cols, rows, t):
    """해가 움직이며 어두운 띠가 대각선으로 지나가는 패턴."""
    ph = (t * 0.12) % 1.4 - 0.2
    return lambda c, r: clamp(1 - abs((c / max(cols - 1, 1)) * 0.8 + (r / max(rows - 1, 1)) * 0.3 - ph) * 5)


STAGES = [(1, 1, "1칸", "모듈 한 칸"), (4, 3, "12칸", "공부방 창 1개"), (10, 10, "100칸", "교실·도서관 한 층"), (40, 25, "1,000칸", "학교·공공건물 전체")]


def s_scale(b, o, t):
    b.rect(0, 0, W, H, fill=CREAM)
    k = min(int(t / 2.6), 3)
    cols, rows, num, what = STAGES[k]
    a = ramp(t - k * 2.6, 0, 0.5)
    cell = min(900 / cols, 400 / rows)
    gx, gy = 640 - cols * cell / 2, 130 + (400 - rows * cell) / 2
    grid(b, gx, gy, cols, rows, cell, facade_dark(cols, rows, t + 2), frame=True)
    b.text(640, 70, num, 48, mix(CREAM, NAVY, a), True, "mm")
    b.text(640, 580, what, 26, mix(CREAM, INK, a), True, "mm")


def s_server(b, o, t):
    b.rect(0, 0, W, H, fill=(18, 36, 56))
    cols, rows, cell = 40, 25, 13
    gx, gy = 640 - cols * cell / 2, 40
    sx = 200 + 880 * ramp(t, 0, 9)
    sun(b, o, sx, 22, 16)
    ph = ramp(t, 0, 9)
    grid(b, gx, gy, cols, rows, cell, lambda c, r: clamp(1 - abs(c / 39 * 0.8 + r / 24 * 0.3 - (ph * 1.2 - 0.1)) * 5), gap=2)
    # 구역 4개 → 서버
    zones = [gx + cols * cell * (i + 0.5) / 4 for i in range(4)]
    b.rect(440, 470, 840, 550, fill=NAVY, r=14)
    b.text(640, 497, "AI 제어 서버 + 표준 IoT 플랫폼", 22, (255, 255, 255), True, "mm")
    b.text(640, 528, "칸별 각도 예측 → 구역 단위로 한 번에 명령", 16, (205, 218, 232), False, "mm")
    for i, zx in enumerate(zones):
        b.line([(640, 470), (zx, gy + rows * cell + 36)], (90, 130, 170), 2)
        p = ((t * 0.9 + i * 0.25) % 1.0)
        px, py = 640 + (zx - 640) * p, 470 + (gy + rows * cell + 36 - 470) * p
        b.circle(px, py, 6, fill=SAND)
        b.text(zx, gy + rows * cell + 22, f"구역 {i + 1}", 14, (205, 218, 232), False, "mm")
    if t > 3:
        b.text(640, 610, "가상 1,000칸 등록·기록 부하 실험: 실패 0건", 22, SAND, True, "mm")


def s_outro(b, o, t):
    a = ramp(t, 0, 0.8)
    grid(b, 560, 170, 4, 3, 40, lambda c, r: 1 if (c == 3 and r < 2) else 0)
    b.text(640, 370, "PolaGrid", 64, mix(CREAM, NAVY, a), True, "mm")
    b.text(640, 435, "창을 가리지 않고, 눈부심만.", 30, mix(CREAM, INK, a), False, "mm")
    b.text(640, 490, "방 한 칸에서 건물 수천 칸까지", 22, mix(CREAM, GREY, a), False, "mm")
    b.text(640, 680, "※ 본 영상은 Claude(생성형 AI)로 코드를 작성해 만든 모션그래픽이며, 수치는 팀이 직접 측정·검증함", 14, mix(CREAM, GREY, a), False, "mm")


SCENES = [
    (4.5, s_title, None),
    (2.5, section("1", "편광창의 작동 원리", "창을 가리지 않고 빛을 줄이는 방법"), None),
    (8.0, s_problem, cap_problem),
    (10.0, "polar", cap_polar),
    (9.0, lambda b, o, t: (b.rect(0, 0, W, H, fill=CREAM), vignette_draw(b, o, t, S_GRID)), cap_grid),
    (2.5, section("2", "어디에 필요한가", "가정에서 학교·사무실까지"), None),
    *[(5.5, vign(*v), None) for v in VIGN],
    (2.5, section("3", "1칸에서 1,000칸까지", "칸 수가 늘어도 같은 방식으로"), None),
    (10.4, s_scale, lambda t: "칸 하나하나가 개별 기기 — 공부방 창 하나부터 건물 전체까지 같은 방식으로 늘어난다"),
    (10.0, s_server, lambda t: "해가 움직이면 구역별 칸이 함께 회전한다. 제어 서버와 앱은 규모와 상관없이 그대로"),
    (5.5, s_outro, None),
]


def render(t_global):
    acc = 0
    for dur, fn, cap in SCENES:
        if t_global < acc + dur or (dur, fn, cap) == SCENES[-1]:
            t = t_global - acc
            break
        acc += dur
    base = Image.new("RGB", (W * K, H * K), CREAM)
    over = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
    b, o = D(base), D(over)
    if fn == "polar":
        th = s_polar(b, o, t)
        base = base.convert("RGBA")
        film(base, 380, 330, 100, 90, (235, 240, 246))
        film(base, 600, 330, 100, 90 + th, SAND)
    else:
        fn(b, o, t)
        base = base.convert("RGBA")
    img = Image.alpha_composite(base, over).convert("RGB")
    if cap:
        d = D(img)
        d.rect(0, H - 64, W, H, fill=(20, 32, 46))
        d.text(W / 2, H - 32, cap(t), 22, (255, 255, 255), False, "mm")
    # 장면 전환 페이드
    fade = clamp(min(t / 0.35, (dur - t) / 0.35))
    img = img.resize((W, H), Image.LANCZOS)
    if fade < 1:
        img = Image.blend(Image.new("RGB", (W, H), CREAM), img, fade)
    return img


if __name__ == "__main__":
    total = sum(s[0] for s in SCENES)
    if "--preview" in sys.argv:
        for s in sys.argv[sys.argv.index("--preview") + 1].split(","):
            render(float(s)).save(f"prev_{float(s):05.1f}.png")
        sys.exit()
    out = sys.argv[1] if len(sys.argv) > 1 else "PolaGrid_시연영상.mp4"
    w = imageio_ffmpeg.write_frames(out, (W, H), fps=FPS, codec="libx264", pix_fmt_out="yuv420p", quality=8, macro_block_size=8)
    w.send(None)
    n = int(total * FPS)
    for i in range(n):
        w.send(np.asarray(render(i / FPS)).tobytes())
        if i % 300 == 0:
            print(f"{i}/{n}", flush=True)
    w.close()
    print("done", out, f"{total:.1f}s")
