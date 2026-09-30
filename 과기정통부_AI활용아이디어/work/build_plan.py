"""기획서 서식(hwpx)의 스타일·첫 문단(secPr)을 그대로 두고 본문만 plan_content로 교체 → 기획서_filled.hwpx.
서식 권장값(12pt·160%)용 글자/문단 모양은 기존 모양을 복사해 header.xml에 추가한다."""
import re
from html import escape
from PIL import Image
from pyhwpxlib.api import insert_image_to_existing
from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive
import plan_content as C

SRC, TMP, OUT = "기획서.hwpx", "기획서_tmp.hwpx", "기획서_filled.hwpx"
FIGS = {"@FIG1": "../../docs/PolaGrid_시제품.png", "@FIG2": "fig_scale.png"}
FULL_W = 48528  # 본문 폭(서식 lineseg horzsize)


# 1) 그림 두 장을 문서 끝에 붙여 두고, 나중에 해당 문단을 잘라 제자리로 옮긴다
path = SRC
for n, (key, img) in enumerate(FIGS.items()):
    w, h = Image.open(img).size
    width = FULL_W if key == "@FIG1" else int(FULL_W * 0.92)
    path = insert_image_to_existing(path, img, f"{n}_{TMP}", width=width, height=int(width * h / w))

arch = read_zip_archive(path)
sec = arch.files["Contents/section0.xml"].decode("utf-8")
hdr = arch.files["Contents/header.xml"].decode("utf-8")


def top_paras(s):
    """최상위 <hp:p> 구간 목록."""
    out, i = [], s.index(">", s.index("<hs:sec")) + 1
    while (j := s.find("<hp:p ", i)) >= 0:
        d = 0
        for t in re.finditer(r"<hp:p |</hp:p>", s[j:]):
            d += 1 if t.group(0) == "<hp:p " else -1
            if d == 0:
                out.append(s[j:j + t.end()]); i = j + t.end(); break
    return out


paras = top_paras(sec)
first, title_t, sub_t, head_t = paras[0], paras[35], paras[36], paras[37]
pics = [p for p in paras if "<hp:pic" in p]
assert len(pics) == 2, len(pics)
# 그림 문단은 가운데 정렬(paraPr 10 = CENTER)
pics = [re.sub(r'paraPrIDRef="\d+"', 'paraPrIDRef="10"', p, count=1) for p in pics]

# 2) 12pt 본문/굵게/주석용 글자 모양, 160% 양쪽정렬 문단 모양 추가
n_char = int(re.search(r'<hh:charProperties itemCnt="(\d+)"', hdr).group(1))
n_para = int(re.search(r'<hh:paraProperties itemCnt="(\d+)"', hdr).group(1))
c0 = re.search(r'<hh:charPr id="0".*?</hh:charPr>', hdr, re.S).group(0)
body_c = c0.replace('id="0"', f'id="{n_char}"').replace('height="1050"', 'height="1200"')
bold_c = body_c.replace(f'id="{n_char}"', f'id="{n_char + 1}"').replace("<hh:underline", "<hh:bold/><hh:underline")
note_c = c0.replace('id="0"', f'id="{n_char + 2}"').replace('height="1050"', 'height="900"').replace('textColor="#000000"', 'textColor="#595959"')
hdr = hdr.replace("</hh:charProperties>", body_c + bold_c + note_c + "</hh:charProperties>")
hdr = hdr.replace(f'<hh:charProperties itemCnt="{n_char}"', f'<hh:charProperties itemCnt="{n_char + 3}"')
p9 = re.search(r'<hh:paraPr id="9".*?</hh:paraPr>', hdr, re.S).group(0)
body_p = (p9.replace('id="9"', f'id="{n_para}"').replace('horizontal="LEFT"', 'horizontal="JUSTIFY"')
          .replace('value="115"', 'value="160"').replace('<hc:next value="1600"', '<hc:next value="600"'))
hdr = hdr.replace("</hh:paraProperties>", body_p + "</hh:paraProperties>")
hdr = hdr.replace(f'<hh:paraProperties itemCnt="{n_para}"', f'<hh:paraProperties itemCnt="{n_para + 1}"')
BODY, BOLD, NOTE, PARA = n_char, n_char + 1, n_char + 2, n_para


def strip_lineseg(p):
    return re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", p, flags=re.S)


def retext(p, text):
    """문단 템플릿의 유일한 <hp:t> 내용을 교체."""
    assert p.count("<hp:t>") == 1
    return strip_lineseg(re.sub(r"<hp:t>[^<]*</hp:t>", f"<hp:t>{escape(text, quote=False)}</hp:t>", p))


def body(text):
    char = NOTE if text.startswith("@NOTE") else None
    text = text.removeprefix("@NOTE")
    runs = []
    for k, part in enumerate(re.split(r"\*\*", text)):
        if part:
            cid = char or (BOLD if k % 2 else BODY)
            runs.append(f'<hp:run charPrIDRef="{cid}"><hp:t>{escape(part, quote=False)}</hp:t></hp:run>')
    return (f'<hp:p id="0" paraPrIDRef="{PARA}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            + "".join(runs) + "</hp:p>")


# 3) 본문 조립: 첫 문단(secPr 포함)의 윗줄 문구만 교체 → 제목 → 부제 → 섹션
first = strip_lineseg(first.replace("'매일 쓰는 생활 속 AI' AI 활용 아이디어 공모전", escape(C.TOP, quote=False)))
out = [first, retext(title_t, C.TITLE), retext(sub_t, C.SUBTITLE)]
for head, paras_ in C.SECTIONS:
    out.append(retext(head_t, head))
    for t in paras_:
        out.append(pics[0] if t == "@FIG1" else pics[1] if t == "@FIG2" else body(t))

start = sec.index(paras[0])
end = sec.rindex("</hs:sec>")
sec = sec[:start] + "".join(out) + sec[end:]

arch.files["Contents/section0.xml"] = sec.encode("utf-8")
arch.files["Contents/header.xml"] = hdr.encode("utf-8")
write_zip_archive(OUT, arch)
print("ok", OUT)
