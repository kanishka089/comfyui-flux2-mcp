"""Smoke test: call the two tools directly without going through MCP.

Run with the embedded ComfyUI Python (or any venv that has the deps installed):

    "d:/ComfyUI/ComfyUI_windows_portable/python_embeded/python.exe" tests/test_smoke.py

Assumes ComfyUI is running.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Make sibling modules importable when running this file directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import server  # noqa: E402
import comfy_client  # noqa: E402


def main() -> int:
    print(f"ComfyUI alive: {comfy_client.is_alive()}")
    if not comfy_client.is_alive():
        print("ABORT: ComfyUI not running.")
        return 1

    print("\n--- generate_image ---")
    t = time.time()
    out = server.generate_image("a tiny red cube on a white beach, photograph, golden hour")
    print(f"  Saved: {out}")
    print(f"  Took:  {time.time()-t:.1f}s")
    assert Path(out).is_file(), f"output file missing: {out}"

    print("\n--- edit_image ---")
    t = time.time()
    out2 = server.edit_image(out, "turn the cube into a glowing blue cube at night")
    print(f"  Saved: {out2}")
    print(f"  Took:  {time.time()-t:.1f}s")
    assert Path(out2).is_file(), f"output file missing: {out2}"

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
