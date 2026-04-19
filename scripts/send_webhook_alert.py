#!/usr/bin/env python3
"""Send alert notification to configured webhooks (Slack / PagerDuty).

Why: operators need a single CLI to route the existing alert notification
envelope to external channels without modifying internal tooling.

Webhook credentials are read from environment variables — never passed on
the command line — to avoid secret leakage in process lists or shell history.

Environment variables:
    ECHO_SLACK_WEBHOOK_URL       Slack Incoming Webhook URL
    ECHO_PAGERDUTY_ROUTING_KEY   PagerDuty Events API v2 routing key

Usage:
    # Normal dispatch (reads env vars automatically)
    python scripts/send_webhook_alert.py

    # Dry-run: log what would be sent without HTTP calls
    python scripts/send_webhook_alert.py --dry-run

    # Use a specific notification JSON
    python scripts/send_webhook_alert.py --notification-in reports/operations/p2_alert_notification.json

    # Use custom env var names
    python scripts/send_webhook_alert.py --slack-url-env MY_SLACK_URL --pagerduty-key-env MY_PD_KEY

    # Fail with exit code 1 when has_alert is True
    python scripts/send_webhook_alert.py --fail-on-alert

    # Machine-readable JSON output
    python scripts/send_webhook_alert.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from po_echo.webhook_dispatch import (
    DispatchResult,
    WebhookConfig,
    configs_from_env,
    dispatch_webhooks,
    evaluate_dispatch_slo,
    summarize_dispatch_results,
)

_DEFAULT_NOTIFICATION_PATH = _REPO_ROOT / "reports" / "operations" / "p2_alert_notification.json"


def _load_notification(path: Path) -> dict:
    if not path.exists():
        print(
            f"[ERROR] notification file not found: {path}\n"
            "Run 'python scripts/dispatch_alert_notification.py' first.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] failed to parse notification JSON: {exc}", file=sys.stderr)
        sys.exit(2)


def _summarise(results: list[DispatchResult], as_json: bool, has_alert: bool) -> None:
    metrics = summarize_dispatch_results(results)
    slo = evaluate_dispatch_slo(metrics)
    if as_json:
        print(
            json.dumps(
                {
                    "has_alert": has_alert,
                    "metrics": metrics,
                    "slo": slo,
                    "dispatched": [
                        {
                            "target": r.target,
                            "success": r.success,
                            "status_code": r.status_code,
                            "error": r.error,
                            "dry_run": r.dry_run,
                        }
                        for r in results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if not results:
        print("[INFO] No webhook targets configured. Set ECHO_SLACK_WEBHOOK_URL or ECHO_PAGERDUTY_ROUTING_KEY.")
        return

    print(
        "[METRICS] total={total} success={success} failure={failure} dry_run={dry_run} success_rate={success_rate:.2%}".format(
            **metrics
        )
    )
    print(f"[SLO] ok={slo['ok']} breaches={','.join(slo['breaches']) if slo['breaches'] else 'none'}")
    for r in results:
        tag = "[DRY-RUN]" if r.dry_run else ("[OK]" if r.success else "[FAIL]")
        msg = f"{tag} {r.target}"
        if r.status_code is not None:
            msg += f" (HTTP {r.status_code})"
        if r.error:
            msg += f" — {r.error}"
        print(msg)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispatch Project Echo alert notification to Slack / PagerDuty."
    )
    parser.add_argument(
        "--notification-in",
        metavar="PATH",
        default=None,
        help="Path to p2_alert_notification.json (default: reports/operations/p2_alert_notification.json).",
    )
    parser.add_argument(
        "--slack-url-env",
        metavar="ENV_VAR",
        default="ECHO_SLACK_WEBHOOK_URL",
        help="Name of env var holding Slack webhook URL (default: ECHO_SLACK_WEBHOOK_URL).",
    )
    parser.add_argument(
        "--pagerduty-key-env",
        metavar="ENV_VAR",
        default="ECHO_PAGERDUTY_ROUTING_KEY",
        help="Name of env var holding PagerDuty routing key (default: ECHO_PAGERDUTY_ROUTING_KEY).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be sent without making HTTP calls.",
    )
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit with code 1 when has_alert is True.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output.",
    )

    args = parser.parse_args()

    notification_path = Path(args.notification_in) if args.notification_in else _DEFAULT_NOTIFICATION_PATH
    notification = _load_notification(notification_path)

    configs: list[WebhookConfig] = configs_from_env(
        slack_url_env=args.slack_url_env,
        pagerduty_key_env=args.pagerduty_key_env,
    )

    results = dispatch_webhooks(notification, configs, dry_run=args.dry_run)
    has_alert = bool(notification.get("has_alert"))

    _summarise(results, as_json=args.json, has_alert=has_alert)

    # Responsibility boundary: this script delivers the payload and reports
    # results. Escalation decisions and on-call routing are operator responsibility.

    if args.fail_on_alert and has_alert:
        sys.exit(1)


if __name__ == "__main__":
    main()
