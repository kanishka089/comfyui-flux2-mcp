"""Environment-driven configuration for the comfyui-flux2-mcp server."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_HERE = Path(__file__).parent.resolve()       # src/
_ROOT = _HERE.parent                           # repo root
load_dotenv(_ROOT / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required env var {name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def _path(name: str, required: bool = True) -> Path:
    raw = os.environ.get(name, "").strip()
    if not raw:
        if required:
            raise RuntimeError(
                f"Required env var {name} is not set. Copy .env.example to .env and fill it in."
            )
        return Path()
    return Path(raw).expanduser().resolve()


COMFYUI_URL: str = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_INPUT_DIR: Path = _path("COMFYUI_INPUT_DIR")
COMFYUI_OUTPUT_DIR: Path = _path("COMFYUI_OUTPUT_DIR")
COMFYUI_TIMEOUT: int = int(os.environ.get("COMFYUI_TIMEOUT", "300"))

FLUX2_MODEL_FILE: str = os.environ.get("FLUX2_MODEL_FILE", "flux-2-klein-9b-Q4_K_S.gguf")
FLUX2_CLIP_FILE: str = os.environ.get("FLUX2_CLIP_FILE", "qwen_3_8b_fp8mixed.safetensors")
FLUX2_VAE_FILE: str = os.environ.get("FLUX2_VAE_FILE", "flux2-vae.safetensors")
FLUX2_STEPS: int = int(os.environ.get("FLUX2_STEPS", "4"))

TEMPLATES_DIR: Path = _HERE / "templates"
