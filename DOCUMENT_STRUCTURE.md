# 문서 구조 및 역할

> 이 파일은 EdgePdM 프로젝트의 문서들이 어떤 목적으로, 누가 읽는지 정리합니다.

---

## I. 핵심 문서 (필수, 공개)

### 1. docs/CONTEXT.md
**목적**: 도메인 모델링, 용어 정의, 핵심 결정 기록

**대상 독자**: 팀원, 심사위원 (처음 읽는 사람)

**내용**
- 프로젝트 이름, 목표 (oneM2M 국제 개발자 공모전 단일 트랙)
- 핵심 용어: EdgePdM, 시나리오, 기술 스택
- 아키텍처 선택 이유 (ADR-001, 002)
- 전제 조건 (팀, 환경, 외부 의존성)

**읽는 시점**
- 처음 시작할 때
- 큰 결정을 할 때 (계획 변경)

---

### 2. docs/DEVELOPMENT.md
**목적**: 팀이 실제로 따라할 상세 계획

**대상 독자**: 팀원 (매일 읽음)

**내용**
- 준비 단계 (9/17~9/28): 신청서, 부품 주문
- 사전 준비 (9/29~10/4): CSE 로컬 실행, 센서 테스트
- 개발 7주 (10/5~11/20): 주차별 구체적 작업, 완료 기준, 산출물
- 리스크 & 대응
- 최종 체크리스트

**읽는 시점**
- 매주 시작 (이번 주 목표 확인)
- 작업 전 (이번 주 구체적 할 일)
- 막혔을 때 (리스크 섹션 확인)

---

### 3. docs/APPLICATION.md
**목적**: 해커톤 신청서 제출용

**대상 독자**: oneM2M 심사위원회

**내용**
- 서비스 개요 (팩토리/물류 시나리오)
- 구현 방법 (아키텍처, 기술 스택, 리소스 트리)
- 팀 역량
- 기대 효과 (경제, 표준화, 엣지 효율성)

**읽는 시점**
- 신청 전 (9/28 마감 확인)
- 심사 당일 (발표 전)

---

## II. 참고 문서 (선택, 보관)

### 4. docs/ARCHITECTURE.md *(TODO: 생성)*
**목적**: 아키텍처 상세 설명

**대상 독자**: 개발자, 기술 검토자

**내용**
- 아키텍처 다이어그램 (그림)
- oneM2M 리소스 트리 (상세)
- 팩토리/물류 시나리오별 구현 차이
- 데이터 흐름 (센서 → AE → CSE → 추론 → 대시보드)

**생성 시점**: Week 1 기술 검토 후

---

### 5. docs/DUAL-SCENARIO.md *(TODO: 생성)*
**목적**: 팩토리 vs 물류 시나리오 비교

**대상 독자**: 비기술 이해관계자 (지도교수, 기업 담당자)

**내용**
- 산업별 배경 (고장 영향, 현실적 예시)
- 같은 코드로 2개 산업을 지원하는 방법
- 배포 절차 (환경변수만 바꿈)
- 기대 효과 (각 산업별)

**생성 시점**: Week 2

---

### 6. docs/BENCHMARK-RESULTS.md *(TODO: 생성)*
**목적**: MEC vs Cloud 성능 비교 결과

**대상 독자**: 기술 심사위원, 학술 보고서 독자

**내용**
- 벤치마크 설정 (워크로드, 환경)
- 측정 결과 (CSV 데이터)
- 그래프 (지연, 대역폭)
- 결론 (MEC의 장점)

**생성 시점**: Week 6

---

### 7. docs/TUTORIAL-FACTORY.md *(TODO: 생성)*
**목적**: 스마트팩토리 배포 가이드

**대상 독자**: 다른 개발자, 산업체 기술팀

**내용**
```
1. 준비물 (아두이노, 센서, 모터)
2. docker-compose 설정 (SITE_TYPE=factory)
3. 센서 연결도
4. 빌드 & 실행: docker compose up
5. 첫 CIN 확인까지 (5분)
6. 문제 해결 (Q&A)
```

**특징**: 이 가이드만 보고 새 PC에서 30분 내에 작동 가능할 수준

**생성 시점**: Week 6

**라이선스**: CC BY 4.0

---

### 8. docs/TUTORIAL-LOGISTICS.md *(TODO: 생성)*
**목적**: 스마트물류 배포 가이드

**대상 독자**: 다른 개발자, 물류 회사 기술팀

**내용**: TUTORIAL-FACTORY.md와 동일 구조, 물류별 설정 예시

**생성 시점**: Week 6

**라이선스**: CC BY 4.0

---

### 9. docs/TEST-SCENARIOS.md *(TODO: 생성)*
**목적**: E2E 테스트 시나리오 및 결과

**대상 독자**: QA, 재현성 검증

**내용**
- 정상 케이스 (정상 회전, 데이터 수집)
- 장애 케이스 (불균형, 과부하, 센서 단절)
- 네트워크 케이스 (끊김, 지연)
- 각 케이스의 예상 결과 & 실제 결과

**생성 시점**: Week 6~7

---

## III. 정리 완료 (2026-09-17)

### 삭제됨 (상위 문서로 통합됨)
- `docs/proposal_draft_en.md` → `docs/APPLICATION.md`로 통합
- `docs/hackathon_plan.md` → `docs/DEVELOPMENT.md`로 통합
- `AIoT_캡스톤_학기개발계획서_v1.0.md` → 캡스톤 내용은 `docs/DEVELOPMENT.md`와 `docs/CONTEXT.md`로 커버
- `docs/diagram/edgepdm-architecture.visual-check.json` → 실패한 검사 잔여 파일

### 이동됨
- `CONTEXT.md` → `docs/CONTEXT.md`
- `APPLICATION.md` → `docs/APPLICATION.md`
- (`DOCUMENT_STRUCTURE.md`는 프로젝트 최상위 색인 역할이므로 루트에 유지)

### 보관 중
- `docs/diagram/edgepdm-architecture.html` — 아키텍처 다이어그램 (MVP 파이프라인, 공개 가능)
- `docs/diagram/edgepdm.architecture.json` — 위 다이어그램의 Archify 원본
- `docs/diagram/edgepdm-roadmap.html` — 7주 개발 로드맵 다이어그램 (공개 가능)
- `docs/diagram/edgepdm-roadmap.workflow.json` — 위 다이어그램의 Archify 원본

---

## IV. 최종 문서 구조 (예상)

```
onem2m_ton/
├── README.md                          ← 프로젝트 개요 (누구나 읽음, TODO)
├── DOCUMENT_STRUCTURE.md              ← 이 파일 (문서 색인)
├── LICENSE                            ← Apache 2.0 (코드)
├── docs/
│   ├── CONTEXT.md                     ← 도메인 모델 (필수 읽음)
│   ├── APPLICATION.md                 ← 신청서 (제출용)
│   ├── DEVELOPMENT.md                 ← 개발 계획 (팀이 매일 읽음)
│   ├── ARCHITECTURE.md                ← 아키텍처 상세 (TODO)
│   ├── DUAL-SCENARIO.md               ← 팩토리 vs 물류 (TODO)
│   ├── BENCHMARK-RESULTS.md           ← 성능 비교 (TODO)
│   ├── TUTORIAL-FACTORY.md            ← 팩토리 배포 (TODO) [CC BY 4.0]
│   ├── TUTORIAL-LOGISTICS.md          ← 물류 배포 (TODO) [CC BY 4.0]
│   ├── TEST-SCENARIOS.md              ← 테스트 (TODO)
│   ├── MODEL-REPORT.md                ← AI 모델 (생성 예정, Week 3)
│   ├── MEC-DEPLOYMENT.md              ← MEC 기술 (생성 예정, Week 4)
│   ├── adr/                           ← ADR들은 CONTEXT.md에 통합
│   └── diagram/
│       ├── edgepdm-architecture.html      ← MVP 파이프라인 다이어그램
│       ├── edgepdm.architecture.json
│       ├── edgepdm-roadmap.html           ← 7주 개발 로드맵 다이어그램
│       └── edgepdm-roadmap.workflow.json
├── firmware/
│   ├── README.md
│   ├── sensor_read.ino
│   └── motor_control.ino
├── edge-ae/
│   ├── README.md
│   ├── main.py
│   └── requirements.txt
├── simulator/
│   ├── simulator_ae.py
│   └── workloads.json
├── mec-inference/
│   ├── Dockerfile
│   ├── inference.py
│   ├── model.pkl
│   └── appdescriptor.json
├── dashboard/
│   ├── index.html
│   └── style.css
├── benchmark/
│   ├── run_benchmark.py
│   └── results.csv
├── data/
│   ├── normal.csv
│   ├── imbalance.csv
│   └── overload.csv
└── docker-compose.yml
```

---

## V. 읽기 순서 (역할별)

### 처음 프로젝트에 합류한 개발자
1. README.md (프로젝트가 뭔가)
2. docs/CONTEXT.md (왜 이렇게 했나)
3. docs/DEVELOPMENT.md (이번주 뭘 하나)

### 해커톤 심사위원
1. docs/APPLICATION.md (신청서)
2. docs/diagram/edgepdm-architecture.html, edgepdm-roadmap.html (다이어그램)
3. 데모 영상 (Week 7)
4. docs/TUTORIAL-*.md (생태계 기여)
5. docs/BENCHMARK-RESULTS.md (MEC 효과)

