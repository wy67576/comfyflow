"""
ComfyUI HTTP API client.

Wraps the ComfyUI /prompt, /queue, /history, /view endpoints
so you can submit, poll, and retrieve results programmatically.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


class ComfyClient:
    """A lightweight client for the ComfyUI HTTP API.

    Usage
    -----
    >>> client = ComfyClient("http://127.0.0.1:8188")
    >>> pid = client.queue_prompt(workflow)
    >>> result = client.wait_for(pid, poll_interval=5)
    >>> for path in result.output_paths:
    ...     print(path)
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def queue_prompt(
        self,
        workflow: dict[str, Any],
        client_id: str = "comfyflow",
    ) -> str:
        """Submit a workflow JSON and return the prompt_id (str)."""
        payload = {"prompt": workflow, "client_id": client_id}
        body = self._post("/prompt", payload)
        return body["prompt_id"]

    def get_history(self, prompt_id: str) -> dict[str, Any] | None:
        """Return the full history entry for *prompt_id*, or None."""
        body = self._get(f"/history/{prompt_id}")
        return body.get(prompt_id)

    def queue_status(self) -> dict[str, Any]:
        """Return current queue state (running + pending)."""
        return self._get("/queue")

    def is_running(self, prompt_id: str) -> bool:
        """Check if *prompt_id* is still in the execution queue."""
        q = self.queue_status()
        for entry in q.get("queue_running", []):
            if entry[1] == prompt_id:
                return True
        for entry in q.get("queue_pending", []):
            if entry[1] == prompt_id:
                return True
        return False

    def wait_for(
        self,
        prompt_id: str,
        poll_interval: float = 10.0,
        timeout: float | None = 600.0,
        progress_cb=None,
    ) -> "RunResult":
        """Block until *prompt_id* finishes or *timeout* expires.

        Returns a ``RunResult`` with status/outputs/error info.
        """
        deadline = None if timeout is None else time.time() + timeout
        while True:
            if deadline and time.time() > deadline:
                return RunResult(prompt_id=prompt_id, status="timeout")

            if not self.is_running(prompt_id):
                history = self.get_history(prompt_id)
                if history is None:
                    # May have been evicted — treat as unknown
                    return RunResult(prompt_id=prompt_id, status="lost")

                status_str = history.get("status", {}).get("status_str", "unknown")
                outputs = history.get("outputs", {})
                error = None
                for msg in history.get("status", {}).get("messages", []):
                    if msg[0] == "execution_error":
                        error = msg[1].get("exception_message", "unknown error")

                return RunResult(
                    prompt_id=prompt_id,
                    status=status_str,
                    outputs=outputs,
                    error=error,
                )

            if progress_cb:
                progress_cb(prompt_id)
            time.sleep(poll_interval)

    def get_output_filenames(self, outputs: dict) -> list[str]:
        """Extract output filenames from a ComfyUI outputs dict."""
        names: list[str] = []
        for _node_id, node_out in outputs.items():
            images = node_out.get("images") or node_out.get("gifs") or []
            for img in images:
                fname = img.get("filename", "")
                if fname:
                    names.append(fname)
        return names

    def health(self) -> bool:
        """Quick check that ComfyUI is reachable."""
        try:
            self._get("/queue")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, data: dict) -> dict:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._do(req)

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        return self._do(req)

    def _do(self, req: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise ComfyUIError(
                f"HTTP {exc.code}: {raw[:500]}",
                status_code=exc.code,
                body=raw,
            ) from exc
        except urllib.error.URLError as exc:
            raise ComfyUIError(f"Connection failed: {exc.reason}") from exc


class RunResult:
    """The outcome of a single prompt execution."""

    def __init__(
        self,
        prompt_id: str,
        status: str = "unknown",
        outputs: dict | None = None,
        error: str | None = None,
    ):
        self.prompt_id = prompt_id
        self.status = status  # "success" | "error" | "timeout" | "lost"
        self.outputs = outputs or {}
        self.error = error

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    @property
    def failed(self) -> bool:
        return self.status in ("error", "timeout", "lost")

    @property
    def output_paths(self) -> list[str]:
        """List of output filenames (relative to ComfyUI's output dir)."""
        paths: list[str] = []
        for _nid, node_out in self.outputs.items():
            for key in ("images", "gifs"):
                for item in node_out.get(key, []):
                    fname = item.get("filename", "")
                    if fname:
                        sub = item.get("subfolder", "")
                        paths.append(str(Path(sub) / fname) if sub else fname)
        return paths

    def __repr__(self) -> str:
        return (
            f"RunResult(prompt_id={self.prompt_id[:12]}..., "
            f"status={self.status})"
        )


class ComfyUIError(Exception):
    """Raised when ComfyUI returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
