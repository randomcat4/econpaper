from __future__ import annotations

import re
from typing import Any


class StataSpecSafetyError(ValueError):
    """Raised when a spec contains text unsafe to interpolate into Stata code."""


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VAR_TOKEN = re.compile(
    r"^(?:[ibcnos]?\d*\.)?(?:L|F|D|S)?\d*\.?[A-Za-z_][A-Za-z0-9_]*(?:[#]{1,2}(?:[ibcnos]?\d*\.)?(?:L|F|D|S)?\d*\.?[A-Za-z_][A-Za-z0-9_]*)*$"
)
_SAFE_IF_EXPR = re.compile(r"^[A-Za-z0-9_\.\s<>=!&|()+\-*/,]+$")
_SAFE_OPTION = re.compile(r"^[A-Za-z0-9_\.\s=(),:/\-]+$")
_DANGEROUS = re.compile(r"(?i)(?:^|\s)(shell|erase|rm|del|copy|type|winexec|python|!)(?:\s|$)")

SCALAR_VAR_KEYS = {
    "y",
    "treat",
    "post",
    "id",
    "time",
    "gvar",
    "running",
    "cluster",
    "endog",
    "instrument",
    "weight",
    "lat",
    "lon",
    "ppml_y",
}

LIST_VAR_KEYS = {
    "x",
    "covars",
    "controls",
    "fe",
    "absorb",
    "instruments",
    "ppml_x",
}

IF_EXPR_KEYS = {
    "sample_if",
    "if",
    "condition",
}

SPECIAL_ABSORB_TOKENS = {"entity", "time"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _reject_unsafe_text(value: str, field: str) -> None:
    if any(ch in value for ch in ["\n", "\r", ";", "`", '"']):
        raise StataSpecSafetyError(f"{field} contains a Stata command separator or quote.")
    if _DANGEROUS.search(value):
        raise StataSpecSafetyError(f"{field} contains a dangerous Stata command token.")


def _validate_var_token(value: Any, field: str) -> None:
    text = str(value).strip()
    _reject_unsafe_text(text, field)
    if text in SPECIAL_ABSORB_TOKENS:
        return
    if not _VAR_TOKEN.match(text):
        raise StataSpecSafetyError(f"{field} is not a safe Stata variable token: {text!r}")


def _validate_identifier(value: Any, field: str) -> None:
    text = str(value).strip()
    _reject_unsafe_text(text, field)
    if not _IDENT.match(text):
        raise StataSpecSafetyError(f"{field} is not a safe Stata identifier: {text!r}")


def _validate_if_expr(value: Any, field: str) -> None:
    text = str(value).strip()
    _reject_unsafe_text(text, field)
    if not _SAFE_IF_EXPR.match(text):
        raise StataSpecSafetyError(f"{field} contains unsupported characters: {text!r}")


def _validate_option_text(value: Any, field: str) -> None:
    text = str(value).strip()
    _reject_unsafe_text(text, field)
    if text and not _SAFE_OPTION.match(text):
        raise StataSpecSafetyError(f"{field} contains unsupported option characters: {text!r}")


def validate_stata_spec(spec: dict[str, Any]) -> None:
    """Validate common spec fields before interpolating them into a do-file."""

    for key in SCALAR_VAR_KEYS:
        if key in spec and _has_value(spec[key]):
            _validate_identifier(spec[key], key)

    for key in LIST_VAR_KEYS:
        for idx, item in enumerate(_as_list(spec.get(key))):
            if _has_value(item):
                _validate_var_token(item, f"{key}[{idx}]")

    for key in IF_EXPR_KEYS:
        if key in spec and _has_value(spec[key]):
            _validate_if_expr(spec[key], key)

    if isinstance(spec.get("stata"), dict):
        batch_args = spec["stata"].get("batch_args")
        for idx, item in enumerate(_as_list(batch_args)):
            text = str(item).strip()
            _reject_unsafe_text(text, f"stata.batch_args[{idx}]")

    for idx, item in enumerate(_as_list(spec.get("spxtregress_extra_options"))):
        if _has_value(item):
            _validate_option_text(item, f"spxtregress_extra_options[{idx}]")

    for idx, item in enumerate(_as_list(spec.get("spatial_models"))):
        if _has_value(item) and str(item).strip().upper() not in {"SAR", "SEM", "SDM"}:
            raise StataSpecSafetyError(f"spatial_models[{idx}] must be SAR, SEM, or SDM.")

    for idx, item in enumerate(_as_list(spec.get("w_grid"))):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        options = item.get("options")
        if _has_value(name):
            _validate_identifier(name, f"w_grid[{idx}].name")
        if _has_value(options):
            _validate_option_text(options, f"w_grid[{idx}].options")
