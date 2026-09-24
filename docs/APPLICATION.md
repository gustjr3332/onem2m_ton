# 2026 oneM2M International Developer Competition: Application

**Competition**: 2026 oneM2M International Developer Competition  
**Service/Product name**: EdgePdM: Standards-based Predictive Maintenance for Rotating Equipment  
**Team name**: [TODO]  
**Team members**: [TODO, max 5 people]  
**Submission date**: September 28, 2026

---

## 1. Service/Product Overview

### Background

Rotating equipment failure is a critical blind spot across two high-impact industries:

- **Smart Factory**: An unexpected motor failure on a production line (conveyor drive, cooling fan, pump) stops the entire line, causing production loss, product defects, and rushed repairs.
- **Smart Logistics**: The same motor failure on a warehouse sorter conveyor or AGV drive wheel causes missorted packages and shipping delays during peak hours, directly hitting customer satisfaction and delivery SLAs.

Commercial predictive maintenance (PdM) solutions are expensive (€50k–€500k), vendor-locked, and typically built for only one industry domain. Small manufacturers and mid-size logistics operators cannot afford them and instead rely on scheduled maintenance or emergency response.

### Service: EdgePdM

EdgePdM collects vibration, current, and temperature data from low-cost sensors (€20–€50 per equipment) attached to rotating equipment and detects abnormal patterns in real time at the network edge, before the equipment fails.

The same hardware and pipeline serve two deployment scenarios with only a configuration change:

| Aspect | Smart Factory | Smart Logistics |
|---|---|---|
| **Equipment** | Production line conveyor, cooling fan motor | Warehouse sorter conveyor, AGV drive motor |
| **Failure impact** | Line stoppage, product loss | Missorted packages, shipping delay |
| **Alert recipient** | Line maintenance technician (fixed floor zone) | Roaming technician or dispatcher (location-aware via MEC Location API) |
| **Response action** | Auto-slow or stop the line | Auto-slow or reroute the conveyor segment |

### IoT Technologies Used

**oneM2M**  
Sensor data, anomaly results, and metadata are stored in standard oneM2M resources (AE / Container / ContentInstance / Subscription) with a `siteType` tag (factory-line or logistics-hub), so one platform serves both scenarios. Any oneM2M application can query and reuse the data, avoiding vendor lock-in.

**ETSI MEC**  
Anomaly detection runs as a MEC application close to the equipment, keeping latency under 200ms and raw sensor data local, which reduces cloud bandwidth and cost. MEC service APIs (Location API, Service Registry) locate and alert the nearest worker.

### Target Users

- Small and medium-sized manufacturers (< 500 employees)
- Warehouse and 3PL logistics operators (10k–100k SKUs)
- Facility managers responsible for multiple sites
- Maintenance service providers serving both domains

### Why this approach

EdgePdM is not locked to a vendor: the data uses an open standard (oneM2M), so factories and logistics operators can switch platforms or add third-party tools without rewriting. The same code runs in both industries, reducing development cost. Inference happens at the edge, where latency matters, instead of in the cloud. Low-cost sensors and open-source libraries keep the total cost under €5k per site, compared to €50k–€500k for commercial PdM. The team has academic supervision and industrial experience.

---

## 2. Implementation Method

### Hardware

- **Sensor node**: Arduino Uno with MPU6050 (single-axis vibration / acceleration, streamed as binary to fit UART bandwidth at 1kHz), ACS712 (current), DS18B20 (temperature)
- **Test equipment**: Small DC motor or fan; faults are reproduced by adding an imbalance weight or friction pad
- **Deployment**: Same hardware to any rotating equipment via 3–5 sensor connections

### Architecture

```
[Sensor Node: Arduino Uno + 3 sensors]
    │ UART (vibration @ 1kHz, batched into 1s windows; current/temp @ 1Hz)
    ▼
[Edge AE: Python gateway, Docker]
    │ HTTP POST (oneM2M Content Instances, 1 CIN/sec per channel)
    ▼
[MN-CSE: tinyIoT or Mobius, Docker]
    │ oneM2M Subscription / Notification
    ▼
[MEC Inference App: FFT + Isolation Forest (novelty) + Random Forest (fault type), Docker]
    │ MEC Location API → nearest worker alert
    │ Mp1 Service Registry registration
    ▼
[IN-CSE: Central oneM2M server]
    │ Multi-site data aggregation
    ▼
[Web Dashboard: Real-time status + alerts]
```

### oneM2M Resource Tree

```
/pdm
 └─ site
     ├─ factory_line1
     │   └─ motor1
     │       ├─ vibration (Container)
     │       │   └─ [CIN] {timestamp, samples: [f1, f2, ...]}
     │       ├─ current (Container)
     │       ├─ temp (Container)
     │       ├─ anomaly (Container)
     │       │   └─ [CIN] {score, label: "imbalance|overload", timestamp}
     │       └─ command (Container)
     │           └─ [CIN] {action: "slow|stop|reroute", timestamp}
     └─ logistics_hubA
         └─ sorter1
             └─ (same structure)
```

### Implementation Details

#### Core Pipeline
1. **Edge AE**: Reads Arduino sensor data via pyserial (vibration sampled at 1kHz, current/temp at 1Hz), batches each 1-second window, and posts as oneM2M ContentInstances to MN-CSE.
2. **MEC Inference App**: Subscribes to vibration/current/temp containers. For each new 1-second window:
   - Applies scipy FFT to the 1,000-sample vibration window to extract frequency features (32–256 Hz range)
   - Scores the window with a pre-trained Isolation Forest model to flag novel/unseen anomalies
   - Classifies fault type (normal / imbalance / overload) with a supervised Random Forest trained on labeled fault data
   - Writes anomaly CIN when either the Isolation Forest score exceeds threshold or the Random Forest predicts a non-normal class, tagging the predicted fault type
3. **Closed-loop control**: When anomaly is detected, MEC app writes a command CIN. Edge AE polls the command container and adjusts motor PWM (100% → 50% → 0%).
4. **Multi-site**: MN-CSE registers itself to a central IN-CSE, so a dashboard can monitor multiple factory lines or warehouse zones from one interface.

#### Enhanced Features

**Fault Classification (A)**  
Beyond binary anomaly detection, a supervised Random Forest classifier, trained on FFT features from labeled normal/imbalance/overload recordings, labels the fault type, so maintenance teams can dispatch the right technician with the right tools. Isolation Forest remains as a separate novelty check for anomalies the classifier was never trained on.

**Closed-loop Control (B)**  
When an anomaly is confirmed, the MEC app writes a command to the motor. On a factory line, the motor slows or stops to prevent cascading failures. In logistics, it slows or reroutes to maintain throughput.

**Performance Evaluation (C)**  
A virtual motor simulator generates realistic workloads (1, 10, 50 motors). The same inference container runs at the MEC host and at a cloud location. We measure end-to-end latency and upstream bandwidth to prove MEC's value.

**MEC Service Exposure (D)**  
The inference app registers as a "pdm-anomaly" service in the MEC service registry (Mp1), with an Application Descriptor that includes siteType and location metadata. Other MEC applications can discover and subscribe to fault events.

**Open-source Contribution (E)**  
The oneM2M client code is packaged as a reusable Python library. We ship two tutorials:
- "Predictive Maintenance on a Smart Factory Line"
- "Warehouse Sorter Fault Detection and Auto-Reroute"

Both demonstrate how to build oneM2M + MEC AIoT apps from scratch.

### Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Sensors | Arduino Uno (C++) | Low cost, wide availability, UART interface |
| Edge gateway | Python 3.10 + Docker | Easy to maintain, cross-platform, lightweight |
| Local message broker | Mosquitto (if needed) | Optional; can use oneM2M directly |
| Standardized storage | oneM2M (MN-CSE) | ETSI, TTA, 3GPP standard; vendor-neutral |
| AI inference | scipy (FFT) + scikit-learn (Isolation Forest for novelty, Random Forest for fault classification) | Fast, interpretable, no GPU required |
| Edge orchestration | Docker Compose | Single-host simplicity; K3s avoided (overkill for one edge) |
| MEC platform | oneM2M + ETSI MEC | Provided by competition; tinyIoT or Mobius reference |

---

## 3. Team Development Capability

### Team Composition
- **[TODO: Team member 1]**: Role (e.g., firmware & sensors), background
- **[TODO: Team member 2]**: Role (e.g., edge AI), background

### Relevant Coursework
- Sensors & Measurement Systems
- Embedded Systems / Microcontroller Programming
- Internet of Things
- AI IoT Lab
- Machine Learning

### Technical Experience
- Python, Docker, Docker Compose
- Arduino sensor interfacing and serial communication
- Signal processing (FFT, filtering)
- Machine learning model training and deployment
- Web development (HTML, JavaScript for dashboard)

### Project Timeline
The team is dedicated to this competition for the full 7-week development window (10/5–11/20), with preparation starting at application submission (9/28).

---

## 4. Expected Effects

### Economic Impact
Early fault detection prevents cascading failures, reducing unplanned maintenance cost by 30–50% (industry data). Sensors cost €20–€50 each, and the software is open-source, bringing the total entry cost to under €5k per site, down from the €50k–€500k that commercial PdM solutions charge. This opens PdM to small manufacturers and logistics operators who were previously priced out.

### Interoperability & Open Standards
Because data follows oneM2M, equipment from different manufacturers (motors, conveyors, AGVs) and third-party analytics tools coexist on one platform. The open-source implementation is a reference for other developers, reducing the adoption barrier for oneM2M and ETSI MEC.

As a planned platform-extensibility demonstration, a second independent service (PolaGrid, a daylight-control application) may register alongside EdgePdM on the same MN-CSE and MEC service registry if development time allows, showing the architecture supports multiple standards-based AIoT applications, not just one.

### Edge Computing Efficiency
- **Latency**: Inference at the edge (< 200ms) is 10–50× faster than cloud round-trip, which matters for real-time control.
- **Bandwidth**: Raw vibration data (1,000 samples/sec) stays local; only 1-second FFT-feature CINs, alerts, and metadata go to the cloud.
- **Cost**: Reduced cloud egress and compute charges compared to cloud-centric approaches.

The open-source code and public documentation help developers and companies adopt oneM2M and ETSI MEC standards.

---

## Appendix: Architecture Diagram & Timelines

See attached:
- `architecture-dual-scenario.png`: Visual architecture with factory and logistics variants
- `development-timeline.md`: Detailed week-by-week breakdown
- `tutorial-factory.md`: Factory deployment guide (CC BY 4.0)
- `tutorial-logistics.md`: Logistics deployment guide (CC BY 4.0)

---

## Contact

**Primary contact**:  
Name: [TODO]  
Email: okju3369@gmail.com  
Phone: [TODO]  

**Repository**:  
(Will be provided upon team selection)

---

*Submitted: September 28, 2026*

