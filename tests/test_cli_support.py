"""Tests for extracted po-cosmic CLI helper utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from po_cosmic.cli_support import resolve_cli_path_arg


def test_resolve_cli_path_arg_accepts_matching_values() -> None:
    value = resolve_cli_path_arg(
        "runs/in.json",
        "runs/in.json",
        positional_label="input path",
        option_label="--in",
    )
    assert value == "runs/in.json"


def test_resolve_cli_path_arg_rejects_conflicting_values() -> None:
    with pytest.raises(SystemExit) as exc_info:
        resolve_cli_path_arg(
            str(Path("a.json")),
            str(Path("b.json")),
            positional_label="input path",
            option_label="--in",
        )
    assert exc_info.value.code == 1
