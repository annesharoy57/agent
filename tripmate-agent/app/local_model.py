"""CPU-local Qwen inference through llama.cpp; no remote model APIs are used."""

import importlib.util
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "Qwen3-1.7B-Q8_0.gguf"
MIN_MODEL_BYTES = 1_000_000_000


class LocalModelUnavailable(RuntimeError):
    """Raised when the configured local model cannot be used."""


def configured_model_path() -> Path:
    value = os.getenv("TRIPMATE_MODEL_PATH", "").strip()
    path = Path(value) if value else Path("models") / DEFAULT_MODEL
    return path if path.is_absolute() else _ROOT / path


def model_status() -> dict[str, Any]:
    path = configured_model_path()
    has_runtime = importlib.util.find_spec("llama_cpp") is not None
    if not has_runtime:
        state = "runtime_missing"
        detail = "Install llama-cpp-python from the local setup instructions."
    elif not path.is_file():
        state = "model_missing"
        detail = f"Download the configured GGUF model to {path}."
    elif path.stat().st_size < MIN_MODEL_BYTES:
        state = "model_incomplete"
        detail = f"The configured model file is incomplete. Download the full GGUF model to {path}."
    else:
        state = "ready"
        detail = "Local CPU model is configured."
    return {
        "state": state,
        "runtime": "llama.cpp",
        "model": "Qwen3-1.7B-Q8_0",
        "model_path": str(path),
        "remote_inference": False,
        "detail": detail,
    }


@lru_cache(maxsize=1)
def _load_model(path_value: str, context_size: int, threads: int) -> Any:
    path = Path(path_value)
    if not path.is_file():
        raise LocalModelUnavailable(f"Local model file is missing: {path}")
    try:
        from llama_cpp import Llama
    except ImportError as error:
        raise LocalModelUnavailable(
            "llama-cpp-python is not installed. Follow the local setup instructions."
        ) from error
    return Llama(
        model_path=str(path),
        n_ctx=context_size,
        n_threads=threads,
        n_gpu_layers=0,
        verbose=False,
    )


def generate_local_reply(
    system_prompt: str, user_prompt: str, *, max_tokens: int = 500,
) -> str:
    status = model_status()
    if status["state"] != "ready":
        raise LocalModelUnavailable(status["detail"])
    context_size = max(2048, min(4096, int(os.getenv("TRIPMATE_CONTEXT_TOKENS", "3072"))))
    default_threads = min(4, os.cpu_count() or 1)
    threads = max(1, min(8, int(os.getenv("TRIPMATE_MODEL_THREADS", str(default_threads)))))
    model = _load_model(str(configured_model_path()), context_size, threads)
    response = model.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        min_p=0.0,
        presence_penalty=1.5,
        repeat_penalty=1.1,
        max_tokens=max(1, min(max_tokens, 1000)),
    )
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise LocalModelUnavailable("The local model returned an invalid response.") from error
    if not isinstance(content, str) or not content.strip():
        raise LocalModelUnavailable("The local model returned an empty response.")
    return content.strip()
