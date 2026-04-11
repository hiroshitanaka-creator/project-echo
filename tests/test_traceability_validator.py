from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path("src/po_echo/traceability_validator.py").resolve()
SPEC = importlib.util.spec_from_file_location("traceability_validator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(_module)

validate_code_ref = _module.validate_code_ref
validate_test_ref = _module.validate_test_ref
validate_traceability_document = _module.validate_traceability_document
validate_traceability_file = _module.validate_traceability_file


def _mk_doc(code_refs: list[str], tests: list[str]) -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "traceability": [
            {
                "requirement_id": "REQ-TMP-001",
                "title": "Temporary requirement",
                "code_refs": code_refs,
                "tests": tests,
                "status": "implemented",
            }
        ],
    }


def test_validate_code_ref_valid_dotted_symbol() -> None:
    ok, reason = validate_code_ref("po_echo.diversity.apply_semantic_diversity")
    assert ok is True
    assert reason is None


def test_validate_code_ref_without_dot_is_invalid_format() -> None:
    ok, reason = validate_code_ref("invalidref")
    assert ok is False
    assert reason == "invalid_format"


def test_validate_code_ref_missing_module_is_module_import_failed() -> None:
    ok, reason = validate_code_ref("definitely_missing_module.symbol")
    assert ok is False
    assert reason == "module_import_failed"


def test_validate_code_ref_missing_symbol_is_symbol_not_found() -> None:
    ok, reason = validate_code_ref("po_echo.diversity.no_such_symbol")
    assert ok is False
    assert reason == "symbol_not_found"


def test_validate_test_ref_file_only_valid(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "sample_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_example():\n    pass\n", encoding="utf-8")

    ok, reason = validate_test_ref("tests/sample_test.py", repo_root=tmp_path)
    assert ok is True
    assert reason is None


def test_validate_test_ref_missing_file_is_file_not_found(tmp_path: Path) -> None:
    ok, reason = validate_test_ref("tests/missing_test.py", repo_root=tmp_path)
    assert ok is False
    assert reason == "file_not_found"


def test_validate_test_ref_symbol_valid(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "symbols_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "def test_target():\n    pass\n\nclass TestTarget:\n    pass\n",
        encoding="utf-8",
    )

    ok, reason = validate_test_ref("tests/symbols_test.py::test_target", repo_root=tmp_path)
    assert ok is True
    assert reason is None


def test_validate_test_ref_symbol_missing_is_test_symbol_not_found(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "symbols_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_other():\n    pass\n", encoding="utf-8")

    ok, reason = validate_test_ref("tests/symbols_test.py::test_target", repo_root=tmp_path)
    assert ok is False
    assert reason == "test_symbol_not_found"


def test_document_validation_fails_when_code_ref_broken(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "ok_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    pass\n", encoding="utf-8")

    doc = _mk_doc(["po_echo.diversity.no_such_symbol"], ["tests/ok_test.py::test_ok"])
    result = validate_traceability_document(doc, repo_root=tmp_path)

    assert result["ok"] is False
    assert result["entries_checked"] == 1
    assert result["invalid_code_refs"] == [
        {
            "requirement_id": "REQ-TMP-001",
            "ref": "po_echo.diversity.no_such_symbol",
            "reason": "symbol_not_found",
        }
    ]
    assert result["invalid_test_refs"] == []


def test_document_validation_fails_when_test_ref_broken(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "ok_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    pass\n", encoding="utf-8")

    doc = _mk_doc(
        ["po_echo.diversity.apply_semantic_diversity"], ["tests/ok_test.py::test_missing"]
    )
    result = validate_traceability_document(doc, repo_root=tmp_path)

    assert result["ok"] is False
    assert result["entries_checked"] == 1
    assert result["invalid_code_refs"] == []
    assert result["invalid_test_refs"] == [
        {
            "requirement_id": "REQ-TMP-001",
            "ref": "tests/ok_test.py::test_missing",
            "reason": "test_symbol_not_found",
        }
    ]


def test_checked_in_traceability_file_is_valid() -> None:
    result = validate_traceability_file(
        Path("docs/traceability/traceability_v1.yaml"), repo_root=Path.cwd()
    )
    assert result["ok"] is True
    assert result["entries_checked"] > 0
    assert result["invalid_code_refs"] == []
    assert result["invalid_test_refs"] == []


def test_cli_json_output_and_exit_code_matches_ok(tmp_path: Path) -> None:
    valid_file = tmp_path / "valid.json"
    valid_doc = _mk_doc(["po_echo.diversity.apply_semantic_diversity"], [])
    valid_file.write_text(json.dumps(valid_doc), encoding="utf-8")

    cmd = [sys.executable, "scripts/validate_traceability.py", "--json", "--input", str(valid_file)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert set(payload.keys()) == {
        "ok",
        "entries_checked",
        "invalid_code_refs",
        "invalid_test_refs",
    }

    invalid_file = tmp_path / "invalid.json"
    invalid_doc = _mk_doc(["po_echo.diversity.missing_symbol"], [])
    invalid_file.write_text(json.dumps(invalid_doc), encoding="utf-8")

    bad_cmd = [
        sys.executable,
        "scripts/validate_traceability.py",
        "--json",
        "--input",
        str(invalid_file),
    ]
    bad_proc = subprocess.run(bad_cmd, capture_output=True, text=True, check=False)

    assert bad_proc.returncode == 1
    bad_payload = json.loads(bad_proc.stdout)
    assert bad_payload["ok"] is False
