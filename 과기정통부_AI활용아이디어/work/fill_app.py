"""참가 신청서 hwpx 채우기: unpack된 app_x/ 의 section0.xml 원문 문자열 치환 → 신청서_filled.hwpx.
개인정보 칸(성명·생년월일·연락처·이메일·주소·팀원·참가구분·동의·서명·날짜)은 비워 둔다."""
import re
from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

TITLE = "PolaGrid: 방 한 칸에서 건물 수천 칸까지, 눈부심만 골라 줄이는 AI 편광 창"
SUMMARY = (
    "오후 창가에서 공부하거나 일하면 책과 화면에 햇빛이 반사되어 눈이 부시지만, 블라인드를 내리면 방이 어두워져 "
    "낮에도 조명을 켜게 된다. PolaGrid는 창 안쪽에 편광 필름 모듈을 격자로 붙이고, AI가 눈부심을 만드는 칸만 골라 "
    "각도를 돌려 창밖은 보이는 채로 눈부심만 줄이는 서비스다. AI는 시간대·바깥 밝기·계절별로 쌓인 기록에서 칸마다 "
    "알맞은 각도를 예측하고, 사용자가 앱에서 고친 밝기를 학습해 다음 날부터 반영한다. 칸 하나하나를 개별 기기로 "
    "등록하고 제어 서버가 구역 단위로 명령을 한 번에 보내므로, 공부방 창 하나부터 학교·도서관·공공건물의 창 수천 "
    "칸까지 같은 방식으로 늘릴 수 있다. 편광 회전 장치는 2025년 수업 프로젝트에서 만들어 동작을 확인했고, 가상 "
    "1,000칸을 표준 IoT 플랫폼에 등록·기록하는 부하 실험에서 실패 0건을 확인했다."
)
assert len(SUMMARY) <= 500, len(SUMMARY)

arch = read_zip_archive("신청서.hwpx")
key = "Contents/section0.xml"
s = arch.files[key].decode("utf-8") if isinstance(arch.files[key], bytes) else arch.files[key]


def sub1(old, new):
    global s
    assert s.count(old) == 1, (old[:60], s.count(old))
    s = s.replace(old, new)


# 1) 응모 분야: ① 아이디어 기획 선택
sub1("<hp:t>☐ ① 아이디어 기획", "<hp:t>☑ ① 아이디어 기획")

# 2) 작품명: '작품명(제목)' 다음 첫 빈 값 셀(<hp:t> </hp:t>)
i = s.index("작품명(제목)")
j = s.index("<hp:t> </hp:t>", i)
s = s[:j] + f"<hp:t>{TITLE}</hp:t>" + s[j + len("<hp:t> </hp:t>"):]

# 3) 작품 개요: 개요 표 안 첫 빈 문단. 글꼴은 값 칸과 같은 charPr 17, lineseg는 한컴이 다시 계산하도록 제거
i = s.index("3. 작품 개요")
m = re.compile(r'<hp:run charPrIDRef="0"><hp:t/></hp:run><hp:linesegarray>.*?</hp:linesegarray>').search(s, i)
s = s[:m.start()] + f'<hp:run charPrIDRef="17"><hp:t>{SUMMARY}</hp:t></hp:run>' + s[m.end():]
# 개요 문단 줄간격 100% → 160% 양쪽정렬(paraPr 34, 서식에 이미 있는 스타일)
p = s.rindex('paraPrIDRef="33"', i, m.start())
s = s[:p] + 'paraPrIDRef="34"' + s[p + len('paraPrIDRef="33"'):]

# 4) 제출 서류: 신청서·기획서만 체크
sub1("<hp:t>☐ 참가 신청서 1부", "<hp:t>☑ 참가 신청서 1부")
sub1("<hp:t>☐ (별첨) 기획서", "<hp:t>☑ (별첨) 기획서")

arch.files[key] = s.encode("utf-8")
write_zip_archive("신청서_filled.hwpx", arch)
print("ok", len(SUMMARY), "자")
