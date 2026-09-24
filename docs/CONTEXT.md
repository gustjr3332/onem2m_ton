# EdgePdM — 프로젝트 도메인 모델

> 이 파일은 프로젝트의 용어, 개념, 핵심 결정을 기록합니다. 구현이 아니라 *설계의 의도*를 담고 있습니다.

## 1. 핵심 용어

### EdgePdM (서비스)
회전 설비(모터, 팬, 컨베이어 드라이브)의 고장을 미리 감지하는 머신러닝 기반 시스템.
- **엣지**: 설비 근처의 컴퓨터에서 실시간 추론
- **PdM**: Predictive Maintenance (예지보전)

### 프로젝트 목표
2026 oneM2M 국제 개발자 공모전 출품이 이 프로젝트의 유일한 목표다.

| | 값 |
|---|---|
| **기간** | 7주 (10/5~11/20) |
| **출처** | oneM2M 국제 개발자 대회 |
| **기술 스택** | oneM2M + ETSI MEC |
| **코드 기반** | 1개 저장소 (onem2m_ton/) |
| **시나리오** | 팩토리 + 물류 이중 배포 |
| **평가 기준** | oneM2M/MEC 표준 활용, 생태계 기여 |

**전략**: oneM2M + MEC 생태계 기여를 강조하는 단일 코드베이스로 진행.

### 시나리오 (Scenario)
EdgePdM을 어느 산업 현장에 배포하는가를 정의.

**스마트팩토리**
- 장비: 생산라인 컨베이어 모터, 냉각팬
- 고장의 영향: 라인 전체 정지 → 생산 손실 (비용 큼)
- 알림 대상: 해당 라인의 정비사 (위치 고정)
- 대응: 라인 정지 또는 자동 감속

**스마트물류**
- 장비: 창고 분류기 컨베이어, AGV 드라이브 모터
- 고장의 영향: 소포 오정렬, 배송 지연 → 고객 만족도 (시간 비용)
- 알림 대상: 순회 정비사, 창고 관리자 (위치 변함 → MEC Location API 필요)
- 대응: 자동 감속 또는 우회 경로 전환

**코드 관점**: SITE_TYPE (factory / logistics) 환경변수로 전환.
- 리소스 트리: `/pdm/site/{siteType}_{location_id}/motor{N}/...`
- 알림 로직: siteType별 수신자, 액션 다름

### 기술 스택의 선택

**OneM2M (표준 IoT 플랫폼)**
- 용도: 센서 데이터, 추론 결과, 명령(command)을 표준 리소스로 저장/교환
- 유형: 공개 표준 (ETSI, TTA, 3GPP 공동 개발)
- 역할: **신뢰할 수 있는 데이터 저장소** (어떤 애플리케이션이든 쿼리 가능)

**ETSI MEC (엣지 컴퓨팅 플랫폼)**
- 용도: 추론 애플리케이션을 설비 근처에서 실행 (지연 최소화)
- 유형: 표준 컴퓨팅 환경 (Location API, Service Registry 등 제공)
- 역할: **저지연 추론** (클라우드 왕복 지연 없음)

**AWS IoT Core는 왜 안 하나?**
- 해커톤 참가 조건이 oneM2M + ETSI MEC 사용이므로 AWS는 대상이 아님

## 2. 시나리오별 아키텍처

### 공통 계층 (둘 다 같음)
```
[Arduino Uno: 센서 3종]
    ↓ UART
[Edge AE: Python + pyserial]
    ↓ oneM2M HTTP POST
[MN-CSE: tinyIoT or Mobius (Docker)]
    ↓ Subscription/Notification
[MEC Inference App: Docker]
```

### 차이나는 부분 (환경변수로 제어)

| | Factory | Logistics |
|---|---|---|
| SITE_TYPE | "factory" | "logistics" |
| Alert recipient | Line technician (floor:3) | Roaming technician (nearest via Location API) |
| Response action | Stop / slow | Slow / reroute + log |
| Resource path | `/pdm/site/factory_line1/motor{N}` | `/pdm/site/logistics_hub_A/sorter{N}` |
| Benchmark goal | < 100ms latency | < 200ms latency (higher density) |

## 3. 핵심 결정 기록 (ADR)

### ADR-001: 프로젝트를 oneM2M 해커톤 단일 목표로 운영한다

**상태**: Accepted (2026-09-19, 2026-09-17 결정을 대체)

**배경**: 원래 이 프로젝트는 학과 캡스톤(AWS IoT Core 기반)과 oneM2M 해커톤을 같은 코드로 동시에 진행하는 이중 트랙이었다. 이후 캡스톤 병행을 중단하고, oneM2M 국제 개발자 공모전 출품만을 프로젝트의 목표로 확정했다.

**선택**: 기술 스택은 oneM2M + ETSI MEC로 고정. 일정·문서·평가 기준을 모두 해커톤(신청 9/28, 개발 10/5~11/20) 기준으로만 잡는다.

**이유**
- 이중 목표 관리 비용(문서 2벌, 평가 기준 2종)이 1~2인 팀에게 과부하였음
- oneM2M + ETSI MEC 조합은 해커톤 참가 필수 조건이므로 대안 기술 스택 비교가 더 이상 필요 없음

**트레이드오프**
- MEC 플랫폼이 확정되지 않았으므로 킥오프(10/5)까지 불확실성 있음 ← 센서→CSE 부분은 MEC 무관하게 먼저 진행

---

### ADR-002: 두 시나리오를 "환경변수"로 제어한다

**상태**: Accepted (2026-09-17)

**선택지**
1. 팩토리와 물류를 완전히 분리된 애플리케이션으로 빌드
2. 런타임에 SITE_TYPE 환경변수로 제어 (같은 Docker 이미지)

**선택**: 2 (환경변수)

**이유**
- **배포 단순성**: 이미지 1개로 두 현장 모두 지원
- **테스트 효율**: 같은 코드를 2가지 설정으로 테스트하면 버그 겹침 가능성 줄어듦
- **대회 평가**: "다중 산업 지원"이라는 점이 확장성과 재사용성을 보여줄 수 있음

**구현 세부**
- `docker-compose.yml`에서 `SITE_TYPE` 환경변수 선언
- Edge AE에서: 시작 시 siteType 읽고 리소스 트리 경로 설정
- MEC Inference에서: alert recipient, command action을 siteType별로 분기
- 벤치마크 스크립트: 같은 이미지를 SITE_TYPE=factory 설정으로 N번, logistics 설정으로 N번 실행

---

### ADR-003: CSE 구현체는 ACME-oneM2M-CSE 우선 사용

**상태**: Accepted (2026-09-19)

**배경**: 팀은 oneM2M을 이번에 처음 사용함(학부 3학년, 네트워크 기초 지식은 있으나 oneM2M 경험 없음). CSE 후보는 tinyIoT(Node.js), Mobius(Java), ACME-oneM2M-CSE(Python, Andreas Kraft 제작·교육용 설계).

**선택**: ACME-oneM2M-CSE를 우선 시도. 막히는 경우에만 tinyIoT/Mobius 대체 검토.

**이유**
- 팀 기존 스택(Python)과 일치 — Edge AE, MEC Inference도 Python이라 디버깅 시 언어 전환 비용 없음
- 교육용으로 설계되어 문서·튜토리얼이 초심자 친화적
- oneM2M 최초 사용자에게는 언어 학습 곡선까지 겹치면 Week 1 일정이 밀릴 위험이 큼 → 이 리스크를 줄이는 선택

**트레이드오프**
- tinyIoT/Mobius 대비 커뮤니티/레퍼런스 사례가 상대적으로 적을 수 있음 ← 문제 발생 시 Week 0 안에 tinyIoT로 조기 전환 판단

---

## 4. 팀의 전제 조건

- **팀 규모**: 1~2명
- **개발 환경**: Windows 11, Docker Desktop, VSCode
- **배경**: Python, Arduino, Docker 경험 있음
- **외부 의존성**: MEC 플랫폼 환경 (대회에서 제공, 킥오프 확인)

---

## 5. 문서 구조 (이 프로젝트의 규칙)

### 개발 팀이 읽는 문서
- `docs/DEVELOPMENT.md`: 상세 일정, 주차별 목표, 기술 결정
- `docs/ARCHITECTURE.md`: 아키텍처 다이어그램 설명, 리소스 트리
- `firmware/README.md`: 센서 핀맵, 펌웨어 빌드 방법
- `edge-ae/README.md`: ADN-AE 설치, oneM2M 리소스 생성 예제
- `mec-inference/README.md`: MEC 추론 앱 빌드, Mp1 서비스 등록

### 대회에 제출하는 문서
- `APPLICATION.md` (또는 제출 폼): 영문 신청서 (Service Overview, Implementation, Team Capability, Expected Effects)
- `docs/TUTORIAL-FACTORY.md`: 팩토리 배포 가이드 (영문, CC BY 4.0)
- `docs/TUTORIAL-LOGISTICS.md`: 물류 배포 가이드 (영문, CC BY 4.0)
- `docs/BENCHMARK-RESULTS.md`: MEC vs Cloud 성능 비교 (영문)

---

## 6. 진행 상황

**현재** (2026-09-17)
- ✅ 아이디어 정의 (EdgePdM 서비스)
- ✅ 시나리오 정의 (팩토리 + 물류)
- ✅ 기술 스택 선택 (oneM2M + MEC)
- ✅ 핵심 결정 기록 (ADR-001~003)
- ✅ 문서 정리 (CONTEXT/APPLICATION을 docs/로 이동, 중복 문서 삭제)
- ✅ 다이어그램 2종 (MVP 아키텍처, 7주 로드맵)
- ✅ 해커톤 단일 트랙으로 전환 (ADR-001 개정)
- ⏳ 신청서 완성 (TODO: 팀 정보 입력)

**다음** (9/18~9/28)
- [ ] 신청서 제출 (9/28)
- [ ] 부품 주문 (릴레이, 모터 드라이버)
- [ ] 사전 준비: ACME-oneM2M-CSE Docker 실행 테스트

---

## 7. PolaGrid (선택적 확장 서비스)

PolaGrid는 이전 창의기초설계 과제에서 이미 동작을 검증한 규칙 기반 Arduino 데모(조도센서 + 서보모터 + 편광필름으로 채광 투과율 조절)다. 같은 oneM2M MN-CSE/IN-CSE와 MEC Mp1 서비스 레지스트리에 EdgePdM과는 독립된 두 번째 서비스로 선택적으로 접목한다.

- 필수 A~E 기능에 포함되지 않는다. Week 4 팩토리 MVP가 정시 완료되는 경우에만 시도하는 Week 5 스트레치 항목이다 (조건 상세: `DEVELOPMENT.md` 섹션 V, VI).
- `/polagrid/...` 별도 최상위 리소스 경로를 쓰며, `/pdm/...` 트리는 전혀 수정하지 않는다.
