"""MCP server: exposes generate_image + edit_image tools backed by local ComfyUI + FLUX.2 Klein."""
from __future__ import annotations

import copy
import json
import random
import shutil
import sys
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import config
import comfy_client
from comfy_client import ComfyUIError


mcp = FastMCP("comfyui-flux2")


def _load_template(name: str) -> dict:
    path = config.TEMPLATES_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)["prompt"]


def _random_seed() -> int:
    return random.randint(0, 2**32 - 1)


def _apply_model_filenames(workflow: dict) -> None:
    """Override the model/CLIP/VAE filenames in the template using env vars."""
    for node in workflow.values():
        ct = node.get("class_type")
        if ct == "UnetLoaderGGUF":
            node["inputs"]["unet_name"] = config.FLUX2_MODEL_FILE
        elif ct == "CLIPLoader":
            node["inputs"]["clip_name"] = config.FLUX2_CLIP_FILE
        elif ct == "VAELoader":
            node["inputs"]["vae_name"] = config.FLUX2_VAE_FILE
        elif ct == "Flux2Scheduler":
            node["inputs"]["steps"] = config.FLUX2_STEPS


@mcp.tool()
def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: int = -1,
) -> str:
    """Generate an image from a text prompt using FLUX.2 Klein 9B.

    Args:
        prompt: What to draw. Be specific; the Qwen3 text encoder follows long, detailed prompts well.
        width: Image width in pixels (default 1024). Must be a multiple of 16.
        height: Image height in pixels (default 1024). Must be a multiple of 16.
        seed: Random seed. Use -1 to randomize per call (default).

    Returns:
        Absolute filesystem path to the saved PNG.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt cannot be empty")
    if width % 16 or height % 16:
        raise ValueError("width and height must be multiples of 16")

    workflow = copy.deepcopy(_load_template("t2i.json"))
    _apply_model_filenames(workflow)

    # Patch the per-call parameters
    workflow["4"]["inputs"]["text"] = prompt
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    workflow["6"]["inputs"]["width"] = width
    workflow["6"]["inputs"]["height"] = height
    workflow["9"]["inputs"]["noise_seed"] = _random_seed() if seed < 0 else seed
    workflow["12"]["inputs"]["filename_prefix"] = "mcp/Flux2-Klein"

    prompt_id = comfy_client.submit_prompt(workflow)
    saved = comfy_client.wait_for_result(prompt_id, save_node_id="12")
    return str(saved)


@mcp.tool()
def edit_image(
    source_path: str,
    prompt: str,
    seed: int = -1,
) -> str:
    """Edit an existing image with an instruction prompt (Kontext-style).

    The source image becomes a reference; the prompt acts as the edit instruction
    (e.g. "make it nighttime", "add snow", "change the cat to a dog").

    Args:
        source_path: Absolute path to an existing PNG/JPG on disk.
        prompt: What to change.
        seed: Random seed. Use -1 to randomize per call (default).

    Returns:
        Absolute filesystem path to the saved edited PNG.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt cannot be empty")
    src = Path(source_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source image not found: {src}")

    # Copy the source into ComfyUI's input/ folder under a unique name
    config.COMFYUI_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    staged_name = f"mcp_source_{uuid.uuid4().hex[:12]}{src.suffix.lower()}"
    staged = config.COMFYUI_INPUT_DIR / staged_name
    shutil.copyfile(src, staged)

    workflow = copy.deepcopy(_load_template("edit.json"))
    _apply_model_filenames(workflow)

    workflow["4"]["inputs"]["image"] = staged_name
    workflow["8"]["inputs"]["text"] = prompt
    workflow["15"]["inputs"]["noise_seed"] = _random_seed() if seed < 0 else seed
    workflow["18"]["inputs"]["filename_prefix"] = "mcp/Flux2-Klein-edit"

    try:
        prompt_id = comfy_client.submit_prompt(workflow)
        saved = comfy_client.wait_for_result(prompt_id, save_node_id="18")
    finally:
        # Don't leave the staged copy lying around forever
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            pass

    return str(saved)


def main() -> None:
    # Validate config eagerly so we fail loudly on bad setup
    if not config.COMFYUI_INPUT_DIR.exists():
        print(
            f"WARNING: COMFYUI_INPUT_DIR does not exist: {config.COMFYUI_INPUT_DIR}",
            file=sys.stderr,
        )
    if not config.COMFYUI_OUTPUT_DIR.exists():
        print(
            f"WARNING: COMFYUI_OUTPUT_DIR does not exist: {config.COMFYUI_OUTPUT_DIR}",
            file=sys.stderr,
        )
    mcp.run()


if __name__ == "__main__":
    main()
