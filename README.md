# comfyui-flux2-mcp

An MCP (Model Context Protocol) server that lets **Claude** generate and edit images on your own machine via a local **ComfyUI** + **FLUX.2 Klein 9B** install.

Once configured, you can say things like *"generate an image of a hummingbird in flight"* in a Claude conversation and the model will call this server, render the image on your GPU, and return a path to the saved PNG. Editing works the same way: *"edit `C:/photos/garden.jpg` — make it look like autumn"*.

No cloud GPU rental. No API costs. Your prompts and outputs never leave your machine.

## What it does

Exposes two MCP tools:

| Tool | Purpose |
|---|---|
| `generate_image(prompt, width, height, seed)` | Text-to-image with FLUX.2 Klein 9B |
| `edit_image(source_path, prompt, seed)` | Kontext-style image editing using an existing image as reference |

Under the hood: thin Python wrapper around ComfyUI's HTTP API (`/prompt`, `/history`) using pre-built API-format workflow JSONs.

## Prereqs

You need a working ComfyUI install with FLUX.2 Klein 9B before this is useful. Specifically:

- **ComfyUI** running locally (the portable Windows build works great)
- **FLUX.2 Klein 9B GGUF** — quantized model file in `ComfyUI/models/unet/` ([unsloth/FLUX.2-klein-9B-GGUF](https://huggingface.co/unsloth/FLUX.2-klein-9B-GGUF))
- **Qwen3 8B text encoder** — `qwen_3_8b_fp8mixed.safetensors` in `ComfyUI/models/text_encoders/`
- **FLUX.2 VAE** — `flux2-vae.safetensors` in `ComfyUI/models/vae/`
- **ComfyUI-GGUF** custom node by city96 ([github.com/city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF))
- **Python 3.10+** on your PATH

Tested with: ComfyUI v0.21.x, PyTorch 2.11 + CUDA 13, RTX 3060 Laptop 6 GB. About **60 s** per 1024×1024 generation, **90 s** per edit.

## Install

```bash
git clone https://github.com/kanishka089/comfyui-flux2-mcp.git
cd comfyui-flux2-mcp
python install.py
```

`install.py` will:

1. Create a `.venv/` and install dependencies into it
2. Copy `.env.example` → `.env`
3. Print the snippet to paste into your Claude MCP config (path depends on your OS)

Then edit `.env` to point at **your** ComfyUI's `input/` and `output/` folders, paste the MCP snippet into `~/.claude/mcp.json` (or `~/.claude.json` depending on Claude Code version), restart Claude Code, and run `/mcp` to verify.

## Usage

In any Claude conversation:

> *"Use comfyui-flux2 to generate an image of a Sri Lankan tea plantation at sunrise"*

> *"Use comfyui-flux2 to edit `D:/photos/garden.png` — make it a winter scene with snow"*

Claude will call the tool, wait for the generation, and report the saved path. Open the file in any image viewer.

## Configuration (`.env`)

| Variable | Default | What it does |
|---|---|---|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | Where ComfyUI is listening |
| `COMFYUI_INPUT_DIR` | (required) | ComfyUI's `input/` folder — needs to be a path the MCP server can write to |
| `COMFYUI_OUTPUT_DIR` | (required) | Where ComfyUI saves outputs |
| `COMFYUI_TIMEOUT` | `300` | Seconds before giving up on a generation |
| `FLUX2_MODEL_FILE` | `flux-2-klein-9b-Q4_K_S.gguf` | Filename of the GGUF unet |
| `FLUX2_CLIP_FILE` | `qwen_3_8b_fp8mixed.safetensors` | Text encoder filename |
| `FLUX2_VAE_FILE` | `flux2-vae.safetensors` | VAE filename |
| `FLUX2_STEPS` | `4` | Sampling steps (Klein is 4-step distilled) |

If you swap to a different FLUX.2 variant (different quantization, the 4B model, etc.), just change `FLUX2_MODEL_FILE` — no code edit needed.

## Troubleshooting

**`ComfyUI not reachable at http://127.0.0.1:8188`** — ComfyUI isn't running. Launch it first (`run_nvidia_gpu.bat` or your custom launcher), wait for "Starting server", then try again.

**`Workflow validation failed: <node>: Value not in list`** — one of `FLUX2_MODEL_FILE` / `FLUX2_CLIP_FILE` / `FLUX2_VAE_FILE` doesn't match a file in your `ComfyUI/models/*/` folders. Check spelling and that the file is actually present.

**Tool times out at 300s** — first generation after launching ComfyUI is slow (model load + low-VRAM swap). Bump `COMFYUI_TIMEOUT=600` and try once; subsequent calls should be fast.

**Edit produces unrelated images** — `edit_image` needs the source path to point at a real image file (PNG/JPG). It copies the file into ComfyUI's `input/` folder per call. If the copy fails silently (permission denied, wrong path), the workflow falls back to a default and the output won't reflect your source.

## License

The MCP server code: **MIT** (see [LICENSE](LICENSE)).

The FLUX.2 Klein 9B model itself: **FLUX Non-Commercial License** by Black Forest Labs. **You cannot legally sell outputs** from FLUX.2 Klein. For commercial use you'd need a commercial FLUX license, or switch the underlying model to something like FLUX.1 [schnell] (Apache 2.0) — the same workflows mostly work with just `FLUX2_MODEL_FILE` changed and one node-type swap.

## Status

Tested on Windows 11. Should work on Linux and macOS — paths use `pathlib.Path` and forward slashes everywhere — but not actually exercised on those platforms. [File an issue](https://github.com/kanishka089/comfyui-flux2-mcp/issues) if it doesn't.
