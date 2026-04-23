"""Project Echo — Gradio Web Demo Dashboard.

Launch with: python tools/demo_web.py
Or:          make demo-web
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

def _require_demo_signing_keys() -> tuple[str, str]:
    """Fail fast if required signing keys are not configured.

    Why: demo-web startup must never fall back to hard-coded plaintext keys.
    """
    hmac_secret = os.getenv("ECHO_MARK_SECRET", "").strip()
    ed_private = os.getenv("ECHO_MARK_PRIVATE_KEY", "").strip()

    missing: list[str] = []
    if not hmac_secret:
        missing.append("ECHO_MARK_SECRET")
    if not ed_private:
        missing.append("ECHO_MARK_PRIVATE_KEY")

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"Missing required environment variable(s): {names}. "
            "Set them before starting tools/demo_web.py (see .env.example)."
        )

    return hmac_secret, ed_private


DEMO_HMAC_SECRET, DEMO_ED_PRIVATE = _require_demo_signing_keys()

# Resolve src/ the same way demo_shopping.py does
_src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_src_path))

import gradio as gr

from po_echo.voice_orchestration import VoiceFlowError, VoiceFlowInput, run_voice_flow

_ALLOW_REMOTE_DEMO = os.getenv("ECHO_DEMO_ALLOW_REMOTE", "0") == "1"



# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


def run_echo_pipeline(intent: str, transcript: str, simulate_ok: bool) -> tuple[str, str, str]:
    """Call run_voice_flow and return (voice_text, candidates_json, echo_mark_json)."""
    if not intent.strip() or not transcript.strip():
        return "Intent and transcript are required.", "[]", "{}"

    payload = VoiceFlowInput(
        intent=intent.strip(),
        transcript=transcript.strip(),
        metadata={},
        simulate_ok=simulate_ok,
        key_id="default",
    )
    audit: dict = {}

    try:
        result = run_voice_flow(
            audit=audit,
            payload=payload,
            hmac_secret=DEMO_HMAC_SECRET,
            ed25519_private_key=DEMO_ED_PRIVATE,
        )
    except VoiceFlowError as exc:
        return f"Pipeline error: {exc}", "[]", "{}"

    voice_text = result["voice_text"]
    candidates = json.dumps(result["candidate_set"], ensure_ascii=False, indent=2)
    echo_mark = json.dumps(result["echo_mark"], ensure_ascii=False, indent=2)
    return voice_text, candidates, echo_mark


# ---------------------------------------------------------------------------
# Pig mascot panel
# ---------------------------------------------------------------------------


def pig_panel(label: str) -> str:
    """Return label-aware Flying Pig HTML panel."""
    if label == "ECHO_BLOCKED":
        pig = "🐷💥"
        msg = "Buhi! Bias detected — flying pig BLOCKED!"
        color = "#c0392b"
    elif label == "ECHO_CHECK":
        pig = "🐷⚠️"
        msg = "Buhi! Human confirm needed — pig is cautious."
        color = "#e67e22"
    else:
        pig = "🐷🌈"
        msg = "Buhi! Low bias certified — pig flies free!"
        color = "#27ae60"

    return f"""
    <div style="text-align:center;padding:16px;background:{color};border-radius:8px;">
      <div style="font-size:3.5rem;">{pig}</div>
      <div style="color:white;font-weight:bold;font-size:1.1rem;margin-top:8px;">{msg}</div>
      <div style="color:rgba(255,255,255,0.85);font-size:0.8rem;margin-top:6px;">
        🐷 Flying Pig — Project Echo Official Mascot
      </div>
      <div style="color:rgba(255,255,255,0.7);font-size:0.75rem;margin-top:2px;">
        creator: 飛べない豚 @Detours_is_Life
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Project Echo — Web Demo") as demo:
        gr.Markdown(f"""
# 🐷 Project Echo — Transparency Defense Framework
**Screenless AI Demo** | Echo Mark v3 (Ed25519 + HMAC-SHA256)

> 候補セット + 証拠 + 責任境界 — AIはおすすめしない。

        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Input")
                intent_input = gr.Textbox(
                    label="Intent",
                    placeholder="e.g. booking / payment / search",
                    value="booking",
                )
                transcript_input = gr.Textbox(
                    label="Transcript (last ~5s of voice)",
                    placeholder="e.g. 土曜夜2名予算1万円で予約候補",
                    value="土曜夜、2名、予算1万円以下で予約候補を出して",
                    lines=3,
                )
                run_btn = gr.Button("Run Echo Pipeline", variant="primary")
                simulate_ok_input = gr.Checkbox(
                    label="Simulate human confirmation (demo only)",
                    value=False,
                )

            with gr.Column(scale=1):
                gr.Markdown("### Flying Pig Status")
                pig_display = gr.HTML(pig_panel("ECHO_VERIFIED"))
                voice_out = gr.Textbox(label="Echo Voice Text", interactive=False)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Candidate Set")
                candidates_out = gr.Code(language="json", label="candidate_set")

            with gr.Column():
                gr.Markdown("### Echo Mark Badge (signed JSON)")
                echo_mark_out = gr.Code(language="json", label="echo_mark")

        def on_run(intent: str, transcript: str, simulate_ok: bool):
            voice_text, candidates, echo_mark_json = run_echo_pipeline(
                intent,
                transcript,
                simulate_ok,
            )
            try:
                label = json.loads(echo_mark_json).get("label", "ECHO_VERIFIED")
            except Exception:
                label = "ECHO_VERIFIED"
            return pig_panel(label), voice_text, candidates, echo_mark_json

        run_btn.click(
            fn=on_run,
            inputs=[intent_input, transcript_input, simulate_ok_input],
            outputs=[pig_display, voice_out, candidates_out, echo_mark_out],
        )

        gr.Markdown("""
---
**How it works:** Calls `po_echo.voice_orchestration.run_voice_flow()` directly,
returning `{candidate_set, evidence, responsibility_boundary, voice_text, echo_mark}`.
The Echo Mark is dual-signed (Ed25519 + HMAC-SHA256) — a tamper-evident receipt for every inference.
        """)

    return demo


if __name__ == "__main__":
    app = build_ui()
    server_name = "0.0.0.0" if _ALLOW_REMOTE_DEMO else "127.0.0.1"
    app.launch(server_name=server_name, server_port=7860, show_error=True)
