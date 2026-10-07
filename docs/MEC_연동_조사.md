# oneM2M–MEC 연동 조사 (2026-10-07)

대회 개요 자료(0-7b)가 가리킨 규격을 읽고 PolaGrid에 쓸 것만 추렸다. 원문은 아래 출처. 측정하거나 실행해 보지 않은 내용은 "미확인"으로 적었다.

## 1. 읽은 것

| 문서 | 상태 | 쓸모 |
|---|---|---|
| oneM2M TR-0077 v0.3.0 (2026-03-26) "oneM2M and MEC integration scenario and mechanisms" | 초안. 배치 옵션·Handover 분석은 내용이 있고, **7.1 등록 해법(Solution 1~5)과 FL·Swarm 해법은 제목만 있음** | 배치 옵션, Handover 갭 분석, FL 구조 |
| oneM2M TR-0080 v5.0.0 (2025-11-11) | TR-0077 5~6절과 같은 내용의 발행판 | 인용용 |
| ETSI GS MEC 033 V3.1.1 (2022-12) "IoT API" | 발행 규격 | IoT 플랫폼(=우리 CSE)·장치를 MEC에 등록하는 API |
| TR-0078 개발자 가이드, TS-0042(oneM2M–MEC 연동 규격) | ESTIMED 산출물 목록에 있으나 공개 위치를 못 찾음 | Discord 멘토에게 물어볼 것 |

## 2. 배치 옵션 4개 (TR-0077 5.1) — PolaGrid는 어디인가

| 옵션 | 구성 | PolaGrid 대응 |
|---|---|---|
| A | CSE는 클라우드, MEC는 엣지 | IN-CSE(중앙)만 보면 이것 |
| B | CSE와 MEC가 둘 다 엣지, 다른 물리 노드 | **지금 시연 구성**: 구역 MN-CSE는 우리 PC, MEC 플랫폼은 원격 ETSI Sandbox |
| C | CSE와 MEC가 같은 엣지 노드 | **목표 구성**: 구역 MN-CSE + 구역 컨트롤러(MEC 앱)가 한 엣지 노드 |
| D | 밀결합, CSE 자체가 MEC 서비스 | MN-CSE를 MEC011로 서비스 등록하면 이 방향의 일부를 시연 |

- 서술 방식: "구역마다 엣지에 MN-CSE + MEC 앱(옵션 C)을 두고, 중앙 IN이 묶는 계층 구조. 해커톤 시연은 공용 Sandbox를 써서 옵션 B로 돌렸다."
- TR-0077 7.1은 "MN-CSE를 MEC 앱으로 등록(Solution 4)", "oneM2M을 MEC 서비스로 통합(Solution 5)"을 해법 후보로 **제목만** 적어 두었다. **우리가 MEC011 서비스 등록으로 구현하면 규격이 비워 둔 부분의 사례**가 된다(기사·인터뷰 소재).

## 3. MEC API 두 가지로 할 수 있는 것

### 3-1. MEC011 서비스 등록 (Solution 5 방향)
- 구역 컨트롤러가 시작할 때 `confirm_ready` → `services`에 `polagrid-daylight` 등록. `transportInfo.endpoint`에 그 구역 MN-CSE 주소.
- 다른 앱(대시보드·BMS mock)은 MEC 서비스 조회로 구역 CSE를 찾는다. 시험 순서는 개발.md 0-7b와 대화 기록의 "MEC 시험 방식".

### 3-2. MEC033 IoT API (TR-0077이 직접 언급: FL 문맥에서 "IoT API로 문맥 보강")
루트는 `{apiRoot}/iots/v1/`, HTTPS + OAuth 2.0 필수(Sandbox가 처리하는지 미확인).

| 리소스 | 우리 쓰임 |
|---|---|
| `POST /registered_iot_platforms` (`IotPlatformInfo`) | **구역 MN-CSE를 IoT 플랫폼으로 등록.** `iotPlatformId`=`polagrid-mn001`, `userTransportInfo`=MQTT 브로커(`type: MB_TOPIC_BASED`, `protocol: MQTT`, `implSpecificInfo.uplinkTopics`/`downlinkTopics`에 oneM2M MQTT 토픽 `/oneM2M/req/...`), `customServicesTransportInfo`=oneM2M HTTP 주소(`REST_HTTP`) |
| `POST /registered_devices` (`DeviceInfo`) | **실물 ESP32 칸을 장치로 등록**, `requestedIotPlatformId`로 구역 MN에 연결. 필수는 `deviceId`·`deviceAuthenticationInfo`·`enabled`. IMEI 등 셀룰러 식별자는 "적어도 하나 권장"이라 Wi-Fi ESP32는 `deviceMetadata`에 MAC을 넣는 식으로 우회(규격 해석, 미확인) |
| `GET /registered_iot_platforms/{id}` | 다른 MEC 앱이 우리 CSE의 원래 API(oneM2M)를 찾는 경로 |

→ "MEC가 oneM2M CSE를 IoT 플랫폼으로 알고, 칸 장치를 그 플랫폼에 배정한다"는 장면을 표준 API로 보여 줄 수 있다. 루브릭 oneM2M–MEC Application·MEC Services 근거. **Sandbox에서 MEC033이 실제로 열려 있는지부터 확인**(Sandbox README에는 지원 목록에 있음).

## 4. Handover (루브릭 CSE Handover & Service Continuity, TR-0077 6.3·7.2)

- 규격이 꼽는 상황 3개 중 **"엣지 노드 장애 시 긴급 이전"**과 **"부하 분산"**이 PolaGrid에 맞다(칸은 움직이지 않음).
- 방식은 **네트워크 주도**(장치는 지시만 따름): 구역 MN이 죽거나 과부하면 IN 쪽 오케스트레이터 AE가 칸들에 새 MN으로 재등록을 지시.
- 규격이 요구하는 동작과 지표를 그대로 측정 항목으로 쓴다:
  - 구독은 **새 구독을 먼저 만들고 옛 구독을 지운다**(6.2).
  - 지표: 재등록 시간, 유실 메시지, 지연 변화(6.3 "KPIs such as attach/authentication time, packet loss, and latency deltas"). 예시 예산 "중요 데이터 ≤ 200 ms".
- 규격이 **아직 표준이 없다고 적은 갭**(7.2.2)을 우리가 부딪히는 문제로 연결하면 기사 소재가 된다:
  - 7.2.2.1 AE 신원 연속성(재등록하면 AE-ID가 바뀜)
  - 7.2.2.4 명령(하향)을 지금 담당 MN으로 보내는 방법 없음 → 우리는 구역 GRP 멤버를 다시 만들어야 함
  - 7.2.2.5 같은 AE가 두 MN에 동시 등록되는 것을 막는 규칙 없음
- 비용: MN 장애 주입 + 재등록·구독 복원 스크립트 + 측정. 하루 정도. 일정상 Week 6 장애 테스트와 합친다(0-7).

## 5. 연합학습 FL (TR-0077 6.5, 루브릭 Federated Learning)

- 규격 Option 1: **FL 클라이언트 = MN 쪽 AE**(구역 데이터로 로컬 학습), **집계 = IN 또는 MEC 앱**, 원시 데이터는 구역 밖으로 안 나감.
- AI ③은 구역별 회귀 모델이라 **계수 가중 평균(FedAvg)**만으로 구현할 수 있다. 모델 계수는 oneM2M 리소스(CIN 또는 FlexContainer)로 IN에 올리고, 집계 결과를 다시 내려보낸다.
- 비용이 작아 보여서(반나절, 미확인) 0-7에서 "먼저 버림"으로 둔 FL을 다시 검토할 가치가 있다. 단 우선순위는 ACP → FlexContainer 다음.

## 6. 바로 쓸 결정 사항

1. MEC 시연 구성은 **옵션 B(지금) → C(목표)**로 서술한다.
2. MEC 연동은 **MEC011 서비스 등록 + MEC033 IoT 플랫폼 등록** 두 장면. Sandbox에서 둘 다 되는지 확인이 먼저.
3. Handover는 "MN 장애 → 네트워크 주도 재등록, 새 구독 먼저" 시나리오로, 규격의 KPI로 측정.
4. FL은 AI ③ 계수 평균으로 저비용 구현 가능성 → ACP·FlexContainer 이후 재검토.
5. Discord 멘토에게 물을 것: TR-0078·TS-0042 공개 위치, Sandbox의 MEC033 지원 여부.

## 출처
- oneM2M TR-0077 v0.3.0: https://specifications.onem2m.org/tr/tr-0077/latest/ (docx 다운로드로 전문 확인)
- oneM2M TR-0080 v5.0.0: https://specifications.onem2m.org/tr/tr-0080/latest/
- ETSI GS MEC 033 V3.1.1: https://etsi.org/deliver/etsi_gs/mec/001_099/033/03.01.01_60/gs_mec033v030101p.pdf
- ESTIMED 산출물 목록: https://estimed.etsi.org/reports_specifications
- ETSI MEC Sandbox README: https://labs.etsi.org/rep/mec/etsi-mec-sandbox-frontend/-/raw/master/README.md
