from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_administrator
from app.core.database import get_db
from app.models.user import User
from app.rag.retrieval.intent_config import (
    get_all_intent_configs,
    reset_intent_configs,
    update_intent_config,
)
from app.rag.retrieval.llm_provider import (
    AVAILABLE_LLM_PROFILES,
    get_active_llm,
    set_active_llm,
    test_provider_connectivity,
)
from app.rag.retrieval.rag_config import (
    get_active_config,
    get_config_preset,
    list_available_presets,
    set_active_config,
    RAGConfig,
)
from app.services.ai_config_service import save_intents, save_llm, save_rag

router = APIRouter(prefix="/config", tags=["AI Configuration"])

# Notes from the handoff sheet. No credentials are stored here.
PROFILE_NOTES = {
    "gemma3:4b": {
        "context_window": "4,096 tokens",
        "latency": "~0.8s - 1.5s",
        "fit": "โมเดลขนาดเล็ก ทำงานในเครื่องได้รวดเร็ว",
    },
    "qwen3:4b": {
        "context_window": "4,096 tokens",
        "latency": "~0.9s - 1.6s",
        "fit": "ภาษาไทยและบริบทโครงงานวิจัยตอบตรงตามเอกสาร",
    },
    "qwen2.5:7b": {
        "context_window": "8,192 tokens",
        "latency": "~1.5s - 3.0s",
        "fit": "ความแม่นยำสูงสุดในโหมด local สำหรับตารางและโค้ด",
    },
    "gemini-3.5-flash": {
        "context_window": "1,000,000 tokens",
        "latency": "~0.4s - 0.8s",
        "fit": "เร็วและรองรับภาษาไทยเป็นธรรมชาติ",
    },
    "gemini-3.5-flash-lite": {
        "context_window": "1,000,000 tokens",
        "latency": "~0.3s - 0.6s",
        "fit": "ตอบสั้นและคัดกรองข้อมูลได้เร็ว",
    },
    "gpt-4o-mini": {
        "context_window": "128,000 tokens",
        "latency": "~0.5s - 1.0s",
        "fit": "สังเคราะห์คำตอบและจัดโครงสร้างได้คงที่",
    },
    "gpt-4o": {
        "context_window": "128,000 tokens",
        "latency": "~1.0s - 2.0s",
        "fit": "ใช้เมื่อต้องการคำตอบเชิงวิเคราะห์ที่ละเอียด",
    },
}


def _admin(db: Session = Depends(get_db), _user: User = Depends(get_current_administrator)):
    return db


@router.get("/intents")
def read_intents(db: Session = Depends(_admin)):
    return {"status": "success", "intents": get_all_intent_configs()}


@router.put("/intents/{intent_name}")
def write_intent(intent_name: str, payload: dict, db: Session = Depends(_admin)):
    try:
        updated = update_intent_config(intent_name, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    save_intents(db)
    return {"status": "success", "message": "Updated", "config": updated.to_dict()}


@router.post("/intents/reset")
def reset_intents(db: Session = Depends(_admin)):
    intents = reset_intent_configs()
    save_intents(db)
    return {"status": "success", "message": "Reset all intents", "intents": intents}


@router.get("/rag")
def read_rag(_db: Session = Depends(_admin)):
    active = get_active_config()
    return {
        "active_config": active.to_dict(),
        "available_presets": {item["profile_name"]: item for item in list_available_presets()},
    }


@router.put("/rag")
def write_rag(payload: dict, db: Session = Depends(_admin)):
    merged = {**get_active_config().to_dict(), **payload}
    config = RAGConfig.from_dict(merged)
    set_active_config(config)
    save_rag(db, config)
    return {"status": "success", "message": "Updated RAG config", "config": config.to_dict()}


@router.post("/rag/preset/{preset_name}")
def apply_preset(preset_name: str, db: Session = Depends(_admin)):
    try:
        config = get_config_preset(preset_name)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    set_active_config(config)
    save_rag(db, config)
    return {
        "status": "success",
        "active_preset": preset_name,
        "active_config": config.to_dict(),
    }


@router.get("/llms")
def read_llms(_db: Session = Depends(_admin)):
    provider, model = get_active_llm()
    profiles = []
    for profile in AVAILABLE_LLM_PROFILES:
        notes = PROFILE_NOTES.get(profile["model"], {})
        profiles.append({**profile, **notes})
    return {"active": {"provider": provider, "model": model}, "profiles": profiles}


@router.post("/llms/set-active")
def activate_llm(payload: dict, db: Session = Depends(_admin)):
    provider = str(payload.get("provider") or "").strip()
    model = payload.get("model")
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ต้องระบุ provider")
    set_active_llm(provider, model)
    active_provider, active_model = get_active_llm()
    save_llm(db, active_provider, active_model)
    return {"status": "success", "active": {"provider": active_provider, "model": active_model}}


@router.post("/benchmark/run")
def run_benchmark(payload: dict, _db: Session = Depends(_admin)):
    from app.rag.evaluation.benchmark_run import run_preset_benchmark

    baseline = str(payload.get("baseline") or "precision_hybrid")
    candidate = str(payload.get("candidate") or "fast_mode")
    if baseline == candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="baseline กับ candidate ต้องคนละโหมด")
    try:
        limit = int(payload.get("limit") or 2)
    except (TypeError, ValueError):
        limit = 2
    try:
        return run_preset_benchmark(baseline, candidate, min(max(limit, 1), 6))
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/llms/test-connectivity")
def ping_llm(payload: dict, _db: Session = Depends(_admin)):
    provider = str(payload.get("provider") or "").strip()
    model = payload.get("model")
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ต้องระบุ provider")
    result = test_provider_connectivity(provider, model)
    online = bool(result.get("success"))
    return {
        "status": "online" if online else "offline",
        "latency_ms": round(float(result.get("latency_sec") or 0) * 1000, 1),
        "message": "Connection healthy" if online else str(result.get("response_sample") or "Connection failed"),
    }
