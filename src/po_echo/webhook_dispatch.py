"""Webhook dispatch adapter for alert notifications.

Why: alert_notify.py generates a structured notification envelope, but
operators need actual delivery to external channels (Slack, PagerDuty).
This module converts the envelope into channel-specific payloads and
sends them via HTTP without adding new runtime dependencies (stdlib only).

Design principles:
- Webhook URLs/keys are never hardcoded — they are injected at runtime via
  environment variables or explicit arguments (responsibility boundary: secret
  management is the caller's responsibility).
- dry_run=True skips all HTTP calls and records what would have been sent.
- Each dispatch attempt is returned as a DispatchResult so callers can audit
  successes and failures without crashing.
- Slack uses the Incoming Webhooks Block Kit format.
- PagerDuty uses the Events API v2 (enqueue_event endpoint).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

# PagerDuty Events API v2 endpoint (public, not configurable).
_PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"

# HTTP timeout for webhook calls (seconds).
_HTTP_TIMEOUT = 10

# Retry delays (seconds) applied between attempts on network-level failures.
# Only network exceptions (OSError, URLError, timeout) trigger retries;
# HTTP-level responses (4xx, 5xx) are returned immediately.
# Why: network-level failures indicate the request never reached the server,
# so retrying is safe. HTTP responses mean the server received the request
# (PagerDuty dedup_key handles idempotency there); retrying would risk
# duplicate delivery for channels without server-side dedup (e.g. Slack).
_RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)

# Severity → PagerDuty severity mapping.
# Why: PagerDuty uses its own severity taxonomy; we map from internal labels.
_PD_SEVERITY_MAP: dict[str, str] = {
    "SEV-1": "critical",
    "SEV-2": "error",
    "SEV-3": "warning",
    "NONE": "info",
}

# Severity → Slack emoji for quick visual scanning.
_SLACK_EMOJI_MAP: dict[str, str] = {
    "SEV-1": ":red_circle:",
    "SEV-2": ":large_orange_circle:",
    "SEV-3": ":large_yellow_circle:",
    "NONE": ":white_check_mark:",
}


@dataclass(frozen=True)
class DispatchResult:
    """Outcome of a single webhook delivery attempt.

    Attributes:
        target: Human-readable target name (e.g. "slack", "pagerduty").
        success: True when the HTTP call returned 2xx or dry_run=True.
        status_code: HTTP response code (None for dry-run or network failure).
        error: Error message on failure (None on success).
        dry_run: True when no actual HTTP call was made.
        payload_preview: First 200 chars of the serialised payload for auditing.
    """

    target: str
    success: bool
    status_code: int | None = None
    error: str | None = None
    dry_run: bool = False
    payload_preview: str = ""


@dataclass
class WebhookConfig:
    """Runtime configuration for a single webhook target.

    Attributes:
        target: Identifier used in DispatchResult (e.g. "slack").
        url: Full webhook URL (for Slack) or routing key (for PagerDuty).
        kind: One of "slack" or "pagerduty".
    """

    target: str
    url: str
    kind: str  # "slack" | "pagerduty"


def format_slack_payload(notification: dict[str, Any]) -> dict[str, Any]:
    """Convert a notification envelope to a Slack Block Kit payload.

    Why: Block Kit gives structured, scannable alerts compared to plain text.
    Responsibility boundary: payload formatting only — delivery is separate.
    """
    severity = notification.get("severity", "NONE")
    has_alert = bool(notification.get("has_alert"))
    emoji = _SLACK_EMOJI_MAP.get(severity, ":white_check_mark:")
    title = f"{emoji} Project Echo Alert [{severity}]" if has_alert else f"{emoji} Project Echo — No Alert"

    flags = notification.get("flags", {})
    evidence = notification.get("evidence", {})
    generated_at = notification.get("generated_at_utc", "")

    fields_text_parts = []
    if flags.get("has_reported_failures"):
        fields_text_parts.append("• `has_reported_failures` = *true*")
    if flags.get("has_malformed_artifact"):
        fields_text_parts.append("• `has_malformed_artifact` = *true*")
    if not fields_text_parts:
        fields_text_parts.append("• All KPI flags nominal")

    evidence_parts = []
    if evidence.get("latest_week_id"):
        evidence_parts.append(f"Week: `{evidence['latest_week_id']}`")
    if evidence.get("latest_month_id"):
        evidence_parts.append(f"Month: `{evidence['latest_month_id']}`")
    if evidence.get("kpi_delta_ref"):
        evidence_parts.append(f"KPI delta: `{evidence['kpi_delta_ref']}`")
    if evidence.get("monthly_summary_ref"):
        evidence_parts.append(f"Monthly summary: `{evidence['monthly_summary_ref']}`")

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title, "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(fields_text_parts)},
        },
    ]

    if evidence_parts:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Evidence links*\n" + "\n".join(f"• {e}" for e in evidence_parts)},
            }
        )

    rb = notification.get("responsibility_boundary", {})
    if rb.get("human_scope"):
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f":information_source: Human scope: {rb['human_scope']}"},
                ],
            }
        )

    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Generated at: {generated_at}"}],
        }
    )

    return {"blocks": blocks}


def format_pagerduty_payload(
    notification: dict[str, Any],
    routing_key: str,
    dedup_key: str | None = None,
) -> dict[str, Any]:
    """Convert a notification envelope to a PagerDuty Events API v2 payload.

    Why: PagerDuty's structured event fields enable automated escalation
    routing without operator intervention.
    Responsibility boundary: payload formatting and delivery only — routing
    key management and escalation policy are operator responsibility.

    Args:
        notification: Output of ``build_alert_notification``.
        routing_key: PagerDuty service integration key (32-char hex).
        dedup_key: Optional deduplication key (default: derived from generated_at).
    """
    severity = notification.get("severity", "NONE")
    pd_severity = _PD_SEVERITY_MAP.get(severity, "info")
    has_alert = bool(notification.get("has_alert"))
    generated_at = notification.get("generated_at_utc", "")

    summary = (
        f"Project Echo [{severity}]: KPI alert detected"
        if has_alert
        else "Project Echo [NONE]: All KPI flags nominal"
    )

    flags = notification.get("flags", {})
    evidence = notification.get("evidence", {})

    custom_details: dict[str, Any] = {
        "has_reported_failures": flags.get("has_reported_failures", False),
        "has_malformed_artifact": flags.get("has_malformed_artifact", False),
        "latest_week_id": evidence.get("latest_week_id"),
        "latest_month_id": evidence.get("latest_month_id"),
        "generated_at_utc": generated_at,
    }

    if dedup_key is None:
        # Why: deterministic dedup_key prevents double-paging for the same
        # alert window when the script is retried.
        dedup_key = f"project-echo-alert-{generated_at}"

    return {
        "routing_key": routing_key,
        "event_action": "trigger" if has_alert else "resolve",
        "dedup_key": dedup_key,
        "payload": {
            "summary": summary,
            "severity": pd_severity,
            "source": "project-echo-ops",
            "custom_details": custom_details,
        },
    }


def _request_id(body: bytes) -> str:
    """Return first 16 hex chars of SHA-256(body) as a content-addressed request ID.

    Why: sending a stable X-Request-Id derived from payload content lets
    operators correlate log entries across retries without generating a new
    random ID per attempt. This also aids Slack-side debugging even though
    Slack does not natively deduplicate on this header.
    """
    return hashlib.sha256(body).hexdigest()[:16]


def _http_post(url: str, body: bytes, timeout: int = _HTTP_TIMEOUT) -> tuple[int, str]:
    """Send an HTTP POST with JSON body; return (status_code, response_text).

    Why: using stdlib urllib avoids adding runtime dependencies while still
    supporting HTTPS. Callers handle exceptions.
    """
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Request-Id": _request_id(body),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def _dispatch_single(
    target: str,
    url: str,
    payload: dict[str, Any],
    *,
    dry_run: bool,
    retry_delays: tuple[float, ...] = _RETRY_DELAYS,
) -> DispatchResult:
    """Attempt a webhook delivery with retry on network-level failures.

    Retry policy:
    - Only network exceptions (OSError, urllib.error.URLError, timeout) are
      retried. HTTP responses (including 5xx) are returned immediately.
    - Why: HTTP responses mean the server received the request. PagerDuty
      provides idempotency via dedup_key; Slack has no server-side dedup, so
      retrying an acknowledged HTTP response risks duplicate delivery.
    - retry_delays controls inter-attempt sleep durations (seconds). Pass
      an empty tuple to disable retries (e.g. in unit tests).
    """
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    preview = body.decode("utf-8")[:200]

    if dry_run:
        return DispatchResult(
            target=target,
            success=True,
            status_code=None,
            error=None,
            dry_run=True,
            payload_preview=preview,
        )

    last_network_error: str | None = None

    for attempt, delay in enumerate((0.0, *retry_delays)):
        if attempt > 0:
            time.sleep(delay)

        try:
            status_code, _ = _http_post(url, body)
            success = 200 <= status_code < 300
            return DispatchResult(
                target=target,
                success=success,
                status_code=status_code,
                error=None if success else f"HTTP {status_code}",
                dry_run=False,
                payload_preview=preview,
            )
        except urllib.error.HTTPError as exc:
            # HTTPError is an HTTP-level response — return immediately, no retry.
            return DispatchResult(
                target=target,
                success=False,
                status_code=exc.code,
                error=f"HTTPError {exc.code}: {exc.reason}",
                dry_run=False,
                payload_preview=preview,
            )
        except Exception as exc:  # noqa: BLE001
            # Network-level failure — retry if attempts remain.
            last_network_error = str(exc)
            _ = attempt  # suppress unused-variable warning

    return DispatchResult(
        target=target,
        success=False,
        status_code=None,
        error=last_network_error,
        dry_run=False,
        payload_preview=preview,
    )


def dispatch_webhooks(
    notification: dict[str, Any],
    configs: list[WebhookConfig],
    *,
    dry_run: bool = False,
    pagerduty_dedup_key: str | None = None,
    retry_delays: tuple[float, ...] = _RETRY_DELAYS,
) -> list[DispatchResult]:
    """Dispatch a notification envelope to all configured webhook targets.

    Args:
        notification: Output of ``build_alert_notification``.
        configs: List of ``WebhookConfig`` describing each target.
        dry_run: When True, skip HTTP calls and return simulated successes.
        pagerduty_dedup_key: Override dedup_key for PagerDuty events.
        retry_delays: Sleep durations (seconds) between retry attempts on
            network failures. Defaults to ``_RETRY_DELAYS``. Pass an empty
            tuple to disable retries (e.g. in tests).

    Returns:
        List of ``DispatchResult``, one per config entry.

    Responsibility boundary:
        This function formats and sends payloads only. Routing key management,
        escalation policies, and on-call roster decisions are operator
        responsibility.

    Idempotency notes:
        PagerDuty: idempotency is guaranteed via ``dedup_key`` in the payload.
        Slack: no server-side dedup; ``X-Request-Id`` (SHA-256 of body) is sent
        for log correlation only. Duplicate delivery is possible if a Slack
        request was acknowledged (2xx) and a caller retries at a higher level.
    """
    results: list[DispatchResult] = []

    for cfg in configs:
        if cfg.kind == "slack":
            payload = format_slack_payload(notification)
            result = _dispatch_single(
                cfg.target, cfg.url, payload, dry_run=dry_run, retry_delays=retry_delays
            )
        elif cfg.kind == "pagerduty":
            payload = format_pagerduty_payload(
                notification,
                routing_key=cfg.url,
                dedup_key=pagerduty_dedup_key,
            )
            result = _dispatch_single(
                cfg.target,
                _PAGERDUTY_EVENTS_URL,
                payload,
                dry_run=dry_run,
                retry_delays=retry_delays,
            )
        else:
            result = DispatchResult(
                target=cfg.target,
                success=False,
                error=f"unknown webhook kind: {cfg.kind!r}",
                dry_run=dry_run,
            )
        results.append(result)

    return results


def configs_from_env(
    slack_url_env: str = "ECHO_SLACK_WEBHOOK_URL",
    pagerduty_key_env: str = "ECHO_PAGERDUTY_ROUTING_KEY",
) -> list[WebhookConfig]:
    """Build WebhookConfig list from environment variables.

    Why: secrets must never be stored in code or config files. Environment
    variable injection is the minimum-risk approach for CI/CD pipelines.

    Args:
        slack_url_env: Name of the env var holding the Slack webhook URL.
        pagerduty_key_env: Name of the env var holding the PagerDuty routing key.

    Returns:
        List of configured targets (may be empty if no env vars are set).
    """
    configs: list[WebhookConfig] = []

    slack_url = os.environ.get(slack_url_env, "").strip()
    if slack_url:
        configs.append(WebhookConfig(target="slack", url=slack_url, kind="slack"))

    pd_key = os.environ.get(pagerduty_key_env, "").strip()
    if pd_key:
        configs.append(WebhookConfig(target="pagerduty", url=pd_key, kind="pagerduty"))

    return configs
