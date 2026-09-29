# EdgePdM 개발 계획서

> **목적**: 팀이 실제로 읽고 따라할 상세 계획
> **기간**: 9/17(신청) ~ 11/20(최종 제출)
> **팀**: 1~2명, Python/Docker 경험 있음
> **최종 목표**: 2026 oneM2M 국제 개발자 공모전 제출

---

## I. 프로젝트 개요

**EdgePdM**: 회전 설비의 예지보전(PdM) 시스템
- 센서: 진동, 전류, 온도 (Arduino Uno)
- 분석: Edge에서 실시간 이상 감지 (FFT + Isolation Forest)
- 배포: 스마트팩토리 + 스마트물류 (같은 코드, 다른 설정)
- 표준: oneM2M(데이터) + ETSI MEC(추론)

**일정**
| | 값 |
|---|---|
| 기간 | 9/17 ~ 11/25 |
| 신청 마감 | 9/28 |
| 개발 기간 | 10/5 ~ 11/20 (7주) |
| 발표 | 영어 온라인 발표 |
| 핵심 평가 기준 | oneM2M/MEC 표준 활용 |

---

## II. 준비 단계 (9/17 ~ 9/28): 신청서 완성

이 단계에서는 해커톤 신청서를 제출하고 필요한 부품을 주문합니다.

**신청서 영문 초안 완성** (~9/21)
- SERVICE.md의 구성을 따라 팩토리/물류 이중 시나리오를 명시합니다.
- 아키텍처 다이어그램과 oneM2M 리소스 트리를 포함합니다.
- 팀원 정보와 이수 과목을 작성합니다.
- 표준화, 비용 절감, 생태계 기여를 강조합니다.
- 참고: `APPLICATION.md`

**신청서 제출** (9/28 23:59 KST 전)
- 폼: https://onem2m-hackathon.io/regist.asp
- 영문 4항목 + 팀장 정보 + 팀원 정보 (최대 5명)를 작성합니다.
- 선택: 다이어그램, 영상 (ZIP 파일로 업로드)

**부품 주문** (~9/21)
- 릴레이 모듈 또는 모터 드라이버 (PWM 제어용): 2~3만원
- DC 모터 또는 팬 (대체 가능한 것): 1~2만원
- 도착 목표: 10/2까지 (Week 0 준비 기간 전)

---

## III. 사전 준비 단계 (9/29 ~ 10/4): Week 0

팀이 oneM2M을 처음 다루므로, 환경 구축보다 개념 학습을 먼저 끝냅니다. 학습 없이 Week 1에 들어가면 리소스 트리·Subscription/Notification 개념을 실습 중에 배우게 되어 일정이 밀립니다.

**oneM2M 개념 사전 학습 (9/29~30, 약 2일)**
- AE/CSE/CIN/CNT/Subscription/Notification 개념 및 리소스 트리 구조를 문서로 학습합니다.
- ACME-oneM2M-CSE(Andreas Kraft, github.com/ankraft/ACME-oneM2M-CSE) 튜토리얼을 따라 리소스 생성 → 조회 → Subscription 콜백 수신까지 한 번 직접 실습합니다.
- 완료 기준: curl만으로 CNT 생성 → CIN 추가 → Subscription 등록 → Notification 수신을 스스로 재현할 수 있어야 함.

**CSE 로컬 실행**
```bash
cd onem2m_ton
docker-compose up cse  # ACME-oneM2M-CSE 우선 시도 (Python, 팀 기존 스택과 일치, 문서 초심자 친화적)
                        # tinyIoT/Mobius는 ACME로 막히는 경우에만 대체 검토
```
curl로 기본 리소스 생성을 테스트합니다. 참고: `edge-ae/README.md`

**로컬 MEC mock 준비 (10/2~4)**
Week 4까지 실제 MEC 플랫폼이 확정되지 않을 수 있으므로(VI. 리스크 참고), Location API·Mp1 서비스 레지스트리를 흉내내는 최소 Flask mock을 미리 만들어 둡니다. 실제 플랫폼이 늦게 제공돼도 개발이 막히지 않도록 하는 용도이며, Week 4에서 실제 API로 교체합니다.

**Arduino 센서 테스트**
MPU6050 (가속도), ACS712 (전류), DS18B20 (온도)을 아두이노에 연결하고 각각의 raw 값을 시리얼 모니터에서 확인합니다. 참고: `firmware/README.md`

**환경 변수 구조 설계**
docker-compose.yml에 SITE_TYPE과 ALERT_MODE를 선언합니다.
```yaml
environment:
  - SITE_TYPE=factory  # or logistics
  - ALERT_MODE=email   # or sms/push
```

---

## IV. 개발 단계 (10/5 ~ 11/20): 7주

각 주의 완료 기준을 E2E 테스트로 검증합니다. 막힐 때는 리스크 섹션을 확인합니다.

### Week 1 (10/5~11): 센서 → oneM2M 파이프라인

킥오프 미팅에서 MEC 환경을 확인합니다. ADN-AE를 작성해서 `pyserial`로 센서 데이터를 읽고, `requests`로 oneM2M CIN을 만듭니다.

리소스 트리는 이렇게 구성합니다:
```
/pdm/site/{factory_line1 | logistics_hubA}/motor1/
  ├─ vibration (Container)
  │  └─ [CIN] {timestamp, values: [1000 samples @ 1kHz]}  # 1초 윈도우 배치
  ├─ current      # 1Hz
  ├─ temp         # 1Hz
  └─ command (Edge AE가 읽을 명령)
```

완료했으면 실물 센서 1개와 가상 센서 10개(시뮬레이터)가 모두 CSE에 1초 주기로 데이터를 쌓아야 합니다 (진동은 1kHz로 샘플링해 1초 단위 1,000개 배열로 묶어서 전송). `curl <CSE>/pdm/site/factory_line1/motor1/vibration/la`로 조회 가능한지 확인합니다.

산출물:
- `edge-ae/main.py`: AE 구현
- `simulator/simulator_ae.py`: 가상 센서 AE
- `docker-compose.yml`: CSE, AE, Simulator 서비스 정의

---

### Week 2 (10/12~18): 팩토리 시나리오 데이터 수집 + 명령 펌웨어

정상 회전 데이터를 30분 이상 수집합니다. 테이프 불균형, 마찰 패드, 그 외 이상 상태도 각각 30분씩 수집해서 라벨링합니다.

펌웨어를 업데이트해서 CSE의 `command` 컨테이너를 poll하거나 subscribe합니다. 명령은 다음과 같습니다:
```
{"action": "normal"}  // PWM 100%
{"action": "slow"}    // PWM 50%
{"action": "stop"}    // PWM 0%
```

완료했으면 CSV 파일 5개(정상, 불균형, 마찰 등)가 각 30분 분량 있어야 합니다. Arduino가 `command` CIN을 읽고 PWM을 변경하는지 확인합니다. `curl ... POST /pdm/site/factory_line1/motor1/command` 후 5초 내에 모터 속도가 바뀌어야 합니다.

산출물:
- `firmware/motor_control.ino`: 명령 수신, PWM 제어
- `data/`: 라벨링된 센서 CSV

---

### Week 3 (10/19~25): AI 모델 (FFT + Isolation Forest + Random Forest 분류기)

scipy FFT로 1초 윈도우(1,000샘플, 1kHz)를 주파수 영역(32~256Hz)으로 변환합니다. 이 특징을 두 모델에 각각 입력합니다:
- **Isolation Forest** (비지도): 정상 데이터로만 학습시켜, 학습 때 보지 못한 새로운 이상 패턴을 점수(novelty score)로 잡아냅니다. 이 점수는 "얼마나 이상한가"만 알려주며 고장 종류는 구분하지 못합니다.
- **Random Forest** (지도학습): Week 2에서 라벨링한 normal/imbalance/overload 데이터로 학습시켜, fault type을 직접 분류합니다.

anomaly CIN은 Isolation Forest 점수가 임계값을 넘거나 Random Forest가 non-normal을 예측하면 기록되고, 이때 Random Forest의 예측 라벨을 fault type으로 첨부합니다.

테스트셋에서 Random Forest의 Confusion Matrix, Precision, Recall을 계산해서 분류가 잘 작동하는지 확인합니다. Isolation Forest는 정상 데이터만으로 학습했으므로 별도로 이상 탐지 재현율(recall)을 확인합니다.

완료했으면 테스트셋 정확도 리포트(true_label, predicted_label, isolation_score의 CSV)가 있어야 합니다. 두 모델 모두 pickle 파일로 `mec-inference` 컨테이너 안에 저장합니다. 새 CIN을 받으면 2초 내에 anomaly CIN을 기록하는지 확인합니다.

산출물:
- `mec-inference/isolation_model.pkl`: 이상 탐지 모델 (Isolation Forest)
- `mec-inference/classifier_model.pkl`: 고장 분류 모델 (Random Forest)
- `mec-inference/inference.py`: 추론 로직
- `docs/MODEL-REPORT.md`: 정확도, Confusion Matrix, threshold 값

---

### Week 4 (10/26~11/1): MEC 연동 + MVP (팩토리)

MEC Location API를 호출해서 설정된 좌표 기반으로 가장 가까운 정비사를 찾습니다. Mp1 서비스 레지스트리에 "pdm-anomaly" 서비스를 등록하고, siteType과 location 메타데이터를 포함한 AppD(App Descriptor)를 작성합니다.

E2E 시연: 팬에 테이프를 붙이면 10초 내에 anomaly CIN(label=imbalance)이 생성됩니다. command CIN(action=slow)이 자동으로 기록되고 정비사에게 알림이 갑니다.

완료했으면 MEC 환경에서 Location API 호출 로그가 나타나야 합니다. 팩토리 시나리오 E2E 흐름이 5회 이상 성공하고, 대시보드에 anomaly가 표시되는지 확인합니다.

산출물:
- `mec-inference/appdescriptor.json`: MEC AppD
- `docs/MEC-DEPLOYMENT.md`: Location API 사용법, 등록 절차

---

### Week 5 (11/2~8)
**목표**: 다중 현장 + 물류 시나리오 통합

**작업**
- IN-CSE 연동: MN-CSE가 IN-CSE에 등록됨 (다중 현장 지원)
- 대시보드: 실시간 그래프 + 이상 표시
  - 탭 1 (factory): 라인별 상태, 색상 구분
  - 탭 2 (logistics): 구간별 상태, 우회 경로 로그
- 물류 시나리오 테스트:
  1. 시뮬레이터로 물류 워크로드 (50대) 주입
  2. overload 상황 재현
  3. command=reroute 실행, 로그 기록

**완료 기준**
- 팩토리 + 물류 CIN이 한 대시보드에 필터되어 표시
- SITE_TYPE=factory로 실행 후 SITE_TYPE=logistics로 전환, 설정 반영됨 (5분 이내)
- 우회 경로 로그: `logs/reroute_2026-11-05.log` 파일 생성

**산출물**
- `dashboard/index.html`: 웹 UI (Tabs, Chart.js)
- `mec-inference/reroute_handler.py`: 물류 시나리오 처리

**(선택, 조건부) PolaGrid 부가 서비스**: Week 4 MVP가 정시 완료된 경우에만 시도. `/polagrid/site/...` 리소스 트리 구성, 기존 Arduino 하드웨어(조도센서+서보+편광필름) 재사용, MEC Mp1에 `polagrid-daylight` 서비스 등록. 착수 조건은 VI. 리스크 표 참고. Week 5 완료 기준에는 포함되지 않음.

---

### Week 6 (11/9~15)
**목표**: 벤치마크 + 튜토리얼 + 테스트

**작업**

**벤치마크 (C 기능)**
- MEC 위치 vs Cloud 위치에서 같은 추론 컨테이너 실행
- 측정: 지연(latency), 대역폭 (throughput)
- 워크로드:
  - 팩토리: 라인 3개, 총 10대 모터
  - 물류: 분류기 5개 구간, 총 50대 모터
- 결과: CSV + 그래프 (지연 비교, 대역폭 비교)

**튜토리얼 작성 (E 기능)**
- `docs/TUTORIAL-FACTORY.md`: 팩토리 배포 가이드
  ```
  1. docker-compose 설정 (SITE_TYPE=factory)
  2. 센서 연결
  3. docker compose up
  4. 5분 내 첫 CIN 확인
  ```
- `docs/TUTORIAL-LOGISTICS.md`: 물류 배포 가이드

**E2E 장애 테스트**
- 센서 단절 → AE가 감지, 타임아웃 로그
- 네트워크 끊김 → 재연결 후 CIN 재전송 확인
- CSE 재시작 → 데이터 손실 없음

**완료 기준**
- 벤치마크 결과 CSV + 그래프 (지연: 팩토리 <100ms, 물류 <200ms)
- 튜토리얼만 보고 새 PC에서 `docker compose up` → 5분 내 첫 CIN 생성
- 장애 시나리오 3종 로그 기록

**산출물**
- `benchmark/results.csv`: 지연, 대역폭 원본 데이터
- `docs/BENCHMARK-RESULTS.md`: 그래프 + 해석
- `docs/TUTORIAL-FACTORY.md`, `docs/TUTORIAL-LOGISTICS.md`
- `docs/TEST-SCENARIOS.md`: 장애 테스트 결과

---

### Week 7 (11/16~20)
**목표**: 문서 최종화 + 데모 영상 + 제출

**작업**

**README & 문서**
- `README.md`: 프로젝트 개요, 빌드 방법, 라이선스
- `docs/ARCHITECTURE.md`: 아키텍처 설명, 리소스 트리 설명
- `docs/DUAL-SCENARIO.md`: 팩토리 vs 물류 비교, 시나리오별 구현

**데모 영상 (10분)**
- Part 1 (5분): 팩토리 시나리오
  - 센서/아두이노 모습
  - 팬 정상 회전 → 테이프 부착 → 이상 감지
  - 자동 감속 + 알림 수신
- Part 2 (5분): 물류 시나리오
  - 시뮬레이터로 50대 워크로드
  - 이상 감지 + 우회 로그 기록
  - MEC vs Cloud 벤치마크 결과 설명

**발표 스크립트 (영어)**
- 2장 분량, 1장 = 30초 분량
- 비즈니스 케이스 강조: 표준 기반, 다중 산업, 낮은 비용

**GitHub 공개**
- 라이선스: 코드는 Apache 2.0, 문서는 CC BY 4.0
- `.gitignore`: 민감정보(API key, IP) 제외
- 브랜치: main에만 공개, 임시 브랜치는 정리

**제출**
- 해커톤: onem2m-hackathon.io 웹사이트의 "제출" 링크

**완료 기준**
- GitHub에 모든 코드 + 문서 공개
- 데모 영상 업로드 (YouTube or Vimeo)
- 해커톤 제출 완료

---

## V. 추가 기능 (필수 52시간)

| 기능 | 주차 | 시간 | 상태 |
|---|---|---|---|
| A. 고장 분류 | 3 | 10h | 필수 |
| B. 폐루프 제어 | 2~4 | 10h | 필수 |
| C. 벤치마크 | 6 | 12h | 필수 |
| D. MEC 서비스 등록 | 4 | 11h | 필수 |
| E. 튜토리얼 + 패키지 | 6 | 9h | 필수 |
| F. PolaGrid 부가 서비스 | 5 | 11h | 선택/조건부 (52시간 필수 합계에 미포함) |

F는 위 필수 52시간 합계에 포함되지 않는다. 착수 조건은 VI. 리스크 표를 참고.

**학습 곡선 버퍼**: 위 52시간은 oneM2M 경험자 기준 구현 시간이다. 팀이 oneM2M을 처음 다루므로 Week 0 사전 학습(개념 + ACME-CSE 실습, 약 12~16h)을 별도로 확보하고, Week 1~2 디버깅에 추가 여유(+15~20h)를 감안한다. 이 버퍼는 Week 0에서 미리 소진하는 것을 원칙으로 하며, 개발 단계(Week 1~7)의 52시간에는 포함하지 않는다.

---

## VI. 리스크 & 대응

| 리스크 | 시기 | 대응 |
|---|---|---|
| oneM2M 최초 사용 학습 곡선 | 0주 | Week 0에 개념 학습 + ACME-CSE 실습 선행. 완료 기준(Subscription/Notification 재현) 미달 시 Week 1 착수 1~2일 순연 허용 |
| MEC 환경 미확정 | 1주 | Week 0에 만든 로컬 MEC mock으로 개발 지속, 킥오프 때 실제 환경으로 교체 |
| 물류 시나리오 구현 복잡 | 4주 | 우회 로그만 기록하고 실제 전환은 시뮬. 존 간 실제 핸드오프(MEC-to-MEC 이동성)는 이번 범위에서 제외 |
| 벤치마크 측정 정확도 | 6주 | 여러 번 반복 측정, 이상치 제거 |
| PolaGrid(F) 착수 여부 불확실 | 5주 | Week 4 MVP 완료 기준 충족 + Feature A/B/D 완료 + 미해결 블로킹 리스크 없음 + Week 5 여유시간 ≥15h 확인 후 착수. 미충족 시 즉시 포기, 재일정 없음 |

---

## VII. 최종 체크리스트

**9/28까지**: 신청서를 제출하고 부품이 도착했는지 확인합니다.

**10/1**: 선정 발표를 확인합니다.

**10/5**: 킥오프 미팅에서 MEC 환경을 상세히 설명받고 기술 문서를 다운로드합니다.

**11/20**: GitHub에 모든 코드와 문서를 공개하고, 데모 영상을 완성한 후 해커톤 제출 폼을 작성해서 제출합니다.

**11/23~25**: 발표 스크립트를 연습하고 라이브 장애에 대비해 백업 영상을 준비합니다.

