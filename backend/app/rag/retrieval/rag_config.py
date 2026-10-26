"""
Module: rag_config.py
Description:
    Unified Hyperparameter Configuration Manager & Preset Profiles for RAGcoon.
    Includes the Top-3 Empirical Winners from the RTX 3050 Ti (4GB VRAM) Benchmark:
      1. winner_rank1_llama3_2_3b: Meta Llama 3.2 (3B) [47.6 TPS / 5.60s | Suitability 87.70] (Default)
      2. winner_rank2_qwen2_5_3b: Alibaba Qwen 2.5 (3B) [60.0 TPS / 1.9GB VRAM | Suitability 82.48]
      3. winner_rank3_gemma3_4b_academic: Google Gemma 3 (4B) [Quality 84.67 | Deep Academic Champion]
"""

import json
import os
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_CONFIG_FILE = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "evaluation", "results", "custom_rag_configs.json")
)


@dataclass
class RAGConfig:
    """Dataclass holding all tunable runtime hyperparameters for the RAG pipeline."""

    # 1. Retrieval Hyperparameters (Empirical Optimal Defaults from Stage 1 Sweeps)
    top_k: int = 15
    rerank_top_n: int = 10
    collection_name: str = "embedding_evaluation"
    enable_hybrid: bool = True  # BM25 Sparse + E5 Dense (False = Dense Only)
    enable_bm25_only: bool = False  # Pure Sparse BM25 Only (True = Skip E5 Dense Vector)
    enable_reranker: bool = True  # Cross-Encoder Reranker (False = Skip Reranking)
    enable_boilerplate_filter: bool = True  # Pre-rerank boilerplate suppression
    enable_fast_path: bool = True  # Direct deterministic metadata bypass

    # 2. Context & Chunk Quota Hyperparameters (Empirical Optimal Defaults from Stage 2 Sweeps)
    max_context_chunks: int = 6
    max_chunks_per_project: int = 2
    min_score: float = 0.0001

    # 3. Generation & LLM Hyperparameters (Winner Default: llama3.2:3b on RTX 3050 Ti)
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3.2:3b"))
    temperature: float = 0.0
    num_predict: int = 512
    prompt_preset: str = "balanced"  # 'concise', 'balanced', 'deep_academic', 'step_by_step'
    system_prompt_override: Optional[str] = None

    # Metadata
    profile_name: str = "winner_rank1_llama3_2_3b"
    description: str = "🏆 แนะนำอันดับ 1 (Suitability 87.70): Llama 3.2 (3B) + Top-K=15, Top-N=10, Chunks=6, Quota=2 (เร็ว 47.6 TPS / 5.60s)"

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
# Preset Profiles (Featuring the Top-3 Empirical Winners as Defaults)
# =========================================================================

CONFIG_PRESETS: dict[str, RAGConfig] = {
    # 🥇 WINNER RANK 1: Best Overall Speed & Precision (Suitability = 87.70)
    "winner_rank1_llama3_2_3b": RAGConfig(
        profile_name="winner_rank1_llama3_2_3b",
        description="🥇 ชนะเลิศอันดับ 1 (Suitability 87.70): Llama 3.2 (3B, 2.0GB) + Top-K=15, Top-N=10, Chunks=6, Quota=2, Balanced, Temp=0.0 (เร็ว 47.6 TPS / 5.60s, Phrase Recall 86.7%)",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="llama3.2:3b",
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 🥈 WINNER RANK 2: Ultra-Fast Speed Champion (Suitability = 82.48, Speed = 60.0 TPS)
    "winner_rank2_qwen2_5_3b": RAGConfig(
        profile_name="winner_rank2_qwen2_5_3b",
        description="🥈 รองชนะเลิศอันดับ 2 (Suitability 82.48): Qwen 2.5 (3B, 1.9GB) + Top-K=15, Top-N=10, Chunks=6, Quota=2, Balanced, Temp=0.0 (ปั่น Token สูงสุด 60.0 TPS, ประหยัด VRAM)",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="qwen2.5:3b",
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),

    # 🥉 WINNER RANK 3: Academic Thai Language & Depth Champion (Quality = 84.67)
    "winner_rank3_gemma3_4b_academic": RAGConfig(
        profile_name="winner_rank3_gemma3_4b_academic",
        description="🥉 อันดับ 3 / 🏅 แชมป์คุณภาพเนื้อหาสูงสุด (Quality 84.67 | Stage 2 Winner 83.75): Gemma 3 (4B, 3.3GB) + Top-K=15, Top-N=10, Chunks=6, Quota=2, Deep-Academic, Temp=0.0 (เรียบเรียงภาษาไทยและตารางวิชาการละเอียดที่สุด)",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="gemma3:4b",
        num_predict=512,
        temperature=0.0,
        prompt_preset="deep_academic",
    ),

    # Aliases for convenience and backward compatibility
    "optimal_llama3_2_3b": RAGConfig(
        profile_name="optimal_llama3_2_3b",
        description="Alias สำหรับ winner_rank1_llama3_2_3b (โหมดแนะนำค่าเริ่มต้น)",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="llama3.2:3b",
        temperature=0.0,
        prompt_preset="balanced",
    ),
    "optimal_tuned_gemma3_4b": RAGConfig(
        profile_name="optimal_tuned_gemma3_4b",
        description="Alias สำหรับ winner_rank3_gemma3_4b_academic (แชมป์วิชาการภาษาไทย)",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="gemma3:4b",
        temperature=0.0,
        prompt_preset="deep_academic",
    ),

    # Standard / Classical Profiles (Updated with Optimal Parameters)
    "precision_hybrid": RAGConfig(
        profile_name="precision_hybrid",
        description="โหมดมาตรฐานสมดุล (Updated): Top-K=15, Top-N=10, Chunks=6, Quota=2, Balanced Prompt",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),
    "fast_mode": RAGConfig(
        profile_name="fast_mode",
        description="เน้นความเร็วสูงสุด (Speed-Optimized): Llama 3.2 (3B), Top-K=10, Top-N=3, Chunks=3, Prompt กระชับ",
        top_k=10,
        rerank_top_n=3,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=3,
        max_chunks_per_project=1,
        llm_provider="ollama",
        llm_model="llama3.2:3b",
        num_predict=256,
        temperature=0.0,
        prompt_preset="concise",
    ),
    "deep_academic": RAGConfig(
        profile_name="deep_academic",
        description="เน้นความลึกเชิงวิชาการ (Deep-Academic): Gemma 3 (4B), Top-K=15, Top-N=10, Chunks=6, Quota=2, Output=1024",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="gemma3:4b",
        num_predict=1024,
        temperature=0.0,
        prompt_preset="deep_academic",
    ),

    # Ultra-Lightweight Control Profile (1B Parameter / 130.7 TPS)
    "ultra_light_gemma3_1b": RAGConfig(
        profile_name="ultra_light_gemma3_1b",
        description="โหมดน้ำหนักเบาพิเศษ (Ultra-Lightweight 1B): Gemma 3 (1B, 0.8GB) + ความเร็ว 130.7 TPS / 6.86s",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model="gemma3:1b",
        num_predict=256,
        temperature=0.0,
        prompt_preset="concise",
    ),

    # Ablation Study Profiles
    "ablation_dense_only": RAGConfig(
        profile_name="ablation_dense_only",
        description="[Ablation 1] ตัด Sparse BM25 ออก (Dense Vector Only) เพื่อวัดผลของ Hybrid Search",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=False,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),
    "ablation_bm25_only": RAGConfig(
        profile_name="ablation_bm25_only",
        description="[Ablation 1b] ตัด Dense Vector E5 ออก (Sparse BM25 Only) เพื่อวัดผลของคีย์เวิร์ดล้วน",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=False,
        enable_bm25_only=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),
    "ablation_no_rerank": RAGConfig(
        profile_name="ablation_no_rerank",
        description="[Ablation 2] ตัด Cross-Encoder Reranker ออก เพื่อวัดผลของ Neural Re-ranking",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=False,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),
    "ablation_no_filter": RAGConfig(
        profile_name="ablation_no_filter",
        description="[Ablation 3] ปิด Boilerplate Filter เพื่อวัดผลกระทบจากขยะเอกสาร (TOC, อ้างอิง, ลายมือชื่อ)",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=False,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        num_predict=512,
        temperature=0.0,
        prompt_preset="balanced",
    ),
}

# The global active runtime configuration (Defaults to Rank 1 Winner)
_ACTIVE_CONFIG: RAGConfig = deepcopy(CONFIG_PRESETS["winner_rank1_llama3_2_3b"])


def get_active_config() -> RAGConfig:
    """Retrieve the currently active RAG pipeline configuration."""
    global _ACTIVE_CONFIG
    return _ACTIVE_CONFIG


def get_active_rag_config() -> RAGConfig:
    """Convenience alias for get_active_config."""
    return get_active_config()


def set_active_config(config: RAGConfig) -> None:
    """Set the globally active RAG pipeline configuration."""
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = config.clone()


def set_active_rag_config_by_name(name: str) -> RAGConfig:
    """Set the active configuration by preset or custom profile name."""
    cfg = get_config_by_name(name)
    set_active_config(cfg)
    return cfg


def get_config_preset(name: str) -> RAGConfig:
    """Get a copy of a predefined configuration preset."""
    if name not in CONFIG_PRESETS:
        raise KeyError(f"Preset '{name}' not found. Available: {list(CONFIG_PRESETS.keys())}")
    return CONFIG_PRESETS[name].clone()


def get_top3_winner_presets() -> dict[str, RAGConfig]:
    """Return the Top-3 Empirical Winners from the benchmark."""
    return {
        "winner_rank1_llama3_2_3b": CONFIG_PRESETS["winner_rank1_llama3_2_3b"].clone(),
        "winner_rank2_qwen2_5_3b": CONFIG_PRESETS["winner_rank2_qwen2_5_3b"].clone(),
        "winner_rank3_gemma3_4b_academic": CONFIG_PRESETS["winner_rank3_gemma3_4b_academic"].clone(),
    }


def load_custom_configs() -> dict[str, RAGConfig]:
    """Load custom saved profiles from disk."""
    if not os.path.exists(CUSTOM_CONFIG_FILE):
        return {}
    try:
        with open(CUSTOM_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: RAGConfig.from_dict(v) for k, v in data.items()}
    except Exception:
        return {}


def save_custom_config(
    profile_name: str,
    overrides: dict[str, Any],
    base_preset: str = "winner_rank1_llama3_2_3b",
    set_active: bool = True,
) -> RAGConfig:
    """Create or update a custom profile, persist to disk, and optionally activate it."""
    base_cfg = get_config_by_name(base_preset)
    merged_data = base_cfg.to_dict()
    merged_data.update(overrides)
    merged_data["profile_name"] = profile_name

    new_cfg = RAGConfig.from_dict(merged_data)
    customs = load_custom_configs()
    customs[profile_name] = new_cfg

    os.makedirs(os.path.dirname(CUSTOM_CONFIG_FILE), exist_ok=True)
    with open(CUSTOM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({k: v.to_dict() for k, v in customs.items()}, f, ensure_ascii=False, indent=2)

    if set_active:
        set_active_config(new_cfg)
    return new_cfg


def delete_custom_config(profile_name: str) -> bool:
    """Delete a custom profile from disk."""
    customs = load_custom_configs()
    if profile_name not in customs:
        return False
    del customs[profile_name]
    os.makedirs(os.path.dirname(CUSTOM_CONFIG_FILE), exist_ok=True)
    with open(CUSTOM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({k: v.to_dict() for k, v in customs.items()}, f, ensure_ascii=False, indent=2)
    return True


def get_config_by_name(name: str) -> RAGConfig:
    """Look up a configuration from presets or custom saved profiles."""
    if name in CONFIG_PRESETS:
        return CONFIG_PRESETS[name].clone()
    customs = load_custom_configs()
    if name in customs:
        return customs[name].clone()
    raise KeyError(f"Configuration profile '{name}' not found.")


def list_all_configs() -> dict[str, Any]:
    """Return both presets and custom configurations for API / UI dropdowns."""
    presets_summary = {k: v.to_dict() for k, v in CONFIG_PRESETS.items()}
    customs_summary = {k: v.to_dict() for k, v in load_custom_configs().items()}
    return {
        "presets": presets_summary,
        "custom_profiles": customs_summary,
        "top3_winners": [
            "winner_rank1_llama3_2_3b",
            "winner_rank2_qwen2_5_3b",
            "winner_rank3_gemma3_4b_academic",
        ],
    }


def list_available_presets() -> list[dict[str, Any]]:
    """List presets for backward compatibility."""
    return [
        {
            "profile_name": k,
            "description": v.description,
            "top_k": v.top_k,
            "rerank_top_n": v.rerank_top_n,
            "max_context_chunks": v.max_context_chunks,
            "max_chunks_per_project": v.max_chunks_per_project,
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
