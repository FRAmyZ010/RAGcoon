# 📊 รายงานผลการประเมินการตั้งค่า RAG และการศึกษาผลเชิงประจักษ์ (RAG Configuration & Ablation Study)
**วันที่ประเมินผล:** 2026-10-22 16:56:13  
**เอกสารประกอบ:** วิทยานิพนธ์บทที่ 4 (Chapter 4: Results & Evaluation)

---

## 1. การกำหนดค่าระบบที่นำมาเปรียบเทียบ (Configuration Profiles)

| คุณสมบัติ (Hyperparameter) | Baseline: `precision_hybrid` | Candidate: `custom_balanced_boost` |
|---|---|---|
| **คำอธิบาย** | ค่ามาตรฐานสมดุล (Baseline): Hybrid RRF, Top-K=15, Top-N=5, Chunk=5, Balanced Prompt | การปรับแต่งอิสระ (Custom Tuned Optimization): Top-K=20, Top-N=6, Max Chunks=4, Quota=2, Filter=On, Fast-Path=On |
| **LLM Provider / Model** | `ollama` / `gemma3:4b` | `ollama` / `gemma3:4b` |
| **Retrieval Top-K** | 15 | 20 |
| **Rerank Top-N** | 5 | 6 |
| **Hybrid Search (BM25 + Dense)** | เปิดใช้งาน (Enabled) | เปิดใช้งาน (Enabled) |
| **Neural Re-ranking (Cross-Encoder)** | เปิดใช้งาน (Enabled) | เปิดใช้งาน (Enabled) |
| **Boilerplate Suppression Filter** | เปิดใช้งาน (Enabled) | เปิดใช้งาน (Enabled) |
| **Max Context Chunks** | 5 | 4 |
| **Prompt Style Preset** | `balanced` | `balanced` |
| **Max Predict Tokens** | 512 | 512 |

---

## 2. ตารางสรุปภาพรวมเปรียบเทียบดัชนีชี้วัด (Evaluation Overview & Delta Analysis)

| ดัชนีชี้วัดหลัก (Key Metric) | Baseline (`precision_hybrid`) | Candidate (`custom_balanced_boost`) | ส่วนต่าง (Delta $\Delta$) |
|---|---|---|---|
| **คะแนนคุณภาพเฉลี่ย (Quality Score)** | **90.00 / 100** | **91.25 / 100** | **+1.25 pts** |
| **เวลาหน่วงการตอบสนองเฉลี่ย (Total Latency)** | 12.673 s | 5.494 s | **-7.179 s (2.31x)** |
| **อัตราการค้นพบเอกสารถูกต้อง (Hit Rate@N)** | 100.0% | 100.0% | +0.0% |
| **ความครอบคลุมข้อเท็จจริง (Keyword Recall)** | 91.7% | 91.7% | +0.0% |
| **ความเร็วสร้างโทเคน (Generation Speed)** | 7.7 TPS | 6.4 TPS | -1.3 TPS |

---

## 3. รายละเอียดผลทดสอบจำแนกรายข้อ (Per-Test Granular Results)

| รหัสข้อ | หมวดหมู่ | คำถามทดสอบ (Query) | Base Score | Cand Score | $\Delta$ Score | Base Time | Cand Time |
|---|---|---|---|---|---|---|---|
| `GT-01` | Exact Hardware | "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง" | 80.0 | 80.0 | **+0.0** | 44.445s | 18.260s |
| `GT-02` | Advisor Typo Lookup | "อาจารสุรพลดูแลเรื่องไรบ้าง" | 100.0 | 100.0 | **+0.0** | 0.871s | 0.199s |
| `GT-04` | Fast-Path Metadata | "ใครเป็นที่ปรึกษาของ The LoRaWAN" | 100.0 | 100.0 | **+0.0** | 0.208s | 0.201s |
| `GT-06` | Anti-Hallucination Negative | "โครงงาน The LoRaWAN มีการเชื่อมต่อกับ Line Notify หรือไม่" | 80.0 | 85.0 | **+5.0** | 5.167s | 3.314s |

---

## 4. ข้อสังเกตและการวิเคราะห์ผล (Analytical Discussion)

1. **ผลกระทบต่อคุณภาพคำตอบ (Answer Quality Impact):**
   - การเปลี่ยนแปลงคอนฟิกส่งผลให้คะแนนเฉลี่ยเปลี่ยนไป **+1.25 คะแนน**
2. **ประสิทธิภาพด้านเวลาและการประมวลผล (Latency & Throughput Trade-off):**
   - อัตราส่วนความเร็วในการทำงาน (Speedup Ratio): **2.31x**
3. **การนำไปอ้างอิงในบทที่ 4:**
   - ข้อมูลนี้สามารถนำไปเขียนเป็นตารางการวิเคราะห์ความไวของพารามิเตอร์ (Sensitivity Analysis) และการศึกษาการตัดทอนโมดูล (Ablation Study) ได้ทันที
