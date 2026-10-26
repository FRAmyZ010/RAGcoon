"""
Module: rag_config.py
Description:
    Unified Hyperparameter Configuration Manager & Preset Profiles for RAGcoon.
    Enables Hyperparameter Sensitivity Analysis & Ablation Studies for:
      - Retrieval: top_k, rerank_top_n, hybrid enable, reranker enable, boilerplate filter
      - Context: max_context_chunks, max_chunks_per_project, min_score
      - Generation: llm_provider, llm_model, temperature, num_predict, prompt_preset
"""

import os
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RAGConfig:
    """Dataclass holding all tunable runtime hyperparameters for the RAG pipeline."""

    # 1. Retrieval Hyperparameters
    top_k: int = 15
    rerank_top_n: int = 5
    collection_name: str = "embedding_evaluation"
    enable_hybrid: bool = True  # BM25 Sparse + E5 Dense (False = Dense Only)
    enable_bm25_only: bool = False  # Pure Sparse BM25 Only (True = Skip E5 Dense Vector)
    enable_reranker: bool = True  # Cross-Encoder Reranker (False = Skip Reranking)
    enable_boilerplate_filter: bool = True  # Pre-rerank boilerplate suppression
    enable_fast_path: bool = True  # Direct deterministic metadata bypass

    # 2. Context & Chunk Quota Hyperparameters
    max_context_chunks: int = 5
    max_chunks_per_project: int = 2
    min_score: float = 0.0001

    # 3. Generation & LLM Hyperparameters
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gemma3:4b"))
    temperature: float = 0.0
    num_predict: int = 512
    prompt_preset: str = "balanced"  # 'concise', 'balanced', 'deep_academic', 'step_by_step'
    system_prompt_override: Optional[str] = None

    # Metadata
    profile_name: str = "custom"
    description: str = "Custom user-defined configuration"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RAGConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def save_json(self, file_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_json(cls, file_path: str) -> "RAGConfig":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def clone(self) -> "RAGConfig":
        return deepcopy(self)


# =========================================================================
# Preset Profiles for Hyperparameter Sensitivity & Ablation Studies
# =========================================================================

CONFIG_PRESETS: dict[str, RAGConfig] = {
    # 1. Baseline: Balanced Standard
    "precision_hybrid": RAGConfig(
        profile_name="precision_hybrid",
        description="ค่ามาตรฐานสมดุล (Baseline): Hybrid RRF, Top-K=15, Top-N=5, Chunk=5, Balanced Prompt",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 2. Fast-Mode: Latency & Speed Optimized
    "fast_mode": RAGConfig(
        profile_name="fast_mode",
        description="เน้นความเร็วสูงสุด (Speed-Optimized): Top-K=10, Top-N=3, Chunk=3, Prompt กระชับ, Output=256",
        top_k=10,
        rerank_top_n=3,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=3,
        max_chunks_per_project=1,
        num_predict=256,
        temperature=0.0,
        prompt_preset="concise",
    ),

    # 3. Deep-Academic: Maximum Depth & Information Richness
    "deep_academic": RAGConfig(
        profile_name="deep_academic",
        description="เน้นความลึกเชิงวิชาการ (Deep-Academic): Top-K=25, Top-N=8, Chunk=8, Prompt แจกแจงโครงสร้าง, Output=1024",
        top_k=25,
        rerank_top_n=8,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=8,
        max_chunks_per_project=4,
        num_predict=1024,
        temperature=0.0,
        prompt_preset="deep_academic",
    ),

    # 4. Ablation Study 1: Dense Only (No BM25 Keyword Search)
    "ablation_dense_only": RAGConfig(
        profile_name="ablation_dense_only",
        description="[Ablation 1] ตัด Sparse BM25 ออก (Dense Vector Only) เพื่อวัดผลของ Hybrid Search",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=False,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 4b. Ablation Study 1b: BM25 Only (No Dense E5 Vector Search)
    "ablation_bm25_only": RAGConfig(
        profile_name="ablation_bm25_only",
        description="[Ablation 1b] ตัด Dense Vector E5 ออก (Sparse BM25 Only) เพื่อวัดผลของคีย์เวิร์ดล้วน",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=False,
        enable_bm25_only=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 5. Ablation Study 2: No Reranker (Raw Vector/BM25 Ranking Only)
    "ablation_no_rerank": RAGConfig(
        profile_name="ablation_no_rerank",
        description="[Ablation 2] ตัด Cross-Encoder Reranker ออก เพื่อวัดผลของ Neural Re-ranking",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=True,
        enable_reranker=False,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 6. Ablation Study 3: No Boilerplate Filter (Unfiltered Noise)
    "ablation_no_filter": RAGConfig(
        profile_name="ablation_no_filter",
        description="[Ablation 3] ปิด Boilerplate Filter เพื่อวัดผลกระทบจากขยะเอกสาร (TOC, อ้างอิง, ลายมือชื่อ)",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=False,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 7. LLM Model Benchmark: Ollama Qwen 3 (4B)
    "model_qwen3": RAGConfig(
        profile_name="model_qwen3",
        description="ทดสอบโมเดล Ollama Qwen 3 (4B) ในการตอบและวิเคราะห์เหตุผล",
        llm_provider="ollama",
        llm_model="qwen3:4b",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 8. LLM Model Benchmark: Google Gemini (Cloud)
    "model_gemini": RAGConfig(
        profile_name="model_gemini",
        description="ทดสอบโมเดล Google Gemini Cloud API (gemini-3.5-flash)",
        llm_provider="gemini",
        llm_model="gemini-3.5-flash",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 9. LLM Model Benchmark: OpenAI ChatGPT (Cloud)
    "model_openai": RAGConfig(
        profile_name="model_openai",
        description="ทดสอบโมเดล OpenAI ChatGPT Cloud API (gpt-4o-mini)",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        top_k=15,
        rerank_top_n=5,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=5,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 10. Custom Tuned Profile: "custom_balanced_boost" (การปรับแต่งอิสระที่บันทึกไว้ทดสอบ)
    "custom_balanced_boost": RAGConfig(
        profile_name="custom_balanced_boost",
        description="การปรับแต่งอิสระ (Custom Tuned Optimization): Top-K=20, Top-N=6, Max Chunks=4, Quota=2, Filter=On, Fast-Path=On",
        top_k=20,
        rerank_top_n=6,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=4,
        max_chunks_per_project=2,
        min_score=0.0001,
        llm_provider="ollama",
        llm_model="gemma3:4b",
        temperature=0.0,
        num_predict=512,
        prompt_preset="balanced",
    ),

    # 11. Empirical Optimal Tuned Profile (Two-Stage Parameter Sweep Winner for gemma3:4b)
    "optimal_tuned_gemma3_4b": RAGConfig(
        profile_name="optimal_tuned_gemma3_4b",
        description="Optimal Empirical Config (Stage 1+2 Winner): Top-K=15, Top-N=10, Chunks=6, Quota=2, Preset=deep_academic, Temp=0.0",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_bm25_only=False,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        min_score=0.0001,
        llm_provider="ollama",
        llm_model="gemma3:4b",
        temperature=0.0,
        num_predict=512,
        prompt_preset="deep_academic",
    ),
}


# Global active runtime configuration
_ACTIVE_CONFIG: RAGConfig = deepcopy(CONFIG_PRESETS["precision_hybrid"])


def get_active_config() -> RAGConfig:
    """Retrieve the currently active RAG pipeline configuration."""
    global _ACTIVE_CONFIG
    return _ACTIVE_CONFIG


def set_active_config(config: RAGConfig) -> None:
    """Set the globally active RAG pipeline configuration."""
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = config.clone()


def get_config_preset(name: str) -> RAGConfig:
    """Get a copy of a predefined configuration preset."""
    if name not in CONFIG_PRESETS:
        raise KeyError(f"Preset '{name}' not found. Available: {list(CONFIG_PRESETS.keys())}")
    return CONFIG_PRESETS[name].clone()


def list_available_presets() -> list[dict[str, Any]]:
    """List all presets with their profile name and description for UI and API selection."""
    return [
        {
            "profile_name": k,
            "description": v.description,
            "top_k": v.top_k,
            "rerank_top_n": v.rerank_top_n,
            "enable_hybrid": v.enable_hybrid,
            "enable_reranker": v.enable_reranker,
            "enable_boilerplate_filter": v.enable_boilerplate_filter,
            "enable_fast_path": v.enable_fast_path,
            "prompt_preset": v.prompt_preset,
            "llm_provider": v.llm_provider,
            "llm_model": v.llm_model,
        }
        for k, v in CONFIG_PRESETS.items()
    ]

