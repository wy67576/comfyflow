"""
Pre-built workflow templates.

Each template is a callable that returns a complete ComfyUI workflow
dict with sensible defaults.  Templates have been tested on real hardware.
"""
from __future__ import annotations

import random
from typing import Any


def wan_t2v(
    prompt: str,
    *,
    negative_prompt: str = "",
    width: int = 832,
    height: int = 480,
    num_frames: int = 49,
    steps: int = 30,
    cfg: float = 6.0,
    seed: int | None = None,
    model: str = "wan2.1-t2v-1.3b-Q3_K_S.gguf",
    vae: str = "Wan2_1_VAE_bf16.safetensors",
    t5: str = "umt5-xxl-enc-fp8_e4m3fn.safetensors",
) -> dict[str, Any]:
    """Wan2.1 Text-to-Video workflow (tested on RTX 4070 8GB).

    Parameters
    ----------
    prompt : str
        Positive text prompt describing the video.
    negative_prompt : str
        Negative prompt.
    width, height : int
        Output resolution (must be multiples of 8).
    num_frames : int
        Number of frames (49 ≈ 2 s at 24 fps).
    steps : int
        Sampling steps (20-40, lower = faster but lower quality).
    cfg : float
        Classifier-free guidance scale (4.0-7.0).
    seed : int or None
        Random seed (None = auto).
    model : str
        GGUF model filename in ``ComfyUI/models/diffusion_models/``.
    vae : str
        VAE filename in ``ComfyUI/models/vae/``.
    t5 : str
        T5 text-encoder filename in ``ComfyUI/models/text_encoders/``.
    """
    safe_seed = seed if seed is not None else random.randint(0, 2**32)

    return {
        "1": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": model,
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device",
            },
        },
        "2": {
            "class_type": "LoadWanVideoT5TextEncoder",
            "inputs": {"model_name": t5, "precision": "bf16"},
        },
        "3": {
            "class_type": "WanVideoTextEncode",
            "inputs": {
                "positive_prompt": prompt,
                "negative_prompt": negative_prompt or "ugly, blurry, low quality",
                "t5": ["2", 0],
                "force_offload": True,
            },
        },
        "4": {
            "class_type": "WanVideoEmptyEmbeds",
            "inputs": {
                "width": width,
                "height": height,
                "num_frames": num_frames,
            },
        },
        "5": {
            "class_type": "WanVideoVAELoader",
            "inputs": {"model_name": vae, "precision": "bf16"},
        },
        "6": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["1", 0],
                "image_embeds": ["4", 0],
                "steps": steps,
                "cfg": cfg,
                "shift": 5.0,
                "seed": safe_seed,
                "force_offload": True,
                "scheduler": "unipc",
                "riflex_freq_index": 0,
                "text_embeds": ["3", 0],
            },
        },
        "7": {
            "class_type": "WanVideoDecode",
            "inputs": {
                "vae": ["5", 0],
                "samples": ["6", 0],
                "enable_vae_tiling": True,
                "tile_x": 272,
                "tile_y": 272,
                "tile_stride_x": 144,
                "tile_stride_y": 128,
            },
        },
        "8": {
            "class_type": "SaveAnimatedWEBP",
            "inputs": {
                "images": ["7", 0],
                "filename_prefix": "comfyflow_output",
                "fps": 12,
                "lossless": False,
                "quality": 90,
                "method": "default",
            },
        },
    }


# ── Registry ──────────────────────────────────────────────────────────

TEMPLATES: dict[str, tuple[str, type]] = {
    "wan_t2v": ("Wan2.1 Text-to-Video (1.3B, 8GB-friendly)", wan_t2v),
}


def list_templates() -> list[dict]:
    """Return metadata about every available template."""
    return [
        {"name": name, "description": desc}
        for name, (desc, _fn) in TEMPLATES.items()
    ]


def get_template(name: str):
    """Look up a template function by name."""
    entry = TEMPLATES.get(name)
    if entry is None:
        raise KeyError(
            f"Unknown template {name!r}. "
            f"Available: {', '.join(TEMPLATES)}"
        )
    return entry[1]
