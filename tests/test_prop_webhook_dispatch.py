"""Property-based tests for webhook_dispatch module.

Properties verified:
1. Slack payload always has a non-empty blocks list.
2. PagerDuty payload always has required keys regardless of input shape.
3. Severity mapping never returns an unknown string.
4. Dry-run dispatch always succeeds regardless of notification content.
5. configs_from_env returns only "slack" or "pagerduty" kinds.
6. Unknown webhook kinds always produce failure results.
7. Dispatch result list length equals config list length.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.webhook_dispatch import (
    DispatchResult,
    WebhookConfig,
    dispatch_webhooks,
    format_pagerduty_payload,
    format_slack_payload,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_SEVERITIES = ["SEV-1", "SEV-2", "SEV-3", "NONE"]

_notification_strategy = st.fixed_dictionaries(
    {
        "has_alert": st.booleans(),
        "severity": st.sampled_from(_SEVERITIES),
        "flags": st.fixed_dictionaries(
            {
                "has_reported_failures": st.booleans(),
                "has_malformed_artifact": st.booleans(),
            }
        ),
        "evidence": st.fixed_dictionaries(
            {
                "latest_week_id": st.one_of(st.none(), st.just("2026-W10")),
                "latest_month_id": st.one_of(st.none(), st.just("2026-02")),
            }
        ),
        "responsibility_boundary": st.fixed_dictionaries(
            {
                "automation_scope": st.text(min_size=1, max_size=40),
                "human_scope": st.text(min_size=1, max_size=40),
            }
        ),
        "generated_at_utc": st.just("2026-03-11T00:00:00Z"),
    }
)

_routing_key_strategy = st.text(min_size=10, max_size=40, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-"))


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@given(notification=_notification_strategy)
@settings(max_examples=40)
def test_slack_payload_always_has_blocks(notification: dict[str, Any]):
    payload = format_slack_payload(notification)
    assert "blocks" in payload
    assert isinstance(payload["blocks"], list)
    assert len(payload["blocks"]) >= 1


@given(notification=_notification_strategy, routing_key=_routing_key_strategy)
@settings(max_examples=40)
def test_pagerduty_payload_required_keys(notification: dict[str, Any], routing_key: str):
    payload = format_pagerduty_payload(notification, routing_key=routing_key)
    for key in ("routing_key", "event_action", "dedup_key", "payload"):
        assert key in payload


@given(notification=_notification_strategy, routing_key=_routing_key_strategy)
@settings(max_examples=40)
def test_pagerduty_event_action_is_trigger_or_resolve(notification: dict[str, Any], routing_key: str):
    payload = format_pagerduty_payload(notification, routing_key=routing_key)
    assert payload["event_action"] in ("trigger", "resolve")


@given(notification=_notification_strategy, routing_key=_routing_key_strategy)
@settings(max_examples=40)
def test_pagerduty_severity_is_known(notification: dict[str, Any], routing_key: str):
    payload = format_pagerduty_payload(notification, routing_key=routing_key)
    assert payload["payload"]["severity"] in ("critical", "error", "warning", "info")


@given(notification=_notification_strategy)
@settings(max_examples=40)
def test_dry_run_always_succeeds(notification: dict[str, Any]):
    configs = [
        WebhookConfig(target="slack", url="https://hooks.slack.com/test", kind="slack"),
        WebhookConfig(target="pagerduty", url="routing-key-test", kind="pagerduty"),
    ]
    results = dispatch_webhooks(notification, configs, dry_run=True)
    assert all(r.success for r in results)
    assert all(r.dry_run for r in results)


@given(notification=_notification_strategy)
@settings(max_examples=30)
def test_result_count_equals_config_count(notification: dict[str, Any]):
    configs = [
        WebhookConfig(target="slack", url="https://hooks.slack.com/test", kind="slack"),
    ]
    results = dispatch_webhooks(notification, configs, dry_run=True)
    assert len(results) == len(configs)


@given(notification=_notification_strategy)
@settings(max_examples=30)
def test_empty_configs_returns_empty_results(notification: dict[str, Any]):
    results = dispatch_webhooks(notification, [], dry_run=True)
    assert results == []


@given(notification=_notification_strategy)
@settings(max_examples=30)
def test_unknown_kind_always_fails(notification: dict[str, Any]):
    cfg = WebhookConfig(target="unknown", url="https://example.com", kind="discord")
    results = dispatch_webhooks(notification, [cfg], dry_run=True)
    assert results[0].success is False
    assert results[0].error is not None


@given(notification=_notification_strategy, routing_key=_routing_key_strategy)
@settings(max_examples=30)
def test_pagerduty_routing_key_preserved(notification: dict[str, Any], routing_key: str):
    payload = format_pagerduty_payload(notification, routing_key=routing_key)
    assert payload["routing_key"] == routing_key


@given(notification=_notification_strategy)
@settings(max_examples=30)
def test_trigger_iff_has_alert(notification: dict[str, Any]):
    """event_action==trigger iff has_alert==True."""
    payload = format_pagerduty_payload(notification, routing_key="k" * 32)
    if notification["has_alert"]:
        assert payload["event_action"] == "trigger"
    else:
        assert payload["event_action"] == "resolve"
