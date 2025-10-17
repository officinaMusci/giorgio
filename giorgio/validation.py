"""Utilities for statically validating Giorgio scripts.

This module performs safety-first validation using Python's AST without
executing user code. Validation ensures that each script defines the
expected top-level metadata and entry point while avoiding side-effects.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Tuple


ValidationLevel = Literal["error", "warning"]
@dataclass(frozen=True)
class ValidationMessage:
    path: Path
    level: ValidationLevel
    message: str


@dataclass(frozen=True)
class ValidationSummary:
    entries: List[Tuple[Path, List[ValidationMessage]]]
    total_scripts: int

    @property
    def has_errors(self) -> bool:
        return any(message.level == "error" for _, messages in self.entries for message in messages)

    @property
    def has_warnings(self) -> bool:
        return any(message.level == "warning" for _, messages in self.entries for message in messages)

    @property
    def no_scripts(self) -> bool:
        return self.total_scripts == 0

    @property
    def has_messages(self) -> bool:
        return any(messages for _, messages in self.entries)



@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single validation finding."""

    level: ValidationLevel
    code: str
    message: str

    def is_error(self) -> bool:
        return self.level == "error"


def _find_assignment(module: ast.Module, name: str) -> Optional[ast.AST]:
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == name:
                return node.value
    return None


def _validate_config(node: Optional[ast.AST]) -> List[ValidationIssue]:
    if node is None:
        return [ValidationIssue("error", "CONFIG_MISSING", "Missing CONFIG definition.")]

    if not isinstance(node, ast.Dict):
        return [ValidationIssue("error", "CONFIG_NOT_DICT", "CONFIG must be a dict literal.")]

    values = _dict_literal(node)
    issues: List[ValidationIssue] = []

    if values is None:
        return [ValidationIssue("error", "CONFIG_UNSUPPORTED", "CONFIG contains unsupported expressions.")]

    name = values.get("name")
    description = values.get("description")

    if not isinstance(name, str) or not name.strip():
        issues.append(
            ValidationIssue(
                "error",
                "CONFIG_NAME_INVALID",
                "CONFIG['name'] must be a non-empty string.",
            )
        )

    if not isinstance(description, str) or not description.strip():
        issues.append(
            ValidationIssue(
                "error",
                "CONFIG_DESCRIPTION_INVALID",
                "CONFIG['description'] must be a non-empty string.",
            )
        )

    return issues


def _validate_params(node: Optional[ast.AST]) -> List[ValidationIssue]:
    if node is None:
        return [
            ValidationIssue(
                "warning",
                "PARAMS_MISSING",
                "PARAMS is not defined; define an empty dict if no parameters are required.",
            )
        ]

    if not isinstance(node, ast.Dict):
        return [ValidationIssue("error", "PARAMS_NOT_DICT", "PARAMS must be a dict literal.")]

    issues: List[ValidationIssue] = []

    for key_node, value_node in zip(node.keys, node.values):
        key = _const_str(key_node)

        if key is None:
            issues.append(
                ValidationIssue(
                    "error",
                    "PARAM_KEY_INVALID",
                    "PARAMS keys must be string literals.",
                )
            )
            continue

        if isinstance(value_node, ast.Dict):
            issues.extend(_validate_param_entry(key, value_node))
        else:
            issues.append(
                ValidationIssue(
                    "error",
                    "PARAM_ENTRY_NOT_DICT",
                    f"Parameter '{key}' metadata must be a dict literal.",
                )
            )

    return issues


def _validate_param_entry(name: str, node: ast.Dict) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    fields: Dict[str, ast.AST] = {}

    for key_node, value_node in zip(node.keys, node.values):
        field_key = _const_str(key_node)
        if field_key is None:
            issues.append(
                ValidationIssue(
                    "error",
                    "PARAM_FIELD_KEY_INVALID",
                    f"Parameter '{name}' metadata keys must be string literals.",
                )
            )
            continue
        fields[field_key] = value_node

    if "type" not in fields:
        issues.append(
            ValidationIssue(
                "error",
                "PARAM_TYPE_MISSING",
                f"Parameter '{name}' must declare a 'type'.",
            )
        )

    description_node = fields.get("description")
    if description_node is None:
        issues.append(
            ValidationIssue(
                "warning",
                "PARAM_DESCRIPTION_MISSING",
                f"Parameter '{name}' is missing a description.",
            )
        )
    else:
        description_value = _literal_value(description_node)
        if not isinstance(description_value, str):
            issues.append(
                ValidationIssue(
                    "warning",
                    "PARAM_DESCRIPTION_INVALID",
                    f"Parameter '{name}' description should be a string literal.",
                )
            )

    for flag_key in {"required", "multiple"}:
        flag_node = fields.get(flag_key)
        if flag_node is None:
            continue
        literal = _literal_value(flag_node)
        if not _is_bool(literal):
            issues.append(
                ValidationIssue(
                    "warning",
                    "PARAM_FLAG_NOT_BOOL",
                    f"Parameter '{name}' field '{flag_key}' should be a boolean literal.",
                )
            )

    choices_node = fields.get("choices")
    if choices_node is not None:
        literal = _literal_value(choices_node)
        if literal is _UNSUPPORTED or not _is_literal_sequence(literal):
            issues.append(
                ValidationIssue(
                    "warning",
                    "PARAM_CHOICES_NOT_LITERAL",
                    f"Parameter '{name}' field 'choices' should be a literal list or tuple.",
                )
            )

    return issues


def _validate_run_function(module: ast.Module) -> List[ValidationIssue]:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            total_args = len(node.args.args)
            if total_args < 1:
                return [
                    ValidationIssue(
                        "error",
                        "RUN_SIGNATURE_INVALID",
                        "run(context) must accept at least one positional argument.",
                    )
                ]
            first_arg = node.args.args[0].arg
            if first_arg != "context":
                return [
                    ValidationIssue(
                        "warning",
                        "RUN_ARG_NAME",
                        "First argument for run(context) should be named 'context'.",
                    )
                ]
            return []

    return [ValidationIssue("error", "RUN_MISSING", "Missing run(context) function.")]


def _dict_literal(node: ast.Dict) -> Optional[Dict[str, object]]:
    result: Dict[str, object] = {}

    for key_node, value_node in zip(node.keys, node.values):
        key = _const_str(key_node)
        if key is None:
            return None

        value = _literal_value(value_node)
        if value is _UNSUPPORTED:
            return None

        result[key] = value

    return result


_UNSUPPORTED = object()


def _literal_value(node: ast.AST):  # type: ignore[no-untyped-def]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        inner = _dict_literal(node)
        return inner if inner is not None else _UNSUPPORTED
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = []
        for elt in node.elts:
            val = _literal_value(elt)
            if val is _UNSUPPORTED:
                return _UNSUPPORTED
            values.append(val)
        if isinstance(node, ast.Tuple):
            return tuple(values)
        if isinstance(node, ast.Set):
            return set(values)
        return values
    return _UNSUPPORTED


def _const_str(node: Optional[ast.AST]) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _is_literal_sequence(value: object) -> bool:
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, (str, int, float, bool)) for item in value)
    return False


def validate_script(script_path: Path) -> List[ValidationIssue]:
    """Validate a single Giorgio script using static analysis."""

    try:
        source = script_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [ValidationIssue("error", "IO_ERROR", f"Failed to read script: {exc}")]

    try:
        module = ast.parse(source, filename=str(script_path))
    except SyntaxError as exc:
        return [
            ValidationIssue(
                "error",
                "SYNTAX_ERROR",
                f"Syntax error at line {exc.lineno}: {exc.msg}",
            )
        ]

    issues: List[ValidationIssue] = []

    config_node = _find_assignment(module, "CONFIG")
    issues.extend(_validate_config(config_node))

    params_node = _find_assignment(module, "PARAMS")
    issues.extend(_validate_params(params_node))

    issues.extend(_validate_run_function(module))

    return issues


def validate_project(project_root: Path) -> Dict[Path, List[ValidationIssue]]:
    """Validate every Giorgio script under ``project_root``.

    :param project_root: Path to the project root directory.
    :returns: Mapping of script paths to their validation findings.
    """

    scripts_dir = project_root / "scripts"
    results: Dict[Path, List[ValidationIssue]] = {}

    if not scripts_dir.exists():
        return results

    for script_path in sorted(scripts_dir.rglob("script.py")):
        results[script_path.relative_to(project_root)] = validate_script(script_path)

    return results


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    return any(issue.is_error() for issue in issues)


def summarize_validation(results: Dict[Path, List[ValidationIssue]]) -> ValidationSummary:
    entries: List[Tuple[Path, List[ValidationMessage]]] = []

    for path in sorted(results, key=lambda p: str(p)):
        issues = results[path]
        messages = [ValidationMessage(path=path, level=issue.level, message=issue.message) for issue in issues]
        if messages:
            entries.append((path, messages))

    return ValidationSummary(entries=entries, total_scripts=len(results))
