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

## 다음 할 일

- 각 MN 아래 장치 AE 구조 설계 (센서/액추에이터 종류·개수)
- MQTT 기반 제어 명령 흐름 (IN → MN → AE) 정의
- upstream 버그 2건 이슈/PR 여부 결정
