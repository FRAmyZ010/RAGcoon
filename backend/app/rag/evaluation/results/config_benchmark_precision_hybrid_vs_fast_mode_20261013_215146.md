# 📊 รายงานผลการประเมินการตั้งค่า RAG และการศึกษาผลเชิงประจักษ์ (RAG Configuration & Ablation Study)
**วันที่ประเมินผล:** 2026-10-13 21:51:46  
**เอกสารประกอบ:** วิทยานิพนธ์บทที่ 4 (Chapter 4: Results & Evaluation)

---

## 1. การกำหนดค่าระบบที่นำมาเปรียบเทียบ (Configuration Profiles)

| คุณสมบัติ (Hyperparameter) | Baseline: `precision_hybrid` | Candidate: `fast_mode` |
|---|---|---|
| **คำอธิบาย** | ค่ามาตรฐานสมดุล (Baseline): Hybrid RRF, Top-K=15, Top-N=5, Chunk=5, Balanced Prompt | เน้นความเร็วสูงสุด (Speed-Optimized): Top-K=10, Top-N=3, Chunk=3, Prompt กระชับ, Output=256 |
| **LLM Provider / Model** | `ollama` / `gemma3:4b` | `ollama` / `gemma3:4b` |
| **Retrieval Top-K** | 15 | 10 |
| **Rerank Top-N** | 5 | 3 |
| **Hybrid Search (BM25 + Dense)** | เปิดใช้งาน (Enabled) | เปิดใช้งาน (Enabled) |
| **Neural Re-ranking (Cross-Encoder)** | เปิดใช้งาน (Enabled) | เปิดใช้งาน (Enabled) |
| **Boilerplate Suppression Filter** | เปิดใช้งาน (Enabled) | เปิดใช้งาน (Enabled) |
| **Max Context Chunks** | 5 | 3 |
| **Prompt Style Preset** | `balanced` | `concise` |
| **Max Predict Tokens** | 512 | 256 |

---

## 2. ตารางสรุปภาพรวมเปรียบเทียบดัชนีชี้วัด (Evaluation Overview & Delta Analysis)

| ดัชนีชี้วัดหลัก (Key Metric) | Baseline (`precision_hybrid`) | Candidate (`fast_mode`) | ส่วนต่าง (Delta $\Delta$) |
|---|---|---|---|
| **คะแนนคุณภาพเฉลี่ย (Quality Score)** | **95.00 / 100** | **100.00 / 100** | **+5.00 pts** |
| **เวลาหน่วงการตอบสนองเฉลี่ย (Total Latency)** | 1.948 s | 0.221 s | **-1.727 s (8.81x)** |
| **อัตราการค้นพบเอกสารถูกต้อง (Hit Rate@N)** | 100.0% | 100.0% | +0.0% |
| **ความครอบคลุมข้อเท็จจริง (Keyword Recall)** | 100.0% | 100.0% | +0.0% |
| **ความเร็วสร้างโทเคน (Generation Speed)** | 0.0 TPS | 0.0 TPS | +0.0 TPS |

---

## 3. รายละเอียดผลทดสอบจำแนกรายข้อ (Per-Test Granular Results)

| รหัสข้อ | หมวดหมู่ | คำถามทดสอบ (Query) | Base Score | Cand Score | $\Delta$ Score | Base Time | Cand Time |
|---|---|---|---|---|---|---|---|
| `GT-04` | Fast-Path Metadata | "ใครเป็นที่ปรึกษาของ The LoRaWAN" | 95.0 | 100.0 | **+5.0** | 1.948s | 0.221s |

---

## 4. ข้อสังเกตและการวิเคราะห์ผล (Analytical Discussion)

1. **ผลกระทบต่อคุณภาพคำตอบ (Answer Quality Impact):**
   - การเปลี่ยนแปลงคอนฟิกส่งผลให้คะแนนเฉลี่ยเปลี่ยนไป **+5.00 คะแนน**
2. **ประสิทธิภาพด้านเวลาและการประมวลผล (Latency & Throughput Trade-off):**
   - อัตราส่วนความเร็วในการทำงาน (Speedup Ratio): **8.81x**
3. **การนำไปอ้างอิงในบทที่ 4:**
   - ข้อมูลนี้สามารถนำไปเขียนเป็นตารางการวิเคราะห์ความไวของพารามิเตอร์ (Sensitivity Analysis) และการศึกษาการตัดทอนโมดูล (Ablation Study) ได้ทันที
