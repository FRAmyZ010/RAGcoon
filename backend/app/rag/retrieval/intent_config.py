"""
Module: intent_config.py
Description:
    Granular Intent Configuration & Hyperparameter Manager for RAGcoon.
    Provides fine-grained, per-intent control over:
      - Retrieval: top_k, rerank_top_n, enable_fast_path, enable_hybrid, enable_boilerplate_filter
      - Context & Quotas: max_context_chunks, max_chunks_per_project, max_total_projects, min_score, preserve_raw_code
      - Generation: temperature, num_predict, thinking, prompt_preset, custom_system_instruction
"""

import os
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class IntentConfig:
    """Granular configuration for a specific RAG query intent."""

    intent_name: str
    label_th: str
    description_th: str

    # 1. Retrieval Hyperparameters
    top_k: int = 15
    rerank_top_n: int = 5
    enable_fast_path: bool = True
    enable_hybrid: bool = True
    enable_boilerplate_filter: bool = True

    # 2. Context Quotas & Allocation
    max_context_chunks: int = 5
    max_chunks_per_project: int = 2
    max_total_projects: int = 3
    min_score: float = 0.0001
    preserve_raw_code: bool = False

    # 3. LLM Generation Hyperparameters
    temperature: float = 0.0
    num_predict: int = 512
    thinking: bool = False
    prompt_preset: str = "balanced"  # concise, balanced, deep_academic, code_focused, comparative_table
    custom_system_instruction: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntentConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def clone(self) -> "IntentConfig":
        return deepcopy(self)


# =========================================================================
# Default Granular Intent Presets
# =========================================================================

DEFAULT_INTENT_REGISTRY: dict[str, IntentConfig] = {
    "FACTOID": IntentConfig(
        intent_name="FACTOID",
        label_th="ค้นหาข้อเท็จจริงจำเพาะ (Factoid / Direct Lookup)",
        description_th="สำหรับคำถามสั้นๆ เช่น ที่ปรึกษา ผู้จัดทำ ปีการศึกษา สเปกย่อย เน้นความเร็วสูงสุดและ Fast-Path Bypass",
        top_k=15,
        rerank_top_n=5,
        enable_fast_path=True,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=4,
        max_chunks_per_project=2,
        max_total_projects=3,
        min_score=0.0001,
        temperature=0.0,
        num_predict=512,
        prompt_preset="balanced",
    ),
    "FACTUAL_LOOKUP": IntentConfig(
        intent_name="FACTUAL_LOOKUP",
        label_th="ค้นหาข้อเท็จจริงจำเพาะ (Factoid / Direct Lookup)",
        description_th="สำหรับคำถามสั้นๆ เช่น ที่ปรึกษา ผู้จัดทำ ปีการศึกษา สเปกย่อย เน้นความเร็วสูงสุดและ Fast-Path Bypass",
        top_k=15,
        rerank_top_n=5,
        enable_fast_path=True,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=4,
        max_chunks_per_project=2,
        max_total_projects=3,
        min_score=0.0001,
        temperature=0.0,
        num_predict=512,
        prompt_preset="balanced",
    ),
    "DEEP_DIVE": IntentConfig(
        intent_name="DEEP_DIVE",
        label_th="วิเคราะห์โครงสร้างและขั้นตอนการทำงาน (Deep-Dive / Architecture)",
        description_th="สำหรับคำถามที่ต้องการขั้นตอนการทำงาน สถาปัตยกรรมระบบ การทดลอง และรายละเอียดเชิงลึกของ 1 โครงงาน",
        top_k=20,
        rerank_top_n=7,
        enable_fast_path=False,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=6,
        max_chunks_per_project=6,
        max_total_projects=1,
        min_score=0.0001,
        temperature=0.0,
        num_predict=1024,
        prompt_preset="deep_academic",
    ),
    "EXPLANATION": IntentConfig(
        intent_name="EXPLANATION",
        label_th="อธิบายหลักการและวิธีการ (Explanation / Method)",
        description_th="สำหรับคำถามเชิงอธิบายหลักการและที่มาของโครงงานอย่างเป็นขั้นตอน",
        top_k=18,
        rerank_top_n=6,
        enable_fast_path=False,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=5,
        max_chunks_per_project=5,
        max_total_projects=1,
        min_score=0.0001,
        temperature=0.0,
        num_predict=640,
        prompt_preset="deep_academic",
    ),
    "COMPARISON": IntentConfig(
        intent_name="COMPARISON",
        label_th="เปรียบเทียบข้ามโครงงาน (Multi-Project Comparison)",
        description_th="สำหรับเปรียบเทียบจุดประสงค์ ฮาร์ดแวร์ ซอฟต์แวร์ และความแตกต่าง โดยแบ่งโควต้า Context ให้เท่าเทียมกัน",
        top_k=24,
        rerank_top_n=8,
        enable_fast_path=False,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        max_total_projects=4,
        min_score=0.0001,
        temperature=0.0,
        num_predict=896,
        prompt_preset="comparative_table",
    ),
    "RECOMMENDATION": IntentConfig(
        intent_name="RECOMMENDATION",
        label_th="แนะนำและจัดกลุ่มโครงงานตามโจทย์ (Project Recommendation)",
        description_th="สำหรับแนะนำโครงงานตามหัวข้อที่สนใจ เช่น IoT, การเกษตร พร้อมเสริม Tech Stack Chunks อัตโนมัติ",
        top_k=24,
        rerank_top_n=8,
        enable_fast_path=False,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        max_total_projects=4,
        min_score=0.0001,
        temperature=0.1,
        num_predict=768,
        prompt_preset="balanced",
    ),
    "EXPLORATORY": IntentConfig(
        intent_name="EXPLORATORY",
        label_th="สืบค้นกว้างขวางหลายเล่ม (Broad Exploratory / Keyword Scanning)",
        description_th="สำหรับค้นหารายชื่อโครงงานทั้งหมดที่ใช้โมดูลหรือคำสำคัญเฉพาะ เช่น SX1276, LoRa สแกนโครงงานจำนวนมาก",
        top_k=30,
        rerank_top_n=15,
        enable_fast_path=False,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=12,
        max_chunks_per_project=1,
        max_total_projects=15,
        min_score=-1.0,
        temperature=0.0,
        num_predict=640,
        prompt_preset="concise",
    ),
    "CODE": IntentConfig(
        intent_name="CODE",
        label_th="สกัดโค้ดและคำสั่งทางเทคนิค (Code & Implementation Extraction)",
        description_th="สำหรับค้นหาโค้ดฟังก์ชัน, คำสั่ง SQL, หรือการเชื่อมต่อ API โดยคงรูปแบบการเว้นวรรคและชิ้นส่วนโค้ดดิบ",
        top_k=16,
        rerank_top_n=6,
        enable_fast_path=False,
        enable_hybrid=True,
        enable_boilerplate_filter=True,
        max_context_chunks=5,
        max_chunks_per_project=4,
        max_total_projects=2,
        min_score=0.0001,
        preserve_raw_code=True,
        temperature=0.0,
        num_predict=768,
        prompt_preset="code_focused",
    ),
}

# Runtime active state for intent configurations
_ACTIVE_INTENT_CONFIGS: dict[str, IntentConfig] = {
    k: v.clone() for k, v in DEFAULT_INTENT_REGISTRY.items()
}


def get_intent_config(intent_name: str) -> IntentConfig:
    """Retrieve the fine-grained configuration for a specific intent."""
    normalized = "FACTUAL_LOOKUP" if intent_name in {"FACTOID", "FACTUAL_LOOKUP"} else intent_name
    if normalized in _ACTIVE_INTENT_CONFIGS:
        return _ACTIVE_INTENT_CONFIGS[normalized].clone()
    if intent_name in _ACTIVE_INTENT_CONFIGS:
        return _ACTIVE_INTENT_CONFIGS[intent_name].clone()
    return _ACTIVE_INTENT_CONFIGS["FACTOID"].clone()


def get_all_intent_configs() -> dict[str, dict[str, Any]]:
    """Return all active intent configurations as dictionary."""
    return {k: v.to_dict() for k, v in _ACTIVE_INTENT_CONFIGS.items()}


def update_intent_config(intent_name: str, updates: dict[str, Any]) -> IntentConfig:
    """Update granular hyperparameters for a specific intent."""
    key = "FACTOID" if intent_name in {"FACTOID", "FACTUAL_LOOKUP"} else intent_name
    if key not in _ACTIVE_INTENT_CONFIGS:
        raise KeyError(f"Intent '{intent_name}' is not recognized.")

    cur = _ACTIVE_INTENT_CONFIGS[key].to_dict()
    valid_keys = IntentConfig.__dataclass_fields__.keys()
    for k, v in updates.items():
        if k in valid_keys and k not in {"intent_name", "label_th", "description_th"}:
            cur[k] = v

    updated = IntentConfig.from_dict(cur)
    _ACTIVE_INTENT_CONFIGS[key] = updated
    if key == "FACTOID":
        _ACTIVE_INTENT_CONFIGS["FACTUAL_LOOKUP"] = updated.clone()

    return updated.clone()


def reset_intent_configs() -> dict[str, dict[str, Any]]:
    """Reset all intent configurations back to system defaults."""
    global _ACTIVE_INTENT_CONFIGS
    _ACTIVE_INTENT_CONFIGS = {k: v.clone() for k, v in DEFAULT_INTENT_REGISTRY.items()}
    return get_all_intent_configs()
