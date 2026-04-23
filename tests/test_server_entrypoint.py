from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http(url: str, timeout_s: float = 5.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"timeout waiting for {url}")


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_server_entrypoint_is_truthful_gateway() -> None:
    port = _free_port()
    env = dict(os.environ)
    env["PORT"] = str(port)

    proc = subprocess.Popen(
        ["node", "server.js"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_http(f"http://127.0.0.1:{port}/health")

        root = _get_json(f"http://127.0.0.1:{port}/")
        assert root["status"] == "limited_gateway"
        assert "deployed" not in json.dumps(root, ensure_ascii=False).lower()

        health = _get_json(f"http://127.0.0.1:{port}/health")
        assert health["ok"] is True

        schema = _get_json(f"http://127.0.0.1:{port}/api/voice/schema")
        assert "input_schema" in schema
        assert "output_schema" in schema

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/voice/run",
            data=json.dumps({"intent": "search"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            raise AssertionError("expected 501 for unimplemented run path")
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            assert e.code == 501
            assert body["error"] == "not_implemented"
            assert "canonical" in body["canonical_path"].lower()
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_server_gateway_does_not_duplicate_python_security_logic() -> None:
    source = (ROOT / "server.js").read_text(encoding="utf-8").lower()
    assert "ed25519" not in source
    assert "signature_hmac" not in source
    assert "responsibility_boundary" in source  # only as descriptive message
