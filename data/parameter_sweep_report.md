# 📊 RAGcoon Two-Stage Parameter Sweep & Ablation Benchmark Report
- **Generated At:** 2026-10-26 18:02:55
- **Primary LLM Model:** `ollama/gemma3:4b`
- **Optimal Profile Saved:** `optimal_tuned_gemma3_4b`

## 🏆 Optimal Configuration Discovered (`best_rag_config.json`)
| Parameter | Optimal Value | Stage Determined |
| :--- | :--- | :--- |
| `top_k` | **15** | Stage 1 (Exp 1: Wide Retrieval Pool Sweep) |
| `rerank_top_n` | **10** | Stage 1 (Exp 2: Reranker Cutoff Sweep) |
| `enable_hybrid` | **True** | Stage 1 (Exp 3: Component Ablation Matrix) |
| `enable_reranker` | **True** | Stage 1 (Exp 3: Component Ablation Matrix) |
| `enable_boilerplate_filter` | **True** | Stage 1 (Exp 3: Component Ablation Matrix) |
| `enable_fast_path` | **True** | Stage 1 (Exp 3: Component Ablation Matrix) |
| `max_context_chunks` | **6** | Stage 2 (Exp 4: Context & Quota Sweep) |
| `max_chunks_per_project` | **2** | Stage 2 (Exp 4: Context & Quota Sweep) |
| `prompt_preset` | **`deep_academic`** | Stage 2 (Exp 5: Prompt & Temperature Sweep) |
| `temperature` | **0.0** | Stage 2 (Exp 5: Prompt & Temperature Sweep) |
| `num_predict` | **512** | Stage 2 (Exp 5: Prompt & Temperature Sweep) |

## 🔍 Stage 1: Retrieval-Side Parameter Sweep Results
| Exp Group | Parameter Setting | top_k | top_n | Hit Rate (%) | MRR | Precision@N (%) | Recall@N (%) | Noise (%) | Avg Search (ms) | Composite Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Exp 1: top_k Sweep | **top_k = 100** | 100 | 5 | 92.3% | 0.8846 | 76.9% | 88.5% | 0.0% | 1717.3 | **85.17** |
| Exp 1: top_k Sweep | **top_k = 50** | 50 | 5 | 92.3% | 0.8718 | 76.9% | 88.5% | 0.0% | 600.0 | **87.79** |
| Exp 1: top_k Sweep | **top_k = 30** | 30 | 5 | 92.3% | 0.8718 | 76.9% | 88.5% | 0.0% | 538.9 | **87.95** |
| Exp 1: top_k Sweep | **top_k = 15** | 15 | 5 | 92.3% | 0.8718 | 76.9% | 88.5% | 0.0% | 463.7 | **88.15** |
| Exp 1: top_k Sweep | **top_k = 10** | 10 | 5 | 84.6% | 0.7885 | 68.6% | 88.5% | 8.8% | 433.9 | **81.67** |
| Exp 1: top_k Sweep | **top_k = 5** | 5 | 5 | 76.9% | 0.5577 | 46.1% | 88.5% | 37.7% | 405.8 | **66.67** |
| Exp 2: rerank_top_n Sweep | **rerank_top_n = 30** | 30 | 30 | 100.0% | 0.8795 | 74.6% | 100.0% | 0.0% | 540.7 | **87.75** |
| Exp 2: rerank_top_n Sweep | **rerank_top_n = 15** | 30 | 15 | 100.0% | 0.8795 | 74.3% | 100.0% | 0.0% | 539.8 | **89.56** |
| Exp 2: rerank_top_n Sweep | **rerank_top_n = 10** | 30 | 10 | 100.0% | 0.8795 | 75.6% | 96.2% | 0.0% | 542.5 | **90.05** |
| Exp 2: rerank_top_n Sweep | **rerank_top_n = 5** | 30 | 5 | 92.3% | 0.8718 | 76.9% | 88.5% | 0.0% | 541.0 | **87.94** |
| Exp 2: rerank_top_n Sweep | **rerank_top_n = 3** | 30 | 3 | 92.3% | 0.8718 | 76.9% | 88.5% | 0.0% | 537.6 | **87.95** |
| Exp 2: rerank_top_n Sweep | **rerank_top_n = 1** | 30 | 1 | 84.6% | 0.8462 | 84.6% | 80.8% | 0.0% | 537.7 | **86.16** |
| Exp 3: Component Ablation | **Full Pipeline (All Enabled)** | 15 | 10 | 100.0% | 0.9231 | 82.5% | 96.2% | 0.0% | 312.4 | **91.64** |
| Exp 3: Component Ablation | **Dense Only (No BM25)** | 15 | 10 | 84.6% | 0.7769 | 70.0% | 84.6% | 1.9% | 382.8 | **81.85** |
| Exp 3: Component Ablation | **BM25 Only (No E5 Vector)** | 15 | 10 | 84.6% | 0.7949 | 69.9% | 84.6% | 1.9% | 207.7 | **82.74** |
| Exp 3: Component Ablation | **No Reranker (Skip Cross-Encoder)** | 15 | 10 | 84.6% | 0.7436 | 68.5% | 88.5% | 1.7% | 246.2 | **80.93** |
| Exp 3: Component Ablation | **No Boilerplate Filter** | 15 | 10 | 84.6% | 0.7372 | 62.0% | 84.6% | 25.0% | 435.1 | **76.26** |
| Exp 3: Component Ablation | **No Fast-Path Shortcut** | 15 | 10 | 92.3% | 0.8795 | 75.6% | 96.2% | 0.0% | 555.8 | **87.35** |
| Exp 3: Component Ablation | **Legacy Raw Baseline (All Off)** | 15 | 10 | 76.9% | 0.5833 | 48.0% | 76.9% | 43.6% | 322.2 | **65.87** |

## 🤖 Stage 2: LLM Generation-Side Parameter Sweep Results (`gemma3:4b`)
| Exp Group | Parameter Setting | Chunks | Quota/Proj | Preset | Temp | Quality (0-100) | Phrase Recall (%) | Multi-Proj (%) | In Tokens | LLM Latency (s) | Composite Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Exp 4: Context & Quota Sweep | **Chunks=15, Quota=5 (Extra Wide)** | 15 | 5 | `balanced` | 0.0 | 83.0 | 80.0% | 100.0% | 1721 | 15.49s | **79.83** |
| Exp 4: Context & Quota Sweep | **Chunks=10, Quota=3 (Wide)** | 10 | 3 | `balanced` | 0.0 | 82.4 | 80.0% | 100.0% | 1474 | 14.91s | **80.17** |
| Exp 4: Context & Quota Sweep | **Chunks=6, Quota=2 (Balanced Boost)** | 6 | 2 | `balanced` | 0.0 | 84.7 | 86.7% | 100.0% | 1675 | 19.23s | **83.75** |
| Exp 4: Context & Quota Sweep | **Chunks=5, Quota=2 (Standard Baseline)** | 5 | 2 | `balanced` | 0.0 | 81.2 | 80.0% | 100.0% | 1586 | 16.89s | **81.41** |
| Exp 4: Context & Quota Sweep | **Chunks=4, Quota=2 (Compact Balanced)** | 4 | 2 | `balanced` | 0.0 | 82.9 | 86.7% | 100.0% | 1497 | 17.81s | **83.53** |
| Exp 4: Context & Quota Sweep | **Chunks=2, Quota=1 (Ultra Minimal)** | 2 | 1 | `balanced` | 0.0 | 82.4 | 80.0% | 100.0% | 1187 | 16.01s | **80.53** |
| Exp 4: Context & Quota Sweep | **Chunks=6, Quota=6 (Uncapped / No Quota)** | 6 | 6 | `balanced` | 0.0 | 87.1 | 86.7% | 100.0% | 2177 | 19.93s | **81.25** |
| Exp 5: Prompt & Temperature Sweep | **Preset=concise, Temp=0.0, MaxTokens=256** | 6 | 2 | `concise` | 0.0 | 80.0 | 80.0% | 100.0% | 1220 | 12.00s | **82.64** |
| Exp 5: Prompt & Temperature Sweep | **Preset=balanced, Temp=0.0, MaxTokens=384** | 6 | 2 | `balanced` | 0.0 | 82.4 | 80.0% | 100.0% | 1187 | 16.01s | **83.03** |
| Exp 5: Prompt & Temperature Sweep | **Preset=deep_academic, Temp=0.0, MaxTokens=512** | 6 | 2 | `deep_academic` | 0.0 | 82.4 | 80.0% | 100.0% | 1216 | 13.58s | **83.50** |
| Exp 5: Prompt & Temperature Sweep | **Preset=step_by_step, Temp=0.0, MaxTokens=384** | 6 | 2 | `step_by_step` | 0.0 | 82.4 | 80.0% | 100.0% | 1187 | 15.91s | **83.06** |
| Exp 5: Prompt & Temperature Sweep | **Preset=balanced, Temp=0.2, MaxTokens=384** | 6 | 2 | `balanced` | 0.2 | 82.4 | 80.0% | 100.0% | 1187 | 16.20s | **82.99** |
| Exp 5: Prompt & Temperature Sweep | **Preset=balanced, Temp=0.5, MaxTokens=384** | 6 | 2 | `balanced` | 0.5 | 82.4 | 80.0% | 100.0% | 1187 | 16.52s | **82.92** |
