# comfyui-flux2-mcp

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that lets **Claude** generate and edit images on your own machine via a local **ComfyUI** + **FLUX.2 Klein 9B** install.

Once registered, you can say things like *"generate an image of a hummingbird in flight"* in any Claude Code conversation. Claude calls this server, the image renders on your GPU, and you get back the path to the saved PNG. Editing works the same way: *"edit `C:/photos/garden.jpg` — make it look like autumn"*.

No cloud GPU rental. No API costs. Your prompts and outputs never leave your machine.

## Tools exposed

The server registers with MCP under the name **`comfyui-flux2`** and exposes two tools:

| Tool | Signature | Purpose |
|---|---|---|
| `generate_image` | `(prompt, width=1024, height=1024, seed=-1)` | Text-to-image with FLUX.2 Klein 9B. Width/height must be multiples of 16. `seed=-1` randomizes per call. Returns the absolute path to the saved PNG. |
| `edit_image` | `(source_path, prompt, seed=-1)` | Kontext-style image editing — the source image becomes a latent reference and the prompt is the edit instruction (e.g. *"make it nighttime"*, *"add snow"*). Returns the absolute path to the edited PNG. |

## Architecture

A deliberately thin stack — three small modules, no framework beyond the official MCP SDK:

```
Claude (any MCP client)
   │  stdio (JSON-RPC via FastMCP)
   ▼
src/server.py        — tool definitions; loads a workflow template,
   │                   patches prompt/size/seed/model filenames per call
   ▼
src/comfy_client.py  — thin wrapper over ComfyUI's HTTP API:
   │                   POST /prompt to submit, poll GET /history/<id>
   │                   every 3 s until success/error/timeout
   ▼
ComfyUI (local, default http://127.0.0.1:8188)
   └─ saves PNGs under COMFYUI_OUTPUT_DIR/mcp/
```

- **`src/templates/t2i.json`** — API-format text-to-image workflow: `UnetLoaderGGUF → CLIPTextEncode (Qwen3) → Flux2Scheduler → SamplerCustomAdvanced → VAEDecode → SaveImage`.
- **`src/templates/edit.json`** — edit workflow: the source image is copied into ComfyUI's `input/` under a unique staged name, `VAEEncode`d, and injected as a `ReferenceLatent` alongside the instruction prompt (the staged copy is cleaned up after the run).
- **`src/config.py`** — all configuration comes from `.env` (loaded with `python-dotenv`); model/CLIP/VAE filenames are patched into the templates at call time, so swapping FLUX.2 variants needs no code change.
- Dependencies: `mcp`, `requests`, `python-dotenv` (see `pyproject.toml`).

### Repo layout

```
install.py            cross-platform installer (venv + deps + .env + config snippet)
pyproject.toml        package metadata (entry point: comfyui-flux2-mcp = server:main)
.env.example          documented config template — copy to .env
src/
  server.py           MCP server + the two tools
  comfy_client.py     ComfyUI HTTP API client
  config.py           env-driven configuration
  templates/          t2i.json, edit.json (API-format workflows)
tests/
  test_smoke.py       end-to-end smoke test (calls both tools against a live ComfyUI)
```

## Requirements

You need a working ComfyUI install with FLUX.2 Klein 9B before this is useful:

- **ComfyUI** running locally (the portable Windows build works great)
- **FLUX.2 Klein 9B GGUF** — quantized model file in `ComfyUI/models/unet/` ([unsloth/FLUX.2-klein-9B-GGUF](https://huggingface.co/unsloth/FLUX.2-klein-9B-GGUF); default expected filename `flux-2-klein-9b-Q4_K_S.gguf`)
- **Qwen3 8B text encoder** — `qwen_3_8b_fp8mixed.safetensors` in `ComfyUI/models/text_encoders/`
- **FLUX.2 VAE** — `flux2-vae.safetensors` in `ComfyUI/models/vae/`
- **ComfyUI-GGUF** custom node by city96 ([github.com/city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF))
- **Python 3.10+** on your PATH

Tested with: ComfyUI v0.21.x, PyTorch 2.11 + CUDA 13, RTX 3060 Laptop 6 GB. About **60 s** per 1024×1024 generation, **90 s** per edit. The Q4 quant fits comfortably in 6 GB VRAM with ComfyUI's low-VRAM swapping.

## Install

```bash
git clone https://github.com/kanishka089/comfyui-flux2-mcp.git
cd comfyui-flux2-mcp
python install.py
```

`install.py` will:

1. Create a `.venv/` and install the package + dependencies into it
2. Copy `.env.example` → `.env` (if missing)
3. Probe whether ComfyUI is reachable at `http://127.0.0.1:8188`
4. Print the exact snippet to paste into your Claude MCP config

Then **edit `.env`** to point `COMFYUI_INPUT_DIR` and `COMFYUI_OUTPUT_DIR` at *your* ComfyUI's `input/` and `output/` folders.

## Register with Claude Code

Easiest: one CLI command (use `--scope user` to make the tools available in **every** project, not just the current one):

```bash
claude mcp add --scope user comfyui-flux2 -- <repo>/.venv/Scripts/python.exe <repo>/src/server.py
```

(On Linux/macOS the venv Python is at `<repo>/.venv/bin/python`.)

Or add it manually to your MCP config (`~/.claude.json` under `mcpServers`, or `~/.claude/mcp.json` depending on your Claude Code version):

```json
"comfyui-flux2": {
  "command": "D:/path/to/comfyui-flux2-mcp/.venv/Scripts/python.exe",
  "args": ["D:/path/to/comfyui-flux2-mcp/src/server.py"]
}
```

Restart Claude Code and run `/mcp` — you should see `comfyui-flux2 ✓ Connected`.

## Usage

In any Claude conversation:

> *"Use comfyui-flux2 to generate an image of a Sri Lankan tea plantation at sunrise"*

> *"Use comfyui-flux2 to edit `D:/photos/garden.png` — make it a winter scene with snow"*

Claude calls the tool, waits for the generation, and reports the saved path (under `COMFYUI_OUTPUT_DIR/mcp/`). Open the file in any image viewer.

## Configuration (`.env`)

| Variable | Default | What it does |
|---|---|---|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | Where ComfyUI is listening |
| `COMFYUI_INPUT_DIR` | (required) | ComfyUI's `input/` folder — must be writable by the MCP server (used to stage `edit_image` sources) |
| `COMFYUI_OUTPUT_DIR` | (required) | Where ComfyUI saves outputs |
| `COMFYUI_TIMEOUT` | `300` | Seconds before giving up on a generation |
| `FLUX2_MODEL_FILE` | `flux-2-klein-9b-Q4_K_S.gguf` | Filename of the GGUF unet |
| `FLUX2_CLIP_FILE` | `qwen_3_8b_fp8mixed.safetensors` | Text encoder filename |
| `FLUX2_VAE_FILE` | `flux2-vae.safetensors` | VAE filename |
| `FLUX2_STEPS` | `4` | Sampling steps (Klein is 4-step distilled) |

If you swap to a different FLUX.2 variant (different quantization, the 4B model, etc.), just change `FLUX2_MODEL_FILE` — no code edit needed.

`.env` is gitignored. Keep machine-specific paths (and any secrets, if you add some) out of version control.

## Testing

With ComfyUI running, the smoke test exercises both tools end-to-end (generate, then edit the generated image):

```bash
.venv/Scripts/python.exe tests/test_smoke.py
```

## Troubleshooting

**`ComfyUI not reachable at http://127.0.0.1:8188`** — ComfyUI isn't running. Launch it first (`run_nvidia_gpu.bat` or your custom launcher), wait for "Starting server", then try again.

**`Workflow validation failed: <node>: Value not in list`** — one of `FLUX2_MODEL_FILE` / `FLUX2_CLIP_FILE` / `FLUX2_VAE_FILE` doesn't match a file in your `ComfyUI/models/*/` folders. Check spelling and that the file is actually present.

**Tool times out at 300 s** — the first generation after launching ComfyUI is slow (model load + low-VRAM swap). Bump `COMFYUI_TIMEOUT=600` and try once; subsequent calls should be fast.

**Edit produces unrelated images** — `edit_image` needs `source_path` to point at a real image file (PNG/JPG). It copies the file into ComfyUI's `input/` folder per call; if the copy fails (permission denied, wrong path), the workflow falls back to a default and the output won't reflect your source.

**Server starts but warns about missing dirs** — `server.py` validates `COMFYUI_INPUT_DIR` / `COMFYUI_OUTPUT_DIR` eagerly on startup and prints a warning to stderr if either doesn't exist. Fix the paths in `.env`.

## License

The MCP server code: **MIT** (see [LICENSE](LICENSE)).

The FLUX.2 Klein 9B model itself: **FLUX Non-Commercial License** by Black Forest Labs — **you cannot legally sell outputs** generated with FLUX.2 Klein. For commercial use you'd need a commercial FLUX license, or switch the underlying model to something like FLUX.1 [schnell] (Apache 2.0) — the same workflows mostly carry over with `FLUX2_MODEL_FILE` changed and one node-type swap.

## Status

- **v0.1.0** — initial release, both tools working end-to-end.
- Tested on Windows 11 (ComfyUI portable). Should work on Linux and macOS — paths use `pathlib.Path` and forward slashes throughout — but those platforms haven't been exercised. [File an issue](https://github.com/kanishka089/comfyui-flux2-mcp/issues) if something breaks.
- Scope: this repo is **images only**. Sibling local-generation MCP servers for video (Wan 2.1) and music (ACE-Step) exist as separate projects and are not part of this codebase.
