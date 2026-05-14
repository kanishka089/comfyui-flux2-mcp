"""Thin wrapper around ComfyUI's HTTP API."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

import config


class ComfyUIError(Exception):
    """Raised for any user-actionable failure talking to ComfyUI."""


def _connection_error(exc: Exception) -> ComfyUIError:
    return ComfyUIError(
        f"ComfyUI not reachable at {config.COMFYUI_URL}. "
        f"Is ComfyUI running? ({type(exc).__name__}: {exc})"
    )


def is_alive() -> bool:
    try:
        r = requests.get(f"{config.COMFYUI_URL}/system_stats", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def submit_prompt(prompt: dict[str, Any]) -> str:
    """Submit an API-format workflow. Returns the prompt_id."""
    try:
        r = requests.post(
            f"{config.COMFYUI_URL}/prompt",
            json={"prompt": prompt},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise _connection_error(exc) from exc

    if r.status_code != 200:
        raise ComfyUIError(
            f"ComfyUI rejected the workflow ({r.status_code}): {r.text[:500]}"
        )

    body = r.json()
    node_errors = body.get("node_errors") or {}
    if node_errors:
        raise ComfyUIError(
            "Workflow validation failed. Check that model filenames in your "
            f".env match files in ComfyUI/models/. Details: {node_errors}"
        )

    prompt_id = body.get("prompt_id")
    if not prompt_id:
        raise ComfyUIError(f"ComfyUI returned no prompt_id: {body}")
    return prompt_id


def wait_for_result(prompt_id: str, save_node_id: str) -> Path:
    """Poll /history until the prompt completes; return the saved PNG path."""
    deadline = time.monotonic() + config.COMFYUI_TIMEOUT
    poll_url = f"{config.COMFYUI_URL}/history/{prompt_id}"

    while time.monotonic() < deadline:
        try:
            r = requests.get(poll_url, timeout=10)
        except requests.RequestException as exc:
            raise _connection_error(exc) from exc

        if r.status_code != 200:
            time.sleep(3)
            continue

        history = r.json()
        record = history.get(prompt_id)
        if not record:
            time.sleep(3)
            continue

        status = (record.get("status") or {}).get("status_str")
        if status == "success":
            return _extract_output_path(record, save_node_id)
        if status == "error":
            messages = (record.get("status") or {}).get("messages", [])
            raise ComfyUIError(f"ComfyUI execution failed: {messages[-3:]}")

        # still running
        time.sleep(3)

    raise ComfyUIError(
        f"Generation timed out after {config.COMFYUI_TIMEOUT}s. "
        f"First image after launch can be slow; try raising COMFYUI_TIMEOUT in .env."
    )


def _extract_output_path(history_record: dict, save_node_id: str) -> Path:
    outputs = history_record.get("outputs") or {}
    node_out = outputs.get(save_node_id)
    if not node_out:
        raise ComfyUIError(
            f"SaveImage node '{save_node_id}' produced no output. "
            f"Available outputs: {list(outputs)}"
        )
    images = node_out.get("images") or []
    if not images:
        raise ComfyUIError(f"SaveImage node '{save_node_id}' has no images.")
    img = images[0]
    filename = img.get("filename")
    subfolder = img.get("subfolder", "") or ""
    if not filename:
        raise ComfyUIError(f"SaveImage output has no filename: {img}")

    full = config.COMFYUI_OUTPUT_DIR / subfolder / filename
    return full
