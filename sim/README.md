# polargrid — oneM2M 다중 제어 개발 환경

tinyIoT(oneM2M CSE) 기반으로 중앙 서버(IN-CSE) 1개 + 현장 노드(MN-CSE) N개를 MQTT로 묶는 개발/시뮬레이션 환경.

## 구성 (WSL Ubuntu 24.04)

| 역할 | 위치 | 포트 | DB | CSE ID |
|---|---|---|---|---|
| IN-CSE | `~/tinyIoT/source/server` | 3000 | PostgreSQL 16 `tinydb` | `/tinyiot` |
| MN-CSE (단일, 수동) | `~/tinyIoT-mn/source/server` | 3001 | PostgreSQL `tinydb_mn` | `/id-mn` |
| MN-CSE ×N (생성) | `~/polargrid/nodes/mnXXX` | 3001~3000+N | SQLite (`data.db`) | `/id-mnXXX` |
| MQTT 브로커 | mosquitto | 1883 | – | – |

주의: 단일 MN(`~/tinyIoT-mn`)과 생성 노드 mn001은 둘 다 3001을 쓰므로 동시에 띄우지 않는다.

## 사용법

`.build`에는 `patches/`의 4개(콤마 누락, fopt 알림, WAL, TEXT 버퍼 넘침)가 모두 적용돼 있다. 새로 만들 때는 `~/tinyIoT/source/server` 사본에 `patch -p3 < patches/<파일>`을 차례로 적용한 뒤 `gen_nodes.sh`. IN이 먼저 떠 있어야 MN이 등록된다(`tools/run_in.sh`).

```bash
cd ~/tinyIoT/source/server && ./server      # 1) IN 먼저
cd ~/polargrid   # 이 저장소의 sim/ 내용을 ~/polargrid 로 복사해 사용
./gen_nodes.sh 100                          # 2) 노드 생성 (약 1분, ~/tinyIoT config.h 기반)
./nodes.sh start [N]                        # 3) 노드 실행
./nodes.sh status                           #    실행 수 / 메모리
./nodes.sh stop
```

## 검증 결과 (2026-09-29, LG gram i7-1195G7 / WSL 7.8GB)

- 100/100 노드 HTTP 응답, IN에 CSR 100개 등록
- 브로커 연결 101개, MQTT 요청/응답 성공 (`/oneM2M/req/Ctest/id-mn050/json` → rsc 2000)
- 100노드 RSS 합계 541MB, load avg 0.4, 오류 로그 0건

## 설정 변경 내역

- `config.h` (IN): `SERVER_TYPE IN_CSE` (기존 `IN_CSE or MN-CSE` 문법 오류 수정), `ENABLE_MQTT` 활성화, `MQTT_CLIENT_ID "tinyiot"`, `ALLOWED_REMOTE_CSE_ID "/*"`
- 노드: `MN_CSE`, `DB_SQLITE`(PostgreSQL 기본 max_connections 100 초과 회피), `MQTT_CLIENT_ID "id-mnXXX"`(ID 중복 시 브로커가 기존 연결을 끊음), `LOG_LEVEL_INFO`
- IN `defaultACP`: `acor ["/id-in","/id-mn"]` → `["/*"]` (oneM2M PUT으로 변경). ACP는 최초 생성 시 DB에 저장되므로 config 변경만으로는 반영되지 않음
- PostgreSQL: 22.04(PG14) → 24.04(PG16) 이전, `pg_dumpall` 복원, `tinyuser` 비밀번호 재설정(PG16 scram)

## 발견한 upstream 버그 (seslabSJU/tinyIoT @ 832205f)

1. `sqlite_implement.c:196` fcnt 스키마 항목 뒤 콤마 누락 → `DB_SQLITE` 빌드 실패. `~/polargrid/.build` 사본에만 패치
2. MN이 원격 CSE 조회에서 403을 받으면 `Remote CSE is not online : 403` 로그 후 segfault
3. GRP `fopt`로 멤버에 자원을 만들면 그 멤버의 SUB 알림이 나가지 않음(`onem2m.c` fan-out 루프가 `notify_via_sub`를 안 부름). `patches/fopt-member-notify.patch`로 `.build` 사본에만 수정
4. 멤버 100개인 GRP가 DB에 있으면 재시작 시 `*** stack smashing detected ***`로 종료. 원인: `sqlite_implement.c` `db_get_all_resource_as_rtnode()`(:1019, :1046, :1093)가 TEXT 열을 `char buf[256]`에 길이 제한 없이 `strncpy`. 같은 패턴이 7곳(:394/410, :489/505, :1019/1046/1093, :1235/1272, :1314/1368, :2354/2375). 256바이트를 넘는 모든 TEXT(`mid`·`acpi`·`nu`·`poa`·`lbl`·`dcse`·CIN `con`)가 메모리를 덮고, 2,312바이트를 넘으면 크래시(멤버 id 25자 기준 83개부터, 82개는 통과). CIN `con` 3,000바이트도 재시작 크래시 확인. `patches/grp-mid-overflow.patch`(13 hunk, 복사 대신 sqlite 행 포인터 사용)로 수정, `~/grp_debug`에서 ASan·멤버 100/300개·재시작 검증. 10-01 `.build`에 적용, MN 100개 재빌드. 멤버 100개 GRP가 든 DB로 재시작 2회 정상. 크래시 DB는 `~/polargrid/db_backup/`
5. GRP `fopt` 응답이 64KB(`httpd.c` `BUF_SIZE`)를 넘으면(멤버 약 150개 이상) 잘린 본문을 전체 Content-Length로 보냄. 미수정

## 성능 패치

- `patches/sqlite-wal-normal.patch`: SQLite를 `journal_mode=WAL`, `synchronous=NORMAL`로 연다(트랜잭션 시작 전). 운영 처리량 69 → 577 req/s(칸 1,000개, CIN 3,000건). 앱 크래시에는 안전, 전원 차단 시 마지막 커밋 일부 유실 가능. 측정 결과는 `docs/PolaGrid_개발.md` 0-4c

## 다음 할 일

- 각 MN 아래 장치 AE 구조 설계 (센서/액추에이터 종류·개수)
- MQTT 기반 제어 명령 흐름 (IN → MN → AE) 정의
- upstream 버그 2건 이슈/PR 여부 결정
