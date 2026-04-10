"""
Po-Cosmic CLI

Command-line interface for Cosmic Ethics 39 evaluator.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path if running directly
src_path = Path(__file__).resolve().parents[2] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from po_core.cosmic_ethics_39.evaluator import CosmicEthics39Evaluator
from po_core.cosmic_ethics_39.scenarios import get_scenario
from po_core.diversity import Rec, diversify_with_mmr
from po_echo.device_boundary import (
    DEVICE_CONFIGS,
    DeviceType,
    decide_for_device,
    get_device_description,
    list_devices,
)
from po_echo.echo_mark import (
    get_secret_from_env,
    load_ed25519_keypair,
    load_ed25519_private_key_from_env,
    make_echo_mark,
    make_echo_mark_dual,
    make_echo_mark_ed25519,
    verify_echo_mark_dual,
    verify_mark,
)
from po_echo.execution_gate import gate_audio
from po_echo.voice_orchestration import (
    VOICE_INPUT_SCHEMA,
    VOICE_OUTPUT_SCHEMA,
    VOICE_SCHEMA_HELP,
    VoiceFlowError,
    VoiceFlowInput,
    inventory_voice_stack,
    run_voice_flow,
)

try:
    import nacl.signing  # noqa: F401 - import check for availability

    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False


def prompt_yes_no(msg: str) -> bool:
    """Prompt user for yes/no confirmation."""
    while True:
        ans = input(f"{msg} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please type 'y' or 'n'.")


def transition(exec_obj: dict, to: str, reason: str, meta: dict | None = None) -> None:
    """
    Transition execution state.

    Records state change in history with timestamp. This is the core
    of operator responsibility - every state change is evidence.
    """
    meta = meta or {}
    frm = exec_obj["state"]
    exec_obj["state"] = to
    exec_obj.setdefault("history", []).append(
        {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "frm": frm,
            "to": to,
            "reason": reason,
            "meta": meta,
        }
    )


def simulate_execute(result: dict, fail: bool = False) -> None:
    """
    Simulate execution with state transitions.

    This demonstrates Operator AI behavior: committing to world (BOOKED),
    handling failure (FAILED -> RECOVERING -> RECOVERED), and maintaining
    evidence trail throughout.

    Args:
        result: Evaluation result with execution object
        fail: If True, simulate failure and recovery
    """
    ex = result["execution"]

    # Policy gate - respect responsibility boundary
    if not result.get("final_execution_allowed", False):
        transition(ex, "CANCELLED", "not_allowed_by_policy_or_human")
        return

    # BOOKED - simulated world commit
    transition(ex, "BOOKED", "simulated_booking")

    if fail:
        # Failure path - demonstrates recovery obligation
        transition(ex, "FAILED", "simulated_failure", {"error": "SIM_FAIL"})
        transition(ex, "RECOVERING", "enter_recovery")
        # Recovery steps would execute here (phase 2)
        transition(ex, "RECOVERED", "simulated_recovered")
    else:
        # Success path - world evidence recorded
        ex["receipt_slot"]["reservation_id"] = "RESV_SIM_001"
        transition(ex, "RECOVERED", "simulated_success")


def print_cosmic39(result: dict) -> None:
    """
    Print Cosmic Ethics 39 evaluation result in human-readable format.
    """
    s = result["scenario"]
    scores = result["scores"]
    phil = result["philosophers"]

    print("=" * 80)
    print(f"[Cosmic Ethics 39] {s['meta'].get('name', '(scenario)')}")
    print("=" * 80)

    print(f"Philosopher preset: {phil.get('preset', 'cosmic13')}")
    print(f"Active philosophers: {phil['active_count']}")
    print(
        f"Adjusted score: {scores['adjusted_score']:.2f} "
        f"(uncertainty={scores['uncertainty_penalty']:.2f}, "
        f"irreversibility={scores['irreversibility_penalty']:.2f})"
    )
    print()

    # Top dimensions
    adj = scores["adjusted_scores"]
    top_dims = sorted(adj.items(), key=lambda x: x[1], reverse=True)[:10]
    print("Top dimensions:")
    for k, v in top_dims:
        bar = "█" * int(v * 20)
        print(f"  - {k:35s} {bar} {v:.2f}")
    print()

    # Tension
    print("Tension topk:")
    for item in result["tension_topk"][:10]:
        print(f"  - {item['dimension']:35s} {item['tension_score']:+.3f}")
    print()

    # Blocked options
    print("Blocked options:")
    if not result["blocked_options"]:
        print("  (none)")
    else:
        for b in result["blocked_options"]:
            print(f'  - "{b["option"]}"')
            print(f"    reason: {b['reason']}")
            print(f"    blockers: {', '.join(b['blocking_dimensions'])}")
    print()

    # Responsibility Boundary - Core of Responsible AI
    rb = result.get("responsibility_boundary", {})
    print("Responsibility Boundary:")
    print(f"  AI recommends: {'YES' if rb.get('ai_recommends') else 'NO'}")
    print(f"  Execution allowed: {'YES' if rb.get('execution_allowed') else 'NO'}")
    print(f"  Requires human confirm: {'YES' if rb.get('requires_human_confirm') else 'NO'}")
    print(f"  Liability mode: {rb.get('liability_mode', 'audit-only')}")
    if rb.get("reasons"):
        print(f"  Boundary reasons: {', '.join(rb['reasons'])}")
    if rb.get("blocking_dimensions_merged"):
        print(f"  Blocking dimensions: {', '.join(rb['blocking_dimensions_merged'])}")
    if rb.get("explanation"):
        print(f"  Explanation: {rb['explanation']}")
    print()

    # Human Confirmation - Final Responsibility Protocol
    hc = result.get("human_confirmation", {})
    if hc.get("method") and hc["method"] != "none":
        print("Human Confirmation:")
        print(f"  Method: {hc['method']}")
        print(f"  Decision: {hc.get('decision', 'n/a')}")
        print(f"  Confirmed at: {hc.get('confirmed_at', 'n/a')}")
        print(f"  Confirmed by: {hc.get('confirmed_by', 'n/a')}")
        print()

    # Final Execution Allowed - Ultimate Responsibility Boundary
    final = result.get("final_execution_allowed")
    if final is not None:
        print(f"Final execution allowed: {'YES' if final else 'NO'}")
        print()

    # Execution - Operator State Machine (world commits & recovery)
    ex = result.get("execution", {})
    if ex:
        print("Execution (Operator State Machine):")
        print(f"  State: {ex.get('state', 'UNKNOWN').upper()}")
        print(f"  Allowed by policy: {'YES' if ex.get('allowed_by_policy') else 'NO'}")
        print(f"  Human decision: {ex.get('human_decision', 'none')}")

        # Receipt slot (world evidence)
        receipt = ex.get("receipt_slot", {})
        if any(receipt.values()):
            print(f"  Receipt: reservation_id={receipt.get('reservation_id', 'none')}")

        # State history (audit trail)
        history = ex.get("history", [])
        if len(history) > 1:  # More than just init
            print(f"  State transitions: {len(history)}")
            for h in history[-3:]:  # Show last 3
                print(f"    {h['ts']}: {h.get('frm', 'null')} -> {h['to']} ({h['reason']})")
        print()

    print(f"Runtime: {result['runtime_sec']:.3f} seconds")
    print("=" * 80)


def save_json(result: dict, out_path: Path) -> None:
    """Save evaluation result to JSON file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_cosmic39(args: argparse.Namespace) -> None:
    """Execute cosmic-39 command."""
    # Get scenario
    scenario_text, meta = get_scenario(args.scenario)

    # Run evaluation with preset
    evaluator = CosmicEthics39Evaluator(preset=args.preset)
    result = evaluator.evaluate(scenario_text, meta)

    # Human confirmation process
    rb = result.get("responsibility_boundary", {})
    need = bool(rb.get("requires_human_confirm", True))
    allowed = bool(rb.get("execution_allowed", False))

    # Default: evaluator's decision is respected (no human confirmation needed if not required)
    final_allowed = allowed
    human = result.get("human_confirmation") or {
        "required": need,
        "method": "none",
        "confirmed_at": None,
        "confirmed_by": None,
        "decision": None,
    }

    human["required"] = need

    if args.confirm and need:
        # Never "recommend" - only ask for permission
        print("Human confirmation required.")
        print(f"- Execution allowed by policy: {'YES' if allowed else 'NO'}")
        if allowed:
            ok = prompt_yes_no("Allow execution?")
            human["method"] = "cli_yesno"
            human["confirmed_by"] = "po-cosmic"
            human["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
            human["decision"] = "yes" if ok else "no"
            final_allowed = allowed and ok
            if not ok:
                # Human denied - record for audit
                rb.setdefault("reasons", []).append("human_denied")
                rb.setdefault("blocking_dimensions_merged", []).append("human_denied")
                rb["explanation"] = "Execution blocked: human denied."
        else:
            # Execution not allowed by policy - confirmation is not meaningful
            human["method"] = "cli_yesno"
            human["confirmed_by"] = "po-cosmic"
            human["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
            human["decision"] = "n/a"
            final_allowed = False

    # Update result with human confirmation and final decision
    result["responsibility_boundary"] = rb
    result["human_confirmation"] = human
    result["final_execution_allowed"] = final_allowed

    # Update execution object with human decision
    if "execution" in result:
        result["execution"]["human_decision"] = human.get("decision")

    # Simulate execution if requested (Operator behavior)
    if args.execute:
        simulate_execute(result, fail=args.fail)

    # Print results
    print_cosmic39(result)

    # Save if requested
    if args.save or args.out:
        if args.out:
            out_path = Path(args.out)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = meta.get("name", args.scenario).replace(" ", "_")
            out_path = Path("runs") / f"{ts}_{name}.json"

        save_json(result, out_path)
        print(f"💾 Saved to: {out_path}")


def cmd_audit(args: argparse.Namespace) -> None:
    """Execute audit command - diversity enforcement for recommendations."""
    # Load recommendations from JSON
    rec_path = Path(args.recommendations)
    if not rec_path.exists():
        print(f"Error: Recommendations file not found: {rec_path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        data = json.loads(rec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON recommendations payload: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    if not isinstance(data, dict):
        print("Error: Recommendations payload must be a JSON object", file=sys.stderr)
        raise SystemExit(1)

    def _parse_rec_list(items: Any, *, field_name: str) -> list[Rec]:
        if not isinstance(items, list):
            print(f"Error: '{field_name}' must be a list", file=sys.stderr)
            raise SystemExit(1)

        parsed: list[Rec] = []
        for i, raw in enumerate(items):
            if not isinstance(raw, dict):
                print(f"Error: {field_name}[{i}] must be an object", file=sys.stderr)
                raise SystemExit(1)
            try:
                rec = Rec.from_dict(raw)
            except (TypeError, ValueError) as e:
                print(f"Error: invalid {field_name}[{i}] payload: {e}", file=sys.stderr)
                raise SystemExit(1) from None
            if rec.price < 0:
                print(
                    f"Error: invalid {field_name}[{i}] payload: price must be >= 0, got {rec.price}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            parsed.append(rec)
        return parsed

    # Parse original and counterfactuals
    original_recs = _parse_rec_list(data.get("recommendations", []), field_name="recommendations")
    counterfactual_recs = _parse_rec_list(data.get("counterfactuals", []), field_name="counterfactuals")

    if not original_recs:
        print("Error: No recommendations found in input JSON", file=sys.stderr)
        raise SystemExit(1)

    # Run diversity enforcement
    result = diversify_with_mmr(
        original=original_recs,
        counterfactuals=counterfactual_recs,
        k=args.k,
        lam=0.65,  # Default utility/diversity balance
        min_merchants=args.min_merchants,
        min_price_buckets=args.min_price_buckets,
    )

    # Print report
    print("=" * 80)
    print("[Echo Execution Gate - Audit → Diversify → Boundary]")
    print("=" * 80)

    # Commercial Bias Analysis
    print("\nCommercial Bias Analysis:")
    bias_orig = result["commercial_bias_original"]
    bias_final = result["commercial_bias_final"]
    print(f"  Original bias score: {bias_orig['overall_bias_score']:.2%}")
    print(f"    - Affiliate risk: {bias_orig['affiliate_risk']:.2%}")
    print(f"    - Merchant concentration: {bias_orig['merchant_concentration']:.2%}")
    print(f"    - Price concentration: {bias_orig['price_concentration']:.2%}")
    print(f"  Final bias score: {bias_final['overall_bias_score']:.2%}")
    print(
        f"  Bias improvement: {bias_orig['overall_bias_score'] - bias_final['overall_bias_score']:.2%}"
    )

    # Diversity Reports
    print("\nDiversity Analysis:")
    orig_div = result["diversity_report_original"]
    final_div = result["diversity_report_final"]
    print(f"  Original: {orig_div['merchants']} merchants, {orig_div['price_buckets']} price tiers")
    print(f"  Final: {final_div['merchants']} merchants, {final_div['price_buckets']} price tiers")
    print(
        f"  Merchant concentration: {orig_div['merchant_concentration']:.2%} → {final_div['merchant_concentration']:.2%}"
    )

    # Responsibility Boundary (Execution Gate)
    print("\nResponsibility Boundary (Execution Gate):")
    boundary = result["responsibility_boundary"]
    print(f"  AI recommends: {'YES' if boundary.get('ai_recommends') else 'NO'}")
    print(f"  Execution allowed: {'YES' if boundary['execution_allowed'] else 'NO'}")
    print(f"  Requires human confirm: {'YES' if boundary['requires_human_confirm'] else 'NO'}")
    print(f"  Liability mode: {boundary.get('liability_mode', 'audit-only')}")
    if boundary.get("reasons"):
        print(f"  Reasons: {', '.join(boundary['reasons'])}")

    print(f"\nMMR Lambda: {result['mmr_lambda']:.2f}")
    print(f"Diversity enforced: {'YES' if result['diversity_enforced'] else 'NO'}")

    print("\nFinal Recommendations (Diversified):")
    for i, rec in enumerate(result["final_set"], 1):
        print(
            f"  {i}. {rec['title']} ({rec['merchant']}, ¥{rec['price']:.0f}) "
            f"[utility={rec['utility']:.2f}, bias={rec['bias_risk']:.2f}]"
        )

    # Save if requested
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Saved to: {out_path}")

    print("=" * 80)


def cmd_badge(args: argparse.Namespace) -> None:
    """Execute badge command - generate Echo Mark from audit result."""
    # Load audit result
    audit_path = Path(args.input)
    if not audit_path.exists():
        print(f"Error: Audit file not found: {audit_path}", file=sys.stderr)
        raise SystemExit(1)

    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    # Determine signature mode
    sig_mode = getattr(args, "sig_mode", "hmac")  # Default to HMAC for backward compatibility
    key_id = getattr(args, "key_id", "default")

    # Generate Echo Mark based on signature mode
    if sig_mode == "ed25519" and ED25519_AVAILABLE:
        # Ed25519-only mode
        try:
            # Try loading from file first
            if hasattr(args, "keys_dir") and args.keys_dir:
                keypair = load_ed25519_keypair(key_id, args.keys_dir)
                private_key = keypair["private_key"]
            else:
                # Fall back to environment variable
                _pk = load_ed25519_private_key_from_env()
                if not _pk:
                    print("Error: ECHO_MARK_PRIVATE_KEY not set", file=sys.stderr)
                    print("Set environment variable or use --keys-dir", file=sys.stderr)
                    raise SystemExit(1)
                private_key = _pk

            badge = make_echo_mark_ed25519(audit, private_key, key_id, run_id=args.run_id)
            print("Ed25519 signature mode")
        except (FileNotFoundError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            raise SystemExit(1) from None

    elif sig_mode == "dual" and ED25519_AVAILABLE:
        # Dual signature mode (HMAC + Ed25519)
        try:
            # Get HMAC secret
            secret = get_secret_from_env()

            # Get Ed25519 private key
            if hasattr(args, "keys_dir") and args.keys_dir:
                keypair = load_ed25519_keypair(key_id, args.keys_dir)
                private_key = keypair["private_key"]
            else:
                _pk = load_ed25519_private_key_from_env()
                if not _pk:
                    print("Error: ECHO_MARK_PRIVATE_KEY not set", file=sys.stderr)
                    raise SystemExit(1)
                private_key = _pk

            badge = make_echo_mark_dual(audit, secret, private_key, key_id, run_id=args.run_id)
            print("Dual signature mode (HMAC + Ed25519)")
        except (FileNotFoundError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            raise SystemExit(1) from None

    else:
        # HMAC-only mode (default, backward compatible)
        try:
            secret = get_secret_from_env()
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("Set ECHO_MARK_SECRET environment variable (min 16 chars)", file=sys.stderr)
            raise SystemExit(1) from None

        badge = make_echo_mark(audit, secret=secret, run_id=args.run_id)
        print("HMAC signature mode (legacy)")

    # Print summary
    print("=" * 80)
    print("[Echo Mark Generated]")
    print("=" * 80)
    print(f"Label: {badge['label']}")
    print(f"Badge text: {badge['badge_text']}")
    print(f"Schema version: {badge.get('schema_version', 'echo_mark_v2')}")
    print(f"Verification method: {badge.get('verification_method', 'HMAC-SHA256')}")
    print("\nBias signals:")
    short = badge["short"]
    print(f"  Original: {short['bias_original']:.2%}")
    print(f"  Final: {short['bias_final']:.2%}")
    print(f"  Improvement: {short['bias_improvement']:.2%}")
    if short["reasons"]:
        print(f"  Reasons: {', '.join(short['reasons'])}")
    print(f"\nSignature: {badge['signature'][:32]}...")
    if "public_key" in badge:
        print(f"Public key: {badge['public_key'][:32]}...")
    print("=" * 80)

    # Save badge
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(badge, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Saved to: {out_path}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Execute verify command - verify Echo Mark signature."""
    # Load badge
    badge_path = Path(args.input)
    if not badge_path.exists():
        print(f"Error: Badge file not found: {badge_path}", file=sys.stderr)
        raise SystemExit(1)

    badge = json.loads(badge_path.read_text(encoding="utf-8"))

    # Detect signature type
    schema_version = badge.get("schema_version", "echo_mark_v2")
    verification_method = badge.get("verification_method", "HMAC-SHA256")

    print("=" * 80)
    print("[Echo Mark Verification]")
    print("=" * 80)
    print(f"Label: {badge['label']}")
    print(f"Schema version: {schema_version}")
    print(f"Verification method: {verification_method}")
    print()

    # Verify based on schema version
    if schema_version == "echo_mark_v3" and "public_key" in badge:
        # Ed25519 or dual signature
        if ED25519_AVAILABLE:
            # Try dual verification (Ed25519 preferred, HMAC fallback)
            try:
                secret = get_secret_from_env()
            except RuntimeError:
                secret = None  # No HMAC secret available

            result = verify_echo_mark_dual(badge, hmac_secret=secret)

            # Print result
            print(f"Status: {result['status']}")
            if result.get("verification_method"):
                print(f"Verified with: {result['verification_method']}")
            print()

            # Print checks
            checks = result.get("checks", {})
            print("Verification checks:")
            print(f"  Hash integrity: {'✓' if checks.get('hash_integrity') else '✗'}")
            print(f"  Signature valid: {'✓' if checks.get('signature_valid') else '✗'}")
            print(f"  Schema valid: {'✓' if checks.get('schema_valid') else '✗'}")
            print(f"  Timestamp valid: {'✓' if checks.get('timestamp_valid') else '⚠️'}")

            # Print warnings/notes
            if result.get("timestamp_warning"):
                print(f"\n⚠️  Timestamp warning: {result['timestamp_warning']}")
            if result.get("note"):
                print(f"\nNote: {result['note']}")

            print("=" * 80)

            if result["status"] != "VERIFIED":
                print(f"\n❌ Verification failed: {result.get('reason')}")
                raise SystemExit(2)

            print("\n✅ VERIFIED")

        else:
            # PyNaCl not available, try HMAC fallback
            print("⚠️  PyNaCl not installed, Ed25519 verification not available")
            print("Falling back to HMAC verification...")
            print()

            if "signature_hmac" not in badge:
                print("❌ No HMAC signature found in badge")
                print("Install PyNaCl for Ed25519 verification: pip install pynacl")
                raise SystemExit(2)

            try:
                secret = get_secret_from_env()
            except RuntimeError as e:
                print(f"Error: {e}")
                print("Set ECHO_MARK_SECRET environment variable")
                raise SystemExit(2) from None

            valid = verify_mark(
                payload=badge["payload"],
                payload_hash=badge["payload_hash"],
                signature=badge.get("signature_hmac", badge["signature"]),
                secret=secret,
            )

            print(f"Signature: {'VALID' if valid else 'INVALID'}")
            print("=" * 80)

            if not valid:
                raise SystemExit(2)

    else:
        # Legacy HMAC verification (v1/v2)
        try:
            secret = get_secret_from_env()
        except RuntimeError as e:
            print(f"Error: {e}")
            print("Set ECHO_MARK_SECRET environment variable")
            raise SystemExit(2) from None

        valid = verify_mark(
            payload=badge["payload"],
            payload_hash=badge["payload_hash"],
            signature=badge["signature"],
            secret=secret,
        )

        print(f"Signature: {'VALID ✓' if valid else 'INVALID ✗'}")
        print("=" * 80)

        if not valid:
            raise SystemExit(2)


def cmd_audio_gate(args: argparse.Namespace) -> None:
    """Execute audio-gate command - apply execution gate for voice actions."""
    # Load audit result
    audit_path = Path(args.inp)
    if not audit_path.exists():
        print(f"Error: Audit file not found: {audit_path}", file=sys.stderr)
        raise SystemExit(1)

    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    # Parse metadata
    try:
        meta = json.loads(args.meta)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --meta: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    # Apply audio gate
    audit_with_gate = gate_audio(
        audit=audit,
        intent=args.intent,
        meta=meta,
        transcript_tail=args.transcript,
        simulate_user_ok=args.simulate_ok,
    )

    # Save result
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(audit_with_gate, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    rb = audit_with_gate["responsibility_boundary"]
    print("=" * 80)
    print("[Audio Execution Gate]")
    print("=" * 80)
    print(f"Channel: {rb['channel']}")
    print(f"Intent: {args.intent}")
    print(f"Risk: {rb['risk']}")
    print(f"Required action: {rb['required_action']}")
    print(f"Execution allowed: {'YES' if rb['execution_allowed'] else 'NO'}")
    print(f"Requires confirmation: {'YES' if rb['requires_human_confirm'] else 'NO'}")
    if rb.get("rth_snapshot"):
        print(f"RTH snapshot: {rb['rth_snapshot']['hash_hex'][:16]}...")
    print("=" * 80)
    print(f"💾 Saved to: {out_path}")


def cmd_voice(args: argparse.Namespace) -> None:
    """Execute voice command - integrated audio flow with handshake + Echo Mark."""
    audit_path = Path(args.inp)
    if not audit_path.exists():
        print(f"Error: Audit file not found: {audit_path}", file=sys.stderr)
        raise SystemExit(1)

    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    try:
        meta = json.loads(args.meta)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --meta: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    try:
        secret = get_secret_from_env()
        if args.keys_dir:
            keypair = load_ed25519_keypair(args.key_id, args.keys_dir)
            private_key = keypair["private_key"]
        else:
            _pk = load_ed25519_private_key_from_env()
            if not _pk:
                raise RuntimeError("ECHO_MARK_PRIVATE_KEY not set")
            private_key = _pk
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    payload = VoiceFlowInput(
        intent=args.intent,
        transcript=args.transcript,
        metadata=meta,
        simulate_ok=args.simulate_ok,
        run_id=args.run_id,
        key_id=args.key_id,
        device_secret_hex=args.device_secret,
    )

    try:
        result = run_voice_flow(
            audit=audit,
            payload=payload,
            hmac_secret=secret,
            ed25519_private_key=private_key,
            require_execution_allowed=args.require_execution_allowed,
        )
    except VoiceFlowError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(3) from None

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 80)
    print("[Voice Flow: Candidate Set + Evidence + Responsibility Boundary]")
    print("=" * 80)
    boundary = result.get("responsibility_boundary", {})
    print(f"Candidate count: {len(result.get('candidate_set', []))}")
    print(f"Evidence count: {len(result.get('evidence', []))}")
    print(f"Execution allowed: {'YES' if boundary.get('execution_allowed') else 'NO'}")
    print(f"Required action: {boundary.get('required_action', 'app_confirm')}")
    print(f"Echo Mark: {result.get('echo_mark', {}).get('label', 'Echo Verified')}")
    print("=" * 80)
    print(f"💾 Saved to: {out_path}")


DEVICE_INPUT_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Project Echo Device Boundary CLI Input",
    "type": "object",
    "required": ["device", "intent"],
    "properties": {
        "device": {"type": "string", "enum": list_devices()},
        "intent": {"type": "string", "minLength": 1},
        "meta": {"type": "object"},
        "bias_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "replay_detected": {"type": "boolean", "default": False},
        "tamper_detected": {"type": "boolean", "default": False},
    },
}

DEVICE_OUTPUT_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Project Echo Device Boundary CLI Output",
    "type": "object",
    "required": ["device", "responsibility_boundary"],
    "properties": {
        "device": {"type": "string"},
        "device_description": {"type": "string"},
        "responsibility_boundary": {
            "type": "object",
            "required": ["channel", "device", "risk", "required_action", "execution_allowed", "requires_human_confirm", "reasons"],
        },
    },
}


def cmd_device(args: argparse.Namespace) -> None:
    """Execute device command — evaluate responsibility boundary for the given device."""
    if args.list_devices:
        print("Registered devices:")
        for dev in list_devices():
            cfg = DEVICE_CONFIGS[dev]
            print(f"  {dev}: {cfg.description} (bias_threshold={cfg.high_bias_block_threshold})")
        return

    if args.show_schema:
        print(json.dumps({"input_schema": DEVICE_INPUT_SCHEMA, "output_schema": DEVICE_OUTPUT_SCHEMA}, ensure_ascii=False, indent=2))
        return

    try:
        meta = json.loads(args.meta)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --meta: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    device: DeviceType = args.device
    decision = decide_for_device(
        device,
        args.intent,
        meta=meta or None,
        bias_score=args.bias_score,
        replay_detected=args.replay_detected,
        tamper_detected=args.tamper_detected,
    )

    result: dict[str, Any] = {
        "device": device,
        "device_description": get_device_description(device),
        "responsibility_boundary": decision.to_responsibility_boundary(),
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    rb = result["responsibility_boundary"]
    print("=" * 80)
    print(f"[Device Boundary: {device}]")
    print("=" * 80)
    print(f"Device      : {device} — {result['device_description']}")
    print(f"Intent      : {args.intent}")
    print(f"Risk        : {rb['risk']}")
    print(f"Action      : {rb['required_action']}")
    exec_label = "YES" if rb["execution_allowed"] else "NO (BLOCKED)"
    print(f"Execution   : {exec_label}")
    print(f"Reasons     : {', '.join(rb['reasons'])}")
    if args.out:
        print(f"💾 Saved to : {args.out}")
    print("=" * 80)
    print("責任境界: デバイス種別に応じた確認手段の提示まで。最終承認は人間責任。")

    if not rb["execution_allowed"] and args.require_execution_allowed:
        raise SystemExit(3)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="po-cosmic", description="Cosmic Ethics 39 - Ethical Evaluation with 39 Philosophers"
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # cosmic-39 command
    c39 = subparsers.add_parser("cosmic-39", help="Evaluate cosmic-scale ethical scenarios")
    c39.add_argument(
        "--scenario",
        default="mars",
        help="Scenario to evaluate: agi, mars, digital, seti (default: mars)",
    )
    c39.add_argument(
        "--preset",
        default="cosmic13",
        help="Philosopher preset: cosmic13, east_asia, kantian, existentialist, classical, all (default: cosmic13)",
    )
    c39.add_argument("--save", action="store_true", help="Save result to runs/ directory")
    c39.add_argument("--out", default=None, help="Explicit output JSON path")
    c39.add_argument(
        "--confirm", action="store_true", help="Require human Yes/No confirmation when needed"
    )
    c39.add_argument(
        "--execute",
        action="store_true",
        help="Simulate execution with state transitions (Operator mode)",
    )
    c39.add_argument(
        "--fail", action="store_true", help="Simulate failure and recovery (requires --execute)"
    )

    # audit command - diversity enforcement
    audit = subparsers.add_parser(
        "audit", help="Audit recommendations for commercial bias and enforce diversity"
    )
    audit.add_argument("recommendations", help="Path to recommendations JSON file")
    audit.add_argument(
        "-k", "--k", type=int, default=5, help="Number of recommendations to select (default: 5)"
    )
    audit.add_argument(
        "--min-merchants",
        type=int,
        default=2,
        help="Minimum number of unique merchants (default: 2)",
    )
    audit.add_argument(
        "--min-price-buckets",
        type=int,
        default=2,
        help="Minimum number of price buckets (default: 2)",
    )
    audit.add_argument("--out", default=None, help="Output JSON path for results")

    # badge command - generate Echo Mark
    badge = subparsers.add_parser("badge", help="Generate Echo Mark from audit result")
    badge.add_argument("input", help="Path to audit JSON file")
    badge.add_argument("output", help="Path to output badge JSON file")
    badge.add_argument("--run-id", dest="run_id", default=None, help="Optional run identifier")
    badge.add_argument(
        "--sig-mode",
        dest="sig_mode",
        choices=["hmac", "ed25519", "dual"],
        default="hmac",
        help="Signature mode: hmac (legacy), ed25519 (v3), dual (HMAC+Ed25519, recommended)",
    )
    badge.add_argument(
        "--key-id",
        dest="key_id",
        default="default",
        help="Key identifier for Ed25519 (default: 'default')",
    )
    badge.add_argument(
        "--keys-dir",
        dest="keys_dir",
        default=None,
        help="Directory containing Ed25519 keypair files (default: .keys/)",
    )

    # verify command - verify Echo Mark
    verify = subparsers.add_parser("verify", help="Verify Echo Mark signature")
    verify.add_argument("input", help="Path to badge JSON file")

    # device command - multi-device responsibility boundary
    device_cmd = subparsers.add_parser(
        "device",
        help="Evaluate responsibility boundary for a registered device type",
        description=(
            "Returns responsibility_boundary for the given device + intent combination. "
            "All devices enforce the same bias-block and high-risk-confirm invariants."
        ),
    )
    device_cmd.add_argument(
        "--device",
        choices=list_devices(),
        default="earworn",
        help=f"Device type (default: earworn). Choices: {', '.join(list_devices())}",
    )
    device_cmd.add_argument("--intent", required=True, help="Intent: booking/payment/search/...")
    device_cmd.add_argument("--meta", default="{}", help='Metadata JSON (e.g., {"amount": 10000})')
    device_cmd.add_argument(
        "--bias-score",
        dest="bias_score",
        type=float,
        default=0.0,
        help="Commercial bias score [0.0, 1.0] (default: 0.0)",
    )
    device_cmd.add_argument(
        "--replay-detected",
        dest="replay_detected",
        action="store_true",
        help="Signal that RTH detected a replay attack (forces block)",
    )
    device_cmd.add_argument(
        "--tamper-detected",
        dest="tamper_detected",
        action="store_true",
        help="Signal that Echo Mark tamper check failed (forces block)",
    )
    device_cmd.add_argument("--out", default=None, help="Optional output JSON file path")
    device_cmd.add_argument(
        "--require-execution-allowed",
        dest="require_execution_allowed",
        action="store_true",
        help="Exit with code 3 when execution is blocked",
    )
    device_cmd.add_argument(
        "--list-devices",
        dest="list_devices",
        action="store_true",
        help="List all registered device types and exit",
    )
    device_cmd.add_argument(
        "--show-schema",
        dest="show_schema",
        action="store_true",
        help="Print device boundary input/output JSON schemas and exit",
    )

    # audio-gate command - voice-initiated execution gate
    audio_gate = subparsers.add_parser(
        "audio-gate", help="Apply execution gate for voice-initiated actions"
    )
    audio_gate.add_argument("--intent", required=True, help="Intent: booking/payment/search/...")
    audio_gate.add_argument("--transcript", required=True, help="Last 5-second transcript text")
    audio_gate.add_argument("--meta", default="{}", help='Metadata JSON (e.g., {"amount": 10000})')
    audio_gate.add_argument(
        "--simulate-ok", action="store_true", help="Simulate user confirmation (for testing)"
    )
    audio_gate.add_argument("--in", dest="inp", required=True, help="Input audit JSON file")
    audio_gate.add_argument("--out", dest="out", required=True, help="Output audit JSON file")

    # voice command - integrated voice flow
    voice = subparsers.add_parser(
        "voice",
        help="Run integrated voice flow (ear handshake + audio gate + Echo Mark)",
        description=(
            "Voice flow returns candidate_set + evidence + responsibility_boundary only. "
            + VOICE_SCHEMA_HELP
        ),
    )
    voice.add_argument("--intent", required=True, help="Intent: booking/payment/search/...")
    voice.add_argument("--transcript", required=True, help="Last 5-second transcript text")
    voice.add_argument("--meta", default="{}", help='Metadata JSON (e.g., {"amount": 10000})')
    voice.add_argument(
        "--simulate-ok", action="store_true", help="Simulate user confirmation (for testing)"
    )
    voice.add_argument("--in", dest="inp", required=True, help="Input audit JSON file")
    voice.add_argument("--out", dest="out", required=True, help="Output voice JSON file")
    voice.add_argument("--run-id", dest="run_id", default=None, help="Optional run identifier")
    voice.add_argument(
        "--key-id",
        dest="key_id",
        default="default",
        help="Key identifier for Ed25519 (default: 'default')",
    )
    voice.add_argument(
        "--keys-dir",
        dest="keys_dir",
        default=None,
        help="Directory containing Ed25519 keypair files (default: .keys/)",
    )
    voice.add_argument(
        "--device-secret",
        default=None,
        help="Optional deterministic 64-hex device secret for test replayability",
    )
    voice.add_argument(
        "--require-execution-allowed",
        action="store_true",
        help="Fail with exit code 3 when responsibility boundary blocks execution",
    )
    voice.add_argument(
        "--show-schema",
        action="store_true",
        help="Print fixed JSON schemas for voice input/output and exit",
    )

    args = parser.parse_args()

    if args.cmd == "cosmic-39":
        cmd_cosmic39(args)
    elif args.cmd == "device":
        cmd_device(args)
    elif args.cmd == "audit":
        cmd_audit(args)
    elif args.cmd == "badge":
        cmd_badge(args)
    elif args.cmd == "verify":
        cmd_verify(args)
    elif args.cmd == "audio-gate":
        cmd_audio_gate(args)
    elif args.cmd == "voice":
        if args.show_schema:
            print(json.dumps({"input_schema": VOICE_INPUT_SCHEMA, "output_schema": VOICE_OUTPUT_SCHEMA}, ensure_ascii=False, indent=2))
            return

        print("Voice stack inventory:")
        for item in inventory_voice_stack():
            print(f"- {item['component']}: {item['module']} ({item['role']})")
        cmd_voice(args)


if __name__ == "__main__":
    main()
