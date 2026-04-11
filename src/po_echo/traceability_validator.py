"""Strict validator for requirement-level traceability mappings."""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from typing import Any

_REASON_INVALID_FORMAT = "invalid_format"
_REASON_MODULE_IMPORT_FAILED = "module_import_failed"
_REASON_SYMBOL_NOT_FOUND = "symbol_not_found"
_REASON_FILE_NOT_FOUND = "file_not_found"
_REASON_TEST_SYMBOL_NOT_FOUND = "test_symbol_not_found"


def load_traceability_file(path: Path) -> dict[str, Any]:
    """Load a traceability document from YAML (or JSON fallback)."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"traceability file not found: {path}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read traceability file: {path}") from exc

    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(raw_text)
    except ImportError:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"failed to parse traceability document as JSON: {exc.msg}") from exc
    except Exception as exc:
        raise ValueError(f"failed to parse traceability document as YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("traceability document must be a top-level object")

    return data


def validate_code_ref(ref: str) -> tuple[bool, str | None]:
    """Validate a dotted module symbol reference."""
    if "." not in ref:
        return False, _REASON_INVALID_FORMAT

    module_name, symbol_name = ref.rsplit(".", 1)
    if not module_name or not symbol_name:
        return False, _REASON_INVALID_FORMAT

    module: types.ModuleType | None
    try:
        module = importlib.import_module(module_name)
    except Exception:
        module = _import_local_module_fallback(module_name)
        if module is None:
            return False, _REASON_MODULE_IMPORT_FAILED

    if not hasattr(module, symbol_name):
        return False, _REASON_SYMBOL_NOT_FOUND

    return True, None


def _import_local_module_fallback(module_name: str) -> Any | None:
    """Fallback loader for local src modules when package import side effects fail."""
    src_root = Path(__file__).resolve().parents[1]
    file_path = src_root.joinpath(*module_name.split("."))
    if file_path.with_suffix(".py").is_file():
        target = file_path.with_suffix(".py")
    elif file_path.is_dir() and (file_path / "__init__.py").is_file():
        target = file_path / "__init__.py"
    else:
        return None

    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    src_root_str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)
    parts = module_name.split(".")
    if len(parts) > 1:
        for idx in range(1, len(parts)):
            package_name = ".".join(parts[:idx])
            if package_name in sys.modules:
                continue
            package_dir = src_root.joinpath(*parts[:idx])
            if not package_dir.is_dir():
                continue
            package = types.ModuleType(package_name)
            package.__path__ = [str(package_dir)]
            sys.modules[package_name] = package
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


def validate_test_ref(ref: str, repo_root: Path) -> tuple[bool, str | None]:
    """Validate a test reference path with optional top-level symbol."""
    if "::" in ref:
        file_part, symbol_name = ref.split("::", 1)
        if not file_part or not symbol_name:
            return False, _REASON_INVALID_FORMAT
    else:
        file_part = ref
        symbol_name = None

    test_path = repo_root / file_part
    if not test_path.exists() or not test_path.is_file():
        return False, _REASON_FILE_NOT_FOUND

    if symbol_name is None:
        return True, None

    try:
        content = test_path.read_text(encoding="utf-8")
    except OSError:
        return False, _REASON_TEST_SYMBOL_NOT_FOUND

    escaped = re.escape(symbol_name)
    pattern = re.compile(rf"^def {escaped}\(|^class {escaped}\b", re.MULTILINE)
    if pattern.search(content) is None:
        return False, _REASON_TEST_SYMBOL_NOT_FOUND

    return True, None


def validate_traceability_document(doc: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Validate traceability object shape and all refs."""
    schema_version = doc.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("traceability document missing valid 'schema_version' string")

    entries = doc.get("traceability")
    if not isinstance(entries, list):
        raise ValueError("traceability document missing valid 'traceability' array")

    invalid_code_refs: list[dict[str, str]] = []
    invalid_test_refs: list[dict[str, str]] = []

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"traceability entry at index {idx} must be an object")

        requirement_id = entry.get("requirement_id")
        title = entry.get("title")
        code_refs = entry.get("code_refs")
        tests = entry.get("tests")
        status = entry.get("status")

        if not isinstance(requirement_id, str) or not requirement_id.strip():
            raise ValueError(
                f"traceability entry at index {idx} missing valid 'requirement_id' string"
            )
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"traceability entry {requirement_id} missing valid 'title' string")
        if not isinstance(code_refs, list):
            raise ValueError(f"traceability entry {requirement_id} missing valid 'code_refs' array")
        if not isinstance(tests, list):
            raise ValueError(f"traceability entry {requirement_id} missing valid 'tests' array")
        if not isinstance(status, str) or not status.strip():
            raise ValueError(f"traceability entry {requirement_id} missing valid 'status' string")

        for ref in code_refs:
            if not isinstance(ref, str):
                raise ValueError(f"traceability entry {requirement_id} has non-string code_ref")
            ok, reason = validate_code_ref(ref)
            if not ok and reason is not None:
                invalid_code_refs.append(
                    {
                        "requirement_id": requirement_id,
                        "ref": ref,
                        "reason": reason,
                    }
                )

        for ref in tests:
            if not isinstance(ref, str):
                raise ValueError(f"traceability entry {requirement_id} has non-string test ref")
            ok, reason = validate_test_ref(ref, repo_root=repo_root)
            if not ok and reason is not None:
                invalid_test_refs.append(
                    {
                        "requirement_id": requirement_id,
                        "ref": ref,
                        "reason": reason,
                    }
                )

    return {
        "ok": not invalid_code_refs and not invalid_test_refs,
        "entries_checked": len(entries),
        "invalid_code_refs": invalid_code_refs,
        "invalid_test_refs": invalid_test_refs,
    }


def _detect_repo_root(start: Path) -> Path:
    """Find repository root containing scripts/, src/, and docs/."""
    for candidate in [start, *start.parents]:
        if (candidate / "scripts").is_dir() and (candidate / "src").is_dir() and (
            candidate / "docs"
        ).is_dir():
            return candidate
    raise ValueError("could not determine repository root (expected scripts/, src/, docs/)")


def validate_traceability_file(path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """Load and validate a traceability file."""
    root = repo_root or _detect_repo_root(path.resolve().parent)
    doc = load_traceability_file(path)
    return validate_traceability_document(doc, repo_root=root)
