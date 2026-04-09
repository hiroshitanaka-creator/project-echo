#!/usr/bin/env python3
"""CLI entrypoint for strict traceability validation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate docs/traceability/traceability_v1.yaml")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/traceability/traceability_v1.yaml"),
        help="Path to traceability document",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit JSON only")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    validator_path = repo_root / "src" / "po_echo" / "traceability_validator.py"
    spec = importlib.util.spec_from_file_location("traceability_validator", validator_path)
    if spec is None or spec.loader is None:
        print("Error: unable to load traceability validator module", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validate_traceability_file = module.validate_traceability_file

    input_path: Path = args.input
    if not input_path.is_absolute():
        input_path = repo_root / input_path

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        result = validate_traceability_file(input_path, repo_root=repo_root)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"entries_checked: {result['entries_checked']}")
        print(f"invalid_code_refs: {len(result['invalid_code_refs'])}")
        print(f"invalid_test_refs: {len(result['invalid_test_refs'])}")
        for item in result["invalid_code_refs"]:
            print(
                f"invalid_code_ref requirement_id={item['requirement_id']} "
                f"reason={item['reason']} ref={item['ref']}"
            )
        for item in result["invalid_test_refs"]:
            print(
                f"invalid_test_ref requirement_id={item['requirement_id']} "
                f"reason={item['reason']} ref={item['ref']}"
            )

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
