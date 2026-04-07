"""Unit tests for webhook_dispatch module.

Tests cover:
- Slack Block Kit payload structure
- PagerDuty Events API v2 payload structure
- dispatch_webhooks dry-run behaviour
- dispatch_webhooks HTTP failure handling
- configs_from_env (env var injection)
- Unknown webhook kind returns failure result
- Responsibility boundary fields present in payloads
"""

from __future__ import annotations

import json
from unittest.mock import patch

from po_echo.webhook_dispatch import (
    WebhookConfig,
    configs_from_env,
    dispatch_webhooks,
    format_pagerduty_payload,
    format_slack_payload,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_notification(
    *,
    has_alert: bool = True,
    severity: str = "SEV-2",
    has_failures: bool = True,
    has_malformed: bool = False,
    week_id: str = "2026-W10",
    month_id: str = "2026-02",
) -> dict:
    return {
        "has_alert": has_alert,
        "severity": severity,
        "flags": {
            "has_reported_failures": has_failures,
            "has_malformed_artifact": has_malformed,
        },
        "evidence": {
            "integrated_summary_path": "reports/operations/p2_integrated_summary.json",
            "latest_week_id": week_id,
            "latest_month_id": month_id,
            "weekly_archive_dir": f"reports/audit/{week_id}",
            "kpi_delta_ref": f"reports/audit/{week_id}/kpi_delta.md",
            "triage_note_ref": f"reports/audit/{week_id}/triage_note.md",
            "monthly_archive_dir": f"reports/gift_rehearsal/{month_id}",
            "monthly_summary_ref": f"reports/gift_rehearsal/{month_id}/summary.json",
        },
        "responsibility_boundary": {
            "automation_scope": "異常フラグの検知・通知ペイロード生成まで。",
            "human_scope": "公開停止・リスク受容・対外説明・恒久対策承認は運用者責任。",
        },
        "generated_at_utc": "2026-03-11T12:00:00Z",
    }


# ---------------------------------------------------------------------------
# Slack payload tests
# ---------------------------------------------------------------------------

class TestFormatSlackPayload:
    def test_blocks_list_present(self):
        payload = format_slack_payload(_make_notification())
        assert "blocks" in payload
        assert isinstance(payload["blocks"], list)
        assert len(payload["blocks"]) >= 2

    def test_header_block_contains_severity(self):
        payload = format_slack_payload(_make_notification(severity="SEV-1"))
        header = payload["blocks"][0]
        assert header["type"] == "header"
        assert "SEV-1" in header["text"]["text"]

    def test_no_alert_title(self):
        payload = format_slack_payload(_make_notification(has_alert=False, severity="NONE"))
        header = payload["blocks"][0]
        assert "No Alert" in header["text"]["text"]

    def test_failures_flag_in_section(self):
        payload = format_slack_payload(_make_notification(has_failures=True))
        sections = [b for b in payload["blocks"] if b["type"] == "section"]
        combined = " ".join(s["text"]["text"] for s in sections)
        assert "has_reported_failures" in combined

    def test_nominal_message_when_no_flags(self):
        payload = format_slack_payload(_make_notification(has_alert=False, has_failures=False, severity="NONE"))
        sections = [b for b in payload["blocks"] if b["type"] == "section"]
        combined = " ".join(s["text"]["text"] for s in sections)
        assert "nominal" in combined

    def test_evidence_links_present(self):
        payload = format_slack_payload(_make_notification(week_id="2026-W10", month_id="2026-02"))
        blocks_text = json.dumps(payload["blocks"])
        assert "2026-W10" in blocks_text
        assert "2026-02" in blocks_text

    def test_human_scope_in_context(self):
        payload = format_slack_payload(_make_notification())
        context_blocks = [b for b in payload["blocks"] if b["type"] == "context"]
        # Check actual text values (not JSON-serialized) to avoid unicode-escape issues.
        combined = " ".join(
            elem.get("text", "") for b in context_blocks for elem in b.get("elements", [])
        )
        assert "Human scope" in combined or "運用者責任" in combined

    def test_generated_at_in_blocks(self):
        payload = format_slack_payload(_make_notification())
        assert "2026-03-11T12:00:00Z" in json.dumps(payload["blocks"])


# ---------------------------------------------------------------------------
# PagerDuty payload tests
# ---------------------------------------------------------------------------

class TestFormatPagerdutyPayload:
    def test_required_keys(self):
        payload = format_pagerduty_payload(_make_notification(), routing_key="a" * 32)
        for key in ("routing_key", "event_action", "dedup_key", "payload"):
            assert key in payload

    def test_trigger_on_alert(self):
        payload = format_pagerduty_payload(_make_notification(has_alert=True), routing_key="x" * 32)
        assert payload["event_action"] == "trigger"

    def test_resolve_on_no_alert(self):
        payload = format_pagerduty_payload(
            _make_notification(has_alert=False, severity="NONE"), routing_key="x" * 32
        )
        assert payload["event_action"] == "resolve"

    def test_routing_key_propagated(self):
        key = "k" * 32
        payload = format_pagerduty_payload(_make_notification(), routing_key=key)
        assert payload["routing_key"] == key

    def test_severity_mapped(self):
        payload = format_pagerduty_payload(_make_notification(severity="SEV-1"), routing_key="k" * 32)
        assert payload["payload"]["severity"] == "critical"

    def test_sev2_maps_to_error(self):
        payload = format_pagerduty_payload(_make_notification(severity="SEV-2"), routing_key="k" * 32)
        assert payload["payload"]["severity"] == "error"

    def test_dedup_key_default(self):
        payload = format_pagerduty_payload(_make_notification(), routing_key="k" * 32)
        assert "project-echo-alert" in payload["dedup_key"]

    def test_dedup_key_override(self):
        payload = format_pagerduty_payload(
            _make_notification(), routing_key="k" * 32, dedup_key="custom-key-123"
        )
        assert payload["dedup_key"] == "custom-key-123"

    def test_custom_details_flags(self):
        payload = format_pagerduty_payload(
            _make_notification(has_failures=True, has_malformed=True), routing_key="k" * 32
        )
        details = payload["payload"]["custom_details"]
        assert details["has_reported_failures"] is True
        assert details["has_malformed_artifact"] is True

    def test_source_field(self):
        payload = format_pagerduty_payload(_make_notification(), routing_key="k" * 32)
        assert payload["payload"]["source"] == "project-echo-ops"


# ---------------------------------------------------------------------------
# dispatch_webhooks — dry-run
# ---------------------------------------------------------------------------

class TestDispatchWebhooksDryRun:
    def _make_slack_config(self) -> WebhookConfig:
        return WebhookConfig(target="slack", url="https://hooks.slack.com/test", kind="slack")

    def _make_pd_config(self) -> WebhookConfig:
        return WebhookConfig(target="pagerduty", url="routing-key-xxx", kind="pagerduty")

    def test_dry_run_returns_success(self):
        results = dispatch_webhooks(
            _make_notification(),
            [self._make_slack_config()],
            dry_run=True,
        )
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].dry_run is True

    def test_dry_run_no_http_call(self):
        with patch("po_echo.webhook_dispatch._http_post") as mock_post:
            dispatch_webhooks(_make_notification(), [self._make_slack_config()], dry_run=True)
            mock_post.assert_not_called()

    def test_dry_run_pagerduty(self):
        results = dispatch_webhooks(
            _make_notification(), [self._make_pd_config()], dry_run=True
        )
        assert results[0].success is True
        assert results[0].dry_run is True

    def test_dry_run_payload_preview_non_empty(self):
        results = dispatch_webhooks(
            _make_notification(), [self._make_slack_config()], dry_run=True
        )
        assert results[0].payload_preview != ""

    def test_multiple_targets(self):
        results = dispatch_webhooks(
            _make_notification(),
            [self._make_slack_config(), self._make_pd_config()],
            dry_run=True,
        )
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_empty_configs(self):
        results = dispatch_webhooks(_make_notification(), [], dry_run=True)
        assert results == []

    def test_unknown_kind_fails(self):
        cfg = WebhookConfig(target="unknown", url="https://example.com", kind="teams")
        results = dispatch_webhooks(_make_notification(), [cfg], dry_run=True)
        assert results[0].success is False
        assert "unknown webhook kind" in (results[0].error or "")


# ---------------------------------------------------------------------------
# dispatch_webhooks — HTTP success / failure
# ---------------------------------------------------------------------------

class TestDispatchWebhooksHttp:
    def _slack_cfg(self) -> WebhookConfig:
        return WebhookConfig(target="slack", url="https://hooks.slack.com/test", kind="slack")

    def test_http_success(self):
        with patch("po_echo.webhook_dispatch._http_post", return_value=(200, "ok")):
            results = dispatch_webhooks(_make_notification(), [self._slack_cfg()])
        assert results[0].success is True
        assert results[0].status_code == 200

    def test_http_failure_status(self):
        with patch("po_echo.webhook_dispatch._http_post", return_value=(503, "Service Unavailable")):
            results = dispatch_webhooks(_make_notification(), [self._slack_cfg()])
        assert results[0].success is False
        assert results[0].status_code == 503

    def test_network_exception(self):
        # retry_delays=() disables retries to keep the test fast.
        with patch("po_echo.webhook_dispatch._http_post", side_effect=OSError("network down")):
            results = dispatch_webhooks(
                _make_notification(), [self._slack_cfg()], retry_delays=()
            )
        assert results[0].success is False
        assert "network down" in (results[0].error or "")
        assert results[0].status_code is None

    def test_network_exception_retries_and_recovers(self):
        """After a transient network failure, retry should succeed on the next attempt."""
        call_results = [OSError("transient"), (200, "ok")]

        def flaky_post(*_args: object, **_kwargs: object) -> tuple[int, str]:
            r = call_results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r  # type: ignore[return-value]

        with patch("po_echo.webhook_dispatch._http_post", side_effect=flaky_post):
            with patch("po_echo.webhook_dispatch.time") as mock_time:
                results = dispatch_webhooks(
                    _make_notification(), [self._slack_cfg()], retry_delays=(0.0,)
                )
        assert results[0].success is True
        assert results[0].status_code == 200
        mock_time.sleep.assert_called_once_with(0.0)

    def test_http_5xx_is_not_retried(self):
        """HTTP 5xx is returned immediately without retry (server received the request)."""
        with patch(
            "po_echo.webhook_dispatch._http_post", return_value=(503, "Service Unavailable")
        ) as mock_post:
            results = dispatch_webhooks(
                _make_notification(),
                [self._slack_cfg()],
                retry_delays=(0.0, 0.0, 0.0),
            )
        assert results[0].success is False
        assert results[0].status_code == 503
        # Must be called exactly once — no retry on HTTP-level responses.
        mock_post.assert_called_once()


# ---------------------------------------------------------------------------
# configs_from_env
# ---------------------------------------------------------------------------

class TestConfigsFromEnv:
    def test_empty_when_no_env(self, monkeypatch):
        monkeypatch.delenv("ECHO_SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("ECHO_PAGERDUTY_ROUTING_KEY", raising=False)
        assert configs_from_env() == []

    def test_slack_only(self, monkeypatch):
        monkeypatch.setenv("ECHO_SLACK_WEBHOOK_URL", "https://hooks.slack.com/abc")
        monkeypatch.delenv("ECHO_PAGERDUTY_ROUTING_KEY", raising=False)
        configs = configs_from_env()
        assert len(configs) == 1
        assert configs[0].kind == "slack"
        assert configs[0].url == "https://hooks.slack.com/abc"

    def test_pagerduty_only(self, monkeypatch):
        monkeypatch.delenv("ECHO_SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.setenv("ECHO_PAGERDUTY_ROUTING_KEY", "routing-key-xyz")
        configs = configs_from_env()
        assert len(configs) == 1
        assert configs[0].kind == "pagerduty"

    def test_both_configured(self, monkeypatch):
        monkeypatch.setenv("ECHO_SLACK_WEBHOOK_URL", "https://hooks.slack.com/abc")
        monkeypatch.setenv("ECHO_PAGERDUTY_ROUTING_KEY", "routing-key-xyz")
        configs = configs_from_env()
        assert len(configs) == 2
        kinds = {c.kind for c in configs}
        assert kinds == {"slack", "pagerduty"}

    def test_custom_env_var_names(self, monkeypatch):
        monkeypatch.setenv("MY_SLACK", "https://hooks.slack.com/custom")
        monkeypatch.delenv("ECHO_SLACK_WEBHOOK_URL", raising=False)
        configs = configs_from_env(slack_url_env="MY_SLACK")
        assert len(configs) == 1
        assert configs[0].url == "https://hooks.slack.com/custom"

    def test_whitespace_only_env_is_skipped(self, monkeypatch):
        monkeypatch.setenv("ECHO_SLACK_WEBHOOK_URL", "   ")
        monkeypatch.delenv("ECHO_PAGERDUTY_ROUTING_KEY", raising=False)
        assert configs_from_env() == []
