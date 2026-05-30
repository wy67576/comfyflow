#!/usr/bin/env python3
"""
comfyflow CLI — control ComfyUI from the terminal.

Usage
-----
  comfyflow generate --template wan_t2v --prompt "A cat"
  comfyflow run workflow.json --watch
  comfyflow templates
  comfyflow health
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from . import __version__, templates
from .client import ComfyClient


def build_arg_parser():
    import argparse

    p = argparse.ArgumentParser(
        prog="comfyflow",
        description="Control ComfyUI from the command line.",
    )
    p.add_argument(
        "--url",
        default="http://127.0.0.1:8188",
        help="ComfyUI base URL (default: http://127.0.0.1:8188)",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"comfyflow {__version__}",
    )

    sub = p.add_subparsers(dest="command", required=True)

    # ── generate ─────────────────────────────────────────────────
    gen = sub.add_parser("generate", help="Generate using a template")
    gen.add_argument(
        "--template",
        "-t",
        required=True,
        help="Template name (see: comfyflow templates)",
    )
    gen.add_argument("--prompt", "-p", required=True, help="Text prompt")
    gen.add_argument(
        "--negative-prompt", "-n", default="", help="Negative prompt"
    )
    gen.add_argument("--width", type=int, default=832, help="Output width")
    gen.add_argument("--height", type=int, default=480, help="Output height")
    gen.add_argument("--frames", type=int, default=49, help="Number of frames")
    gen.add_argument("--steps", type=int, default=30, help="Sampling steps")
    gen.add_argument("--cfg", type=float, default=6.0, help="CFG scale")
    gen.add_argument("--seed", type=int, default=None, help="Random seed")
    gen.add_argument(
        "--wait", "-w", action="store_true", help="Wait for completion"
    )
    gen.add_argument(
        "--poll-interval",
        type=float,
        default=10.0,
        help="Seconds between polls (default: 10)",
    )

    # ── run ─────────────────────────────────────────────────────
    run_p = sub.add_parser(
        "run", help="Run a workflow JSON file"
    )
    run_p.add_argument("workflow_path", help="Path to workflow JSON file")
    run_p.add_argument(
        "--watch", action="store_true", help="Wait for completion"
    )
    run_p.add_argument(
        "--poll-interval",
        type=float,
        default=10.0,
        help="Seconds between polls (default: 10)",
    )

    # ── templates ─────────────────────────────────────────────────
    sub.add_parser("templates", help="List available templates")

    # ── health ───────────────────────────────────────────────────
    sub.add_parser("health", help="Check ComfyUI connectivity")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    client = ComfyClient(args.url)

    try:
        if args.command == "templates":
            return _cmd_templates()
        elif args.command == "health":
            return _cmd_health(client)
        elif args.command == "run":
            return _cmd_run(client, args)
        elif args.command == "generate":
            return _cmd_generate(client, args)
        else:
            parser.print_help()
            return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


# ── Command implementations ────────────────────────────────────────


def _cmd_templates() -> int:
    print(f"{'Name':<20} Description")
    print("-" * 60)
    for t in templates.list_templates():
        print(f"{t['name']:<20} {t['description']}")
    return 0


def _cmd_health(client: ComfyClient) -> int:
    ok = client.health()
    if ok:
        print(f"✅ ComfyUI reachable at {client.base_url}")
        return 0
    else:
        print(f"❌ Cannot reach ComfyUI at {client.base_url}")
        return 1


def _cmd_run(client: ComfyClient, args) -> int:
    wf_path = Path(args.workflow_path)
    if not wf_path.exists():
        print(f"File not found: {wf_path}", file=sys.stderr)
        return 1

    workflow = json.loads(wf_path.read_text("utf-8"))
    prompt_id = client.queue_prompt(workflow)
    print(f"Queued: {prompt_id}")

    if args.watch:
        return _watch(client, prompt_id, args.poll_interval)
    return 0


def _cmd_generate(client: ComfyClient, args) -> int:
    try:
        template_fn = templates.get_template(args.template)
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    workflow = template_fn(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        steps=args.steps,
        cfg=args.cfg,
        seed=args.seed,
    )
    prompt_id = client.queue_prompt(workflow, client_id="comfyflow-cli")
    print(f"Queued: {prompt_id}")
    print(f"Template: {args.template}")
    print(f"Prompt: {args.prompt[:60]}{'…' if len(args.prompt) > 60 else ''}")

    if args.wait:
        return _watch(client, prompt_id, args.poll_interval)
    return 0


def _watch(
    client: ComfyClient,
    prompt_id: str,
    poll_interval: float,
) -> int:
    """Poll until the prompt finishes, then print results."""
    print(f"Waiting (poll every {poll_interval}s)…")
    start = time.time()

    def progress(_pid):
        elapsed = int(time.time() - start)
        print(f"  … still running [{elapsed}s]", end="\r", file=sys.stderr)

    result = client.wait_for(
        prompt_id,
        poll_interval=poll_interval,
        progress_cb=progress,
    )
    elapsed = int(time.time() - start)
    print(f"\nDone in {elapsed}s — status: {result.status}")

    if result.succeeded:
        paths = result.output_paths
        if paths:
            print("\nOutput files:")
            for p in paths:
                print(f"  📁 {p}")
            print("\nOutput directory: ComfyUI/output/")
        else:
            print("(no output files found)")
        return 0
    elif result.error:
        print(f"\nComfyUI error:\n  {result.error}")
        return 1
    else:
        print(f"\nRun ended with status: {result.status}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
