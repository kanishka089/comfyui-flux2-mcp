"""Cross-platform installer for comfyui-flux2-mcp.

Creates a .venv/, installs the package + dependencies into it, copies
.env.example to .env if needed, and prints the snippet you should paste
into your Claude MCP config.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
VENV_DIR = ROOT / ".venv"


def _venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _claude_mcp_path() -> Path:
    # Same path on all OSes: ~/.claude/mcp.json
    return Path.home() / ".claude" / "mcp.json"


def step(msg: str) -> None:
    print(f"\n>> {msg}")


def main() -> int:
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required (you have {sys.version.split()[0]}).")
        return 1

    step("Creating virtualenv at .venv/")
    if VENV_DIR.exists():
        print("    .venv already exists, reusing.")
    else:
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])

    py = _venv_python()
    if not py.exists():
        print(f"ERROR: expected venv Python at {py} but it's not there.")
        return 1

    step("Upgrading pip in the venv")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])

    step("Installing comfyui-flux2-mcp + dependencies")
    subprocess.check_call([str(py), "-m", "pip", "install", "-e", str(ROOT), "--quiet"])

    step("Setting up .env")
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if env_file.exists():
        print("    .env already exists, leaving untouched.")
    else:
        shutil.copyfile(env_example, env_file)
        print(f"    Created {env_file}")
        print("    EDIT this file: set COMFYUI_INPUT_DIR and COMFYUI_OUTPUT_DIR for your ComfyUI install.")

    step("Probing ComfyUI")
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=3) as r:
            if r.status == 200:
                print("    ComfyUI reachable at http://127.0.0.1:8188")
    except Exception:
        print("    ComfyUI is NOT currently reachable at http://127.0.0.1:8188")
        print("    That's fine for installation, but the MCP tools won't work until you launch ComfyUI.")

    step("Claude MCP config snippet")
    server_path = ROOT / "src" / "server.py"
    print("")
    print(f"    Add this entry under \"mcpServers\" in {_claude_mcp_path()}:")
    print("")
    print('    "comfyui-flux2": {')
    print(f'      "command": "{py.as_posix()}",')
    print(f'      "args": ["{server_path.as_posix()}"]')
    print('    }')
    print("")
    print("    Then restart Claude Code and run /mcp to verify.")

    print("\nDone.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
