<div align="center">

# comfyflow 🎬

**Control ComfyUI from your terminal — no browser needed.**

[![PyPI version](https://img.shields.io/pypi/v/comfyflow-cli?color=blue)](https://pypi.org/project/comfyflow-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/comfyflow-cli)](https://pypi.org/project/comfyflow-cli/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/wy67576/comfyflow?style=social)](https://github.com/wy67576/comfyflow)

`comfyflow-cli` is a Python CLI + SDK for programmatically submitting workflows to [ComfyUI](https://github.com/comfyanonymous/ComfyUI).  
Write a prompt, run a command, get your video. Designed and tested on **8GB VRAM GPUs**.

```bash
pip install comfyflow-cli
comfyflow generate --template wan_t2v --prompt "a cat walking in a cyberpunk city" --wait
```

</div>

---

## Demo

*Coming soon* — demo GIF showing `comfyflow generate --template wan_t2v --prompt "..."` in action.

---

## Why?

ComfyUI is powerful, but every generation requires:
1. Open the browser
2. Drag nodes around
3. Tweak parameters by hand
4. Click "Queue Prompt"
5. Wait and hope

**`comfyflow` changes that.** One command → video out.  
Perfect for batch jobs, CI pipelines, scripts, and headless servers.

## Features

- **CLI mode** — generate video/image with a single command
- **Python SDK** — `ComfyClient` class for programmatic control
- **Pre-built templates** — Wan2.1 T2V, more coming
- **8GB-friendly** — all templates tested on RTX 4070 8GB
- **Poll & wait** — block until generation completes, get output paths
- **Error reporting** — clear messages when ComfyUI fails
- **Zero GUI** — works headless, no browser needed

## Quick start

### 1. Install

```bash
# Via PyPI (once approved)
pip install comfyflow-cli

# Via GitHub Releases (works now)
pip install https://github.com/wy67576/comfyflow/releases/download/v0.1.0/comfyflow_cli-0.1.0-py3-none-any.whl
```

### 2. Generate your first video

```bash
comfyflow generate \
  --template wan_t2v \
  --prompt "a samurai standing in a bamboo forest, cinematic lighting, anime style" \
  --wait
```

Output lands in `ComfyUI/output/comfyflow_output_00001_.webp`.

### 3. Check health

```bash
$ comfyflow health
✅ ComfyUI reachable at http://127.0.0.1:8188
```

## Usage

### CLI

```bash
# List available templates
comfyflow templates

# Generate without waiting (get prompt_id, poll later)
comfyflow generate --template wan_t2v --prompt "a cat"

# Generate and wait for result
comfyflow generate --template wan_t2v --prompt "a cat" --wait

# Run a custom workflow JSON
comfyflow run my_workflow.json --watch

# Customize parameters
comfyflow generate \
  --template wan_t2v \
  --prompt "explosion in space, colorful nebula" \
  --width 832 --height 480 \
  --frames 81 \
  --steps 40 \
  --cfg 7.0 \
  --seed 42 \
  --wait
```

### Python SDK

```python
from comfyflow import ComfyClient, templates

client = ComfyClient("http://192.168.1.100:8188")

# Build a workflow from a template
workflow = templates.wan_t2v(
    prompt="a dancer in a spotlight, dark background",
    width=832,
    height=480,
    num_frames=49,
)

# Submit
pid = client.queue_prompt(workflow)

# Wait (with progress)
result = client.wait_for(pid, poll_interval=10)

if result.succeeded:
    print("Outputs:", result.output_paths)
else:
    print("Failed:", result.error)
```

### Batch generation

```python
from comfyflow import ComfyClient, templates

client = ComfyClient()

prompts = [
    "a red fox in a snowy forest",
    "a blue butterfly on a flower",
    "a green dragon flying over mountains",
]

for i, prompt in enumerate(prompts):
    wf = templates.wan_t2v(prompt=prompt, seed=100 + i)
    pid = client.queue_prompt(wf)
    result = client.wait_for(pid, poll_interval=15)
    print(f"[{i+1}/{len(prompts)}] {result.status}: {result.output_paths}")
```

## Templates

| Name | Description | VRAM |
|------|-------------|------|
| `wan_t2v` | Wan2.1 1.3B T2V — text-to-video, 832×480, ~2 s at 30 steps | ~8 GB |

More templates (AnimateDiff, SDXL, HunyuanVideo) are in development.

## Requirements

- Python 3.9+
- A running [ComfyUI](https://github.com/comfyanonymous/ComfyUI) instance with API enabled
- Required model files in the correct `ComfyUI/models/` directories:
  - `diffusion_models/wan2.1-t2v-1.3b-Q3_K_S.gguf`
  - `vae/Wan2_1_VAE_bf16.safetensors`
  - `text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors`

## Hardware

All templates tested on:
- **GPU:** RTX 4070 8GB
- **RAM:** 16 GB
- **OS:** Windows 11 + WSL2

Generation times (Wan2.1 1.3B, 49 frames, 30 steps): ~5–15 minutes depending on CPU offloading.

## Project structure

```
comfyflow/
├── comfyflow/
│   ├── __init__.py    # Package init
│   ├── client.py      # ComfyUI HTTP client
│   ├── cli.py         # Command-line interface
│   └── templates.py   # Pre-built workflow templates
├── workflows/         # Example workflow JSONs
├── pyproject.toml
└── README.md
```

## FAQ

**Q: Do I need a GPU to use comfyflow?**  
A: Yes — comfyflow controls ComfyUI, which needs a GPU. The machine running comfyflow just needs network access to the ComfyUI host.

**Q: Can I use this remotely?**  
A: Yes. Point `--url` at any reachable ComfyUI instance:  
`comfyflow --url http://192.168.1.100:8188 generate ...`

**Q: Why is generation slow?**  
A: The 1.3B model uses CPU offloading to fit in 8GB VRAM. Each sampling step transfers data between CPU and GPU. This is normal for low-VRAM hardware.

**Q: How is this different from ComfyUI's built-in API?**  
A: ComfyUI has a raw HTTP API. `comfyflow` wraps it with templates, polling, error handling, and a clean CLI — so you don't need to write the boilerplate.

## License

MIT
