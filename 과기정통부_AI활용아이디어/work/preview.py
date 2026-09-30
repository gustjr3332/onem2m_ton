"""hwpx -> 페이지별 PNG (resvg, Windows 시스템 폰트 사용). 사용: python preview.py file.hwpx prefix"""
import sys
import resvg_py
from pyhwpxlib.rhwp_bridge import RhwpEngine

src, prefix = sys.argv[1], sys.argv[2]
doc = RhwpEngine().load(src)
for i in range(doc.page_count):
    svg = doc.render_page_svg(i)
    png = resvg_py.svg_to_bytes(svg_string=svg, zoom=1.5, background="white",
                                font_family="Malgun Gothic", sans_serif_family="Malgun Gothic",
                                serif_family="Batang")
    open(f"{prefix}_p{i}.png", "wb").write(bytes(png))
print(doc.page_count, "pages")
