"""
Module: llm_provider.py
Description:
    Unified Multi-Provider LLM Abstraction Layer for RAGcoon.
    Allows dynamic model selection and benchmark comparison across:
      1. Ollama (Local): gemma3:4b, qwen3:4b, qwen2.5:7b, llama3.1:8b, etc.
      2. Google Gemini (Cloud API): gemini-3.5-flash, gemini-3.5-flash-lite, etc.
      3. OpenAI ChatGPT (Cloud API): gpt-4o-mini, gpt-4o, etc.
"""

import os
import re
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any, Optional
import requests
from dotenv import load_dotenv

# Ensure .env is loaded from both working directory and backend directory
load_dotenv()
_backend_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".env")
if os.path.exists(_backend_env):
    load_dotenv(_backend_env)

# Global active LLM selection for runtime switching across the pipeline
_ACTIVE_PROVIDER: Optional[str] = None
_ACTIVE_MODEL: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        Synchronous completion generation.
        Returns (generated_text, stats_dict).
        """
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> Generator[str, None, None]:
        """
        Streaming token generator.
        Yields individual token strings in real-time.
        """
        pass


class OllamaProvider(BaseLLMProvider):
    """Local Ollama Provider (gemma3:4b, qwen3:4b, llama3.1:8b, etc.)."""

    def __init__(self, model_name: Optional[str] = None):
        model = model_name or os.getenv("OLLAMA_MODEL", "gemma3:4b")
        super().__init__(model)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.session = requests.Session()

    def _format_prompt(
        self,
        prompt: str,
        system_prompt: str = "",
        thinking: bool = False,
    ) -> tuple[str, list[str]]:
        """Format prompt according to model architecture if not already formatted."""
        m_lower = self.model_name.lower()
        extra_stops = ["\n## Sources", "\n## Source", "\n## แหล่งที่มา", "\n### ⚠️", "\n### 🔔"]

        # Check if already templated
        if "<start_of_turn>" in prompt or "<|im_start|>" in prompt or "<|begin_of_text|>" in prompt:
            stops = ["<|im_end|>", "<|im_start|>", "<|endoftext|>", "<end_of_turn>", "<|eot_id|>", "<|end_of_text|>"] + extra_stops
            return prompt, stops

        if "gemma" in m_lower:
            full_user = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            formatted = f"<start_of_turn>user\n{full_user}<end_of_turn>\n<start_of_turn>model\n"
            stops = ["<end_of_turn>", "<start_of_turn>", "<eos>", "<|im_end|>"] + extra_stops
        elif any(k in m_lower for k in ["qwen", "llama", "deepseek", "mistral"]):
            think_tag = "" if thinking else "<think>\n</think>\n"
            sys_block = f"<|im_start|>system\n{system_prompt}<|im_end|>\n" if system_prompt else ""
            formatted = f"{sys_block}<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n{think_tag}"
            stops = ["<|im_end|>", "<|im_start|>", "<|endoftext|>", "</think>"] + extra_stops
        else:
            formatted = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            stops = ["<|im_end|>", "<|endoftext|>"] + extra_stops

        return formatted, stops

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        t0 = time.perf_counter()
        full_prompt, default_stops = self._format_prompt(prompt, system_prompt, thinking=thinking)
        stops = stop_tokens or default_stops
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))

        body = {
            "model": self.model_name,
            "prompt": full_prompt,
            "raw": True,
            "stream": False,
            "think": thinking,
            "keep_alive": "30m",
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "4096")),
                "stop": stops,
            },
        }

        try:
            resp = self.session.post(f"{self.base_url}/api/generate", json=body, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("response", "")
            duration = time.perf_counter() - t0

            p_eval = data.get("prompt_eval_count", 0)
            e_count = data.get("eval_count", 0)
            e_dur_ns = data.get("eval_duration", 0)
            gen_speed = (e_count / (e_dur_ns / 1e9)) if e_dur_ns > 0 else 0.0

            stats = {
                "provider": "ollama",
                "model": self.model_name,
                "prompt_eval_count": p_eval,
                "eval_count": e_count,
                "eval_duration_ns": e_dur_ns,
                "gen_speed_tps": round(gen_speed, 1),
                "ttft_seconds": round(duration, 3),
                "total_seconds": round(duration, 3),
            }
            return answer, stats
        except Exception as e:
            return f"⚠️ Ollama error: {e}", {"provider": "ollama", "model": self.model_name, "error": str(e)}

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> Generator[str, None, None]:
        full_prompt, default_stops = self._format_prompt(prompt, system_prompt, thinking=thinking)
        stops = stop_tokens or default_stops
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))

        body = {
            "model": self.model_name,
            "prompt": full_prompt,
            "raw": True,
            "stream": True,
            "think": thinking,
            "keep_alive": "30m",
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "4096")),
                "stop": stops,
            },
        }

        try:
            resp = self.session.post(f"{self.base_url}/api/generate", json=body, stream=True, timeout=timeout)
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        break
        except Exception as e:
            yield f"⚠️ Ollama stream error: {e}"


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Cloud API Provider (gemini-3.5-flash, gemini-3.5-flash-lite, etc.)."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        super().__init__(model)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.session = requests.Session()

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        t0 = time.perf_counter()
        if not self.api_key:
            return "⚠️ Gemini API key not found. Please set GEMINI_API_KEY in .env", {"error": "Missing API Key"}

        candidate_models = [self.model_name]
        for fallback in ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = ""
        for model_to_try in candidate_models:
            url = f"{self.base_url}/{model_to_try}:generateContent?key={self.api_key}"
            payload: dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": num_predict,
                },
            }
            if system_prompt:
                payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
            if stop_tokens:
                payload["generationConfig"]["stopSequences"] = stop_tokens[:5]

            try:
                resp = self.session.post(url, json=payload, timeout=45)
                duration = time.perf_counter() - t0
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    answer = ""
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        answer = "".join(p.get("text", "") for p in parts if not p.get("thought", False))
                        if not answer:
                            answer = "".join(p.get("text", "") for p in parts)

                    usage = data.get("usageMetadata", {})
                    prompt_tokens = usage.get("promptTokenCount", 0)
                    cand_tokens = usage.get("candidatesTokenCount", 0)
                    gen_speed = (cand_tokens / duration) if duration > 0 else 0.0

                    stats = {
                        "provider": "gemini",
                        "model": model_to_try,
                        "prompt_eval_count": prompt_tokens,
                        "eval_count": cand_tokens,
                        "gen_speed_tps": round(gen_speed, 1),
                        "ttft_seconds": round(duration, 3),
                        "total_seconds": round(duration, 3),
                    }
                    return answer, stats

                # If 503 (demand spike) or 404 (model deprecated), try next fallback
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                last_error = f"Gemini API Error ({resp.status_code}) on {model_to_try}: {err_msg}"
                if resp.status_code in {503, 404}:
                    time.sleep(0.5)
                    continue
                return f"⚠️ {last_error}", {"error": last_error, "model": model_to_try}
            except Exception as e:
                last_error = f"Gemini request failed on {model_to_try}: {e}"
                continue

        return f"⚠️ Gemini Error: {last_error}", {"provider": "gemini", "model": self.model_name, "error": last_error}

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> Generator[str, None, None]:
        if not self.api_key:
            yield "⚠️ Gemini API key not found. Please set GEMINI_API_KEY in .env"
            return

        candidate_models = [self.model_name]
        for fallback in ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        stream_succeeded = False
        last_err = ""
        for model_to_try in candidate_models:
            url = f"{self.base_url}/{model_to_try}:streamGenerateContent?key={self.api_key}&alt=sse"
            payload: dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": num_predict,
                },
            }
            if system_prompt:
                payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
            if stop_tokens:
                payload["generationConfig"]["stopSequences"] = stop_tokens[:5]

            try:
                resp = self.session.post(url, json=payload, stream=True, timeout=45)
                if resp.status_code != 200:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                    last_err = err_msg
                    if resp.status_code in {503, 404}:
                        time.sleep(0.5)
                        continue
                    yield f"⚠️ Gemini API Error ({resp.status_code}): {err_msg}"
                    return

                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data:"):
                            chunk_json = line_str[5:].strip()
                            if chunk_json:
                                data = json.loads(chunk_json)
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        if not p.get("thought", False):
                                            t = p.get("text", "")
                                            if t:
                                                stream_succeeded = True
                                                yield t
                if stream_succeeded:
                    return
            except Exception as e:
                last_err = str(e)
                continue

        if not stream_succeeded:
            yield f"⚠️ Gemini stream failed: {last_err}"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI ChatGPT Cloud API Provider (gpt-4o-mini, gpt-4o, etc.)."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        super().__init__(model)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        self.session = requests.Session()

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        t0 = time.perf_counter()
        if not self.api_key:
            return "⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in .env", {"error": "Missing API Key"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": num_predict,
        }
        if stop_tokens:
            payload["stop"] = stop_tokens[:4]

        try:
            resp = self.session.post(self.endpoint, headers=headers, json=payload, timeout=45)
            duration = time.perf_counter() - t0
            if resp.status_code != 200:
                err_data = resp.json().get("error", {})
                err_msg = err_data.get("message", resp.text)
                if resp.status_code == 429:
                    err_msg = "OpenAI Quota Exceeded (429): บัญชี OpenAI หมดเครดิต (No credits remaining) กรุณาเติมเงินที่ platform.openai.com/billing หรือสลับไปใช้ Ollama (Local) / Gemini"
                return f"⚠️ OpenAI Error: {err_msg}", {"error": err_msg, "status_code": resp.status_code}

            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            gen_speed = (completion_tokens / duration) if duration > 0 else 0.0

            stats = {
                "provider": "openai",
                "model": self.model_name,
                "prompt_eval_count": prompt_tokens,
                "eval_count": completion_tokens,
                "gen_speed_tps": round(gen_speed, 1),
                "ttft_seconds": round(duration, 3),
                "total_seconds": round(duration, 3),
            }
            return answer, stats
        except Exception as e:
            return f"⚠️ OpenAI request failed: {e}", {"provider": "openai", "model": self.model_name, "error": str(e)}

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        num_predict: int = 512,
        stop_tokens: Optional[list[str]] = None,
        thinking: bool = False,
    ) -> Generator[str, None, None]:
        if not self.api_key:
            yield "⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in .env"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": num_predict,
            "stream": True,
        }
        if stop_tokens:
            payload["stop"] = stop_tokens[:4]

        try:
            resp = self.session.post(self.endpoint, headers=headers, json=payload, stream=True, timeout=45)
            if resp.status_code != 200:
                err_data = resp.json().get("error", {})
                err_msg = err_data.get("message", resp.text)
                if resp.status_code == 429:
                    err_msg = "OpenAI Quota Exceeded (429): You have no credits remaining. (กรุณาเติมเงินที่ platform.openai.com/billing)"
                yield f"⚠️ OpenAI Error: {err_msg}"
                return

            for line in resp.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data:"):
                        chunk_str = line_str[5:].strip()
                        if chunk_str == "[DONE]":
                            break
                        if chunk_str:
                            data = json.loads(chunk_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
        except Exception as e:
            yield f"⚠️ OpenAI stream error: {e}"


# =========================================================================
# Provider Factory & Dynamic Router
# =========================================================================

def set_active_llm(provider: str, model: Optional[str] = None) -> None:
    """Set the globally active LLM provider and model for this runtime session."""
    global _ACTIVE_PROVIDER, _ACTIVE_MODEL
    _ACTIVE_PROVIDER = provider.strip().lower()
    _ACTIVE_MODEL = model.strip() if model else None


def get_active_llm() -> tuple[str, str]:
    """Return currently active (provider, model)."""
    prov = _ACTIVE_PROVIDER or os.getenv("LLM_PROVIDER", "ollama")
    prov = prov.strip().lower()
    if _ACTIVE_MODEL:
        mod = _ACTIVE_MODEL
    elif prov == "gemini":
        mod = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    elif prov in {"openai", "chatgpt"}:
        mod = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    else:
        mod = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    return prov, mod


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM Provider instance.
    Checks explicit parameter -> global active selection -> environment variables -> fallback.
    """
    active_prov, active_mod = get_active_llm()
    prov = (provider_name or active_prov).strip().lower()
    mod = model_name or (active_mod if provider_name is None or provider_name.lower() == active_prov else None)

    if prov == "gemini":
        return GeminiProvider(model_name=mod)
    elif prov in {"openai", "chatgpt"}:
        return OpenAIProvider(model_name=mod)
    else:
        # Default: Ollama
        return OllamaProvider(model_name=mod)


AVAILABLE_LLM_PROFILES = [
    {
        "id": "ollama_gemma3",
        "provider": "ollama",
        "model": "gemma3:4b",
        "label": "Ollama Gemma 3 (4B) [Local Default]",
        "description": "โมเดลท้องถิ่นขนาด 4B ทำงานแบบ Offline บนเครื่อง ประหยัดทรัพยากร",
        "is_cloud": False,
    },
    {
        "id": "ollama_qwen3",
        "provider": "ollama",
        "model": "qwen3:4b",
        "label": "Ollama Qwen 3 (4B) [Local Reasoning - 2.5GB]",
        "description": "โมเดล Qwen 3 ขนาด 4B สำหรับงานวิเคราะห์และการตอบเชิงเหตุผล",
        "is_cloud": False,
    },
    {
        "id": "ollama_qwen25_3b",
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "label": "Ollama Qwen 2.5 (3B) [Local Ultra-Fast - 1.9GB]",
        "description": "โมเดลขนาดกะทัดรัด 3B เร็วสูง ประหยัด VRAM 4GB ตอบภาษาไทยแม่นยำ",
        "is_cloud": False,
    },
    {
        "id": "ollama_llama32_3b",
        "provider": "ollama",
        "model": "llama3.2:3b",
        "label": "Ollama Llama 3.2 (3B) [Meta Compact - 2.0GB]",
        "description": "โมเดลขนาด 3B จาก Meta ออกแบบสำหรับ Laptop GPU 4GB โดยเฉพาะ",
        "is_cloud": False,
    },
    {
        "id": "ollama_gemma3_1b",
        "provider": "ollama",
        "model": "gemma3:1b",
        "label": "Ollama Gemma 3 (1B) [Ultra-Lightweight - 815MB]",
        "description": "โมเดลจิ๋วขนาด 1B กินแรมไม่ถึง 1GB เน้นความเร็วสูงสุด",
        "is_cloud": False,
    },
    {
        "id": "ollama_qwen25_7b",
        "provider": "ollama",
        "model": "qwen2.5:7b",
        "label": "Ollama Qwen 2.5 (7B) [Local High-Capacity - 4.7GB]",
        "description": "โมเดลขนาดกลาง 7B ความละเอียดสูง (Hybrid GPU+CPU Offload)",
        "is_cloud": False,
    },
    {
        "id": "ollama_llama31_8b",
        "provider": "ollama",
        "model": "llama3.1:8b",
        "label": "Ollama Llama 3.1 (8B) [Meta Standard - 4.9GB]",
        "description": "โมเดลมาตรฐาน 8B จาก Meta",
        "is_cloud": False,
    },
    {
        "id": "gemini_flash",
        "provider": "gemini",
        "model": "gemini-3.5-flash",
        "label": "Google Gemini 3.5 Flash [Cloud Ultra-Fast]",
        "description": "โมเดลบนคลาวด์ของ Google ความเร็วสูงมากและแม่นยำสูง รองรับบริบทใหญ่",
        "is_cloud": True,
    },
    {
        "id": "gemini_flash_lite",
        "provider": "gemini",
        "model": "gemini-3.5-flash-lite",
        "label": "Google Gemini 3.5 Flash-Lite [Cloud Cost-Effective]",
        "description": "โมเดลตัวเบาของ Gemini เน้นความเร็วในการสร้างคำตอบและประหยัด Token",
        "is_cloud": True,
    },
    {
        "id": "openai_gpt4o_mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "label": "OpenAI ChatGPT (GPT-4o Mini) [Cloud SOTA]",
        "description": "โมเดลเรือธงขนาดกะทัดรัดของ OpenAI สังเคราะห์ภาษาได้สละสลวย",
        "is_cloud": True,
    },
]


def test_provider_connectivity(
    provider_name: str, model_name: Optional[str] = None
) -> dict[str, Any]:
    """Test connectivity and measure basic response latency for an LLM provider."""
    provider = get_llm_provider(provider_name=provider_name, model_name=model_name)
    test_prompt = "Say 'OK' in one word."
    t0 = time.perf_counter()
    ans, stats = provider.generate(test_prompt, num_predict=10)
    latency = time.perf_counter() - t0

    is_error = "⚠️" in ans or "error" in stats
    return {
        "provider": provider_name,
        "model": provider.model_name,
        "success": not is_error,
        "latency_sec": round(latency, 3),
        "response_sample": ans.strip()[:100],
        "stats": stats,
    }
