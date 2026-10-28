import re

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
    CONFIG_PRESETS,
    get_active_config,
    delete_custom_config,
    get_config_by_name,
    load_custom_configs,
    load_showcase_presets,
    save_custom_config,
    set_active_config,
    RAGConfig,
)
from app.services.ai_config_service import (
    active_preset_name,
    apply_named_preset,
    delete_named_preset,
    load_named_presets,
    remember_active_preset,
    save_intents,
    save_llm,
    save_named_preset,
    save_rag,
)

router = APIRouter(prefix="/config", tags=["AI Configuration"])

# Notes from the handoff sheet. No credentials are stored here.
PROFILE_NOTES = {
    "gemma3:4b": {
        "context_window": "4,096 tokens",
        "latency": "~0.8s - 1.5s",
        "fit": "Small local model. Fast on this machine.",
    },
    "qwen3:4b": {
        "context_window": "4,096 tokens",
        "latency": "~0.9s - 1.6s",
        "fit": "Stronger Thai and project-context answers grounded in the documents.",
    },
    "qwen2.5:7b": {
        "context_window": "8,192 tokens",
        "latency": "~1.5s - 3.0s",
        "fit": "Highest local accuracy for tables and code.",
    },
    "gemini-3.5-flash": {
        "context_window": "1,000,000 tokens",
        "latency": "~0.4s - 0.8s",
        "fit": "Fast cloud model with natural Thai.",
    },
    "gemini-3.5-flash-lite": {
        "context_window": "1,000,000 tokens",
        "latency": "~0.3s - 0.6s",
        "fit": "Short answers and quick filtering.",
    },
    "gpt-4o-mini": {
        "context_window": "128,000 tokens",
        "latency": "~0.5s - 1.0s",
        "fit": "Steady synthesis and document structure.",
    },
    "gpt-4o": {
        "context_window": "128,000 tokens",
        "latency": "~1.0s - 2.0s",
        "fit": "Use when the answer needs detailed analysis.",
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


def _preset_card(config: RAGConfig) -> dict:
    return {
        "profile_name": config.profile_name,
        "description": config.description,
        "top_k": config.top_k,
        "rerank_top_n": config.rerank_top_n,
        "max_context_chunks": config.max_context_chunks,
        "max_chunks_per_project": config.max_chunks_per_project,
        "enable_hybrid": config.enable_hybrid,
        "enable_reranker": config.enable_reranker,
        "enable_boilerplate_filter": config.enable_boilerplate_filter,
        "enable_fast_path": config.enable_fast_path,
        "prompt_preset": config.prompt_preset,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "temperature": config.temperature,
        "min_score": config.min_score,
        "num_predict": config.num_predict,
        "custom": config.profile_name not in CONFIG_PRESETS,
    }


def _bundle_card(bundle: dict) -> dict:
    intents = bundle.get("intents") or {}
    preview_name = bundle.get("preview_intent") or next(iter(intents), "")
    preview = intents.get(preview_name) or {}
    return {
        "profile_name": bundle.get("profile_name"),
        "description": f"Saved intent settings. Preview uses {preview_name or 'the first intent'}.",
        "kind": "intent_bundle",
        "custom": True,
        "preview_intent": preview_name,
        "intents": intents,
        "llm_provider": bundle.get("llm_provider"),
        "llm_model": bundle.get("llm_model"),
        "top_k": preview.get("top_k"),
        "rerank_top_n": preview.get("rerank_top_n"),
        "max_context_chunks": preview.get("max_context_chunks"),
        "max_chunks_per_project": preview.get("max_chunks_per_project"),
        "max_total_projects": preview.get("max_total_projects"),
        "min_score": preview.get("min_score"),
        "temperature": preview.get("temperature"),
        "num_predict": preview.get("num_predict"),
        "prompt_preset": preview.get("prompt_preset"),
        "enable_hybrid": preview.get("enable_hybrid"),
        "enable_boilerplate_filter": preview.get("enable_boilerplate_filter"),
        "enable_fast_path": preview.get("enable_fast_path"),
    }


@router.get("/rag")
def read_rag(db: Session = Depends(_admin)):
    active = get_active_config()
    presets = {name: _preset_card(config) for name, config in CONFIG_PRESETS.items()}
    for name, config in load_custom_configs().items():
        presets[name] = _preset_card(config)
    for name, bundle in load_named_presets(db).items():
        presets[name] = _bundle_card(bundle)
    return {
        "active_config": active.to_dict(),
        "active_preset": active_preset_name(db) or active.profile_name,
        "available_presets": presets,
        "showcase_presets": load_showcase_presets(),
    }


@router.put("/rag")
def write_rag(payload: dict, db: Session = Depends(_admin)):
    merged = {**get_active_config().to_dict(), **payload}
    config = RAGConfig.from_dict(merged)
    set_active_config(config)
    save_rag(db, config)
    return {"status": "success", "message": "Updated RAG config", "config": config.to_dict()}


_PROFILE_NAME = re.compile(r"^[\w][\w \-]{0,79}$")
_PROFILE_FIELDS = {
    "top_k",
    "rerank_top_n",
    "max_context_chunks",
    "max_chunks_per_project",
    "temperature",
    "enable_hybrid",
    "enable_reranker",
    "enable_boilerplate_filter",
    "enable_fast_path",
    "prompt_preset",
    "llm_model",
    "llm_provider",
    "description",
}


@router.post("/rag/profiles")
def create_profile(payload: dict, db: Session = Depends(_admin)):
    """Save a named preset from slider values and use it on the next chat question."""
    name = str(payload.get("profile_name") or "").strip()
    if not _PROFILE_NAME.fullmatch(name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile name must be 1-80 letters, numbers, spaces, underscores, or hyphens.",
        )
    if name in CONFIG_PRESETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That name is a built-in preset. Choose a new name.",
        )
    base_preset = str(payload.get("base_preset") or "winner_rank1_llama3_2_3b")
    overrides = payload.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="overrides must be an object")
    overrides = {key: value for key, value in overrides.items() if key in _PROFILE_FIELDS}
    try:
        for key in ("top_k", "rerank_top_n", "max_context_chunks", "max_chunks_per_project"):
            if key in overrides:
                overrides[key] = int(overrides[key])
        if "temperature" in overrides:
            overrides["temperature"] = float(overrides["temperature"])
        for key in ("enable_hybrid", "enable_reranker", "enable_boilerplate_filter", "enable_fast_path"):
            if key in overrides:
                overrides[key] = bool(overrides[key])
        config = save_custom_config(name, overrides, base_preset=base_preset, set_active=True)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preset values must be numbers or switches.") from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    save_rag(db, config)
    remember_active_preset(db, name)
    return {
        "status": "success",
        "profile_name": name,
        "active_preset": name,
        "active_config": config.to_dict(),
    }


@router.post("/presets")
def create_named_preset(payload: dict, db: Session = Depends(_admin)):
    """Name and store the current intent settings together with the selected model."""
    name = str(payload.get("profile_name") or "").strip()
    if not _PROFILE_NAME.fullmatch(name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile name must be 1-80 letters, numbers, spaces, underscores, or hyphens.",
        )
    if name in CONFIG_PRESETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That name is a built-in preset. Choose a new name.",
        )
    intents = payload.get("intents")
    if not isinstance(intents, dict) or not intents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Intent settings are required.")
    provider = str(payload.get("llm_provider") or "ollama").strip()
    model = str(payload.get("llm_model") or "").strip()
    known = {(item["provider"], item["model"]) for item in AVAILABLE_LLM_PROFILES}
    if (provider, model) not in known:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a model from the list.")
    preview_intent = str(payload.get("preview_intent") or "FACTOID")
    try:
        bundle = save_named_preset(db, name, intents, provider, model, preview_intent)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "success", "active_preset": name, "preset": _bundle_card(bundle)}


@router.delete("/presets/{preset_name}")
def remove_named_preset(preset_name: str, db: Session = Depends(_admin)):
    """Delete a custom preset. Recommended presets from the handoff file stay."""
    if preset_name in CONFIG_PRESETS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Built-in presets cannot be deleted.")
    if preset_name in load_named_presets(db):
        delete_named_preset(db, preset_name)
        return {"status": "success", "profile_name": preset_name}
    if delete_custom_config(preset_name):
        return {"status": "success", "profile_name": preset_name}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found.")


@router.post("/rag/preset/{preset_name}")
def apply_preset(preset_name: str, db: Session = Depends(_admin)):
    if preset_name in load_named_presets(db):
        try:
            apply_named_preset(db, preset_name)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return {"status": "success", "active_preset": preset_name, "kind": "intent_bundle"}
    try:
        config = get_config_by_name(preset_name)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    set_active_config(config)
    save_rag(db, config)
    remember_active_preset(db, preset_name)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider is required")
    set_active_llm(provider, model)
    active_provider, active_model = get_active_llm()
    save_llm(db, active_provider, active_model)
    return {"status": "success", "active": {"provider": active_provider, "model": active_model}}


@router.post("/benchmark/run")
def run_benchmark(payload: dict, _db: Session = Depends(_admin)):
    from app.rag.evaluation.benchmark_run import run_preset_benchmark

    baseline = str(payload.get("baseline") or "winner_rank1_llama3_2_3b")
    candidate = str(payload.get("candidate") or "winner_rank2_qwen2_5_3b")
    if baseline == candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Baseline and candidate must be different presets")
    try:
        limit = int(payload.get("limit") or 2)
    except (TypeError, ValueError):
        limit = 2
    try:
        repeats = int(payload.get("repeats") or 5)
    except (TypeError, ValueError):
        repeats = 5
    try:
        return run_preset_benchmark(baseline, candidate, min(max(limit, 1), 6), repeats)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/benchmark/quality")
def rank_quality(payload: dict, _db: Session = Depends(_admin)):
    """Rank the presets named by the caller. Defaults to the three Presets-page recommendations."""
    from app.rag.evaluation.benchmark_run import rank_answer_quality

    try:
        limit = int(payload.get("limit") or 2)
        repeats = int(payload.get("repeats") or 5)
    except (TypeError, ValueError):
        limit, repeats = 2, 5
    raw_names = payload.get("preset_names")
    names = [str(name) for name in raw_names if str(name).strip()] if isinstance(raw_names, list) else None
    try:
        return rank_answer_quality(preset_names=names or None, limit=min(max(limit, 1), 6), repeats=repeats)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/llms/test-connectivity")
def ping_llm(payload: dict, _db: Session = Depends(_admin)):
    provider = str(payload.get("provider") or "").strip()
    model = payload.get("model")
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider is required")
    result = test_provider_connectivity(provider, model)
    online = bool(result.get("success"))
    return {
        "status": "online" if online else "offline",
        "latency_ms": round(float(result.get("latency_sec") or 0) * 1000, 1),
        "message": "Connection healthy" if online else str(result.get("response_sample") or "Connection failed"),
    }
