"""Normalization helpers for recorder payloads."""
from __future__ import annotations

from typing import Any, Dict, List


def compact_payload(value: Any) -> Any:
    """
    Recursively drop null/empty fields while preserving booleans and numeric zero.
    """
    if isinstance(value, dict):
        compact_dict: Dict[str, Any] = {}
        for key, raw in value.items():
            compact_value = compact_payload(raw)
            if compact_value is None:
                continue
            if isinstance(compact_value, str) and not compact_value.strip():
                continue
            if isinstance(compact_value, (list, dict)) and not compact_value:
                continue
            compact_dict[key] = compact_value
        return compact_dict
    if isinstance(value, list):
        compact_list: List[Any] = []
        for item in value:
            compact_item = compact_payload(item)
            if compact_item is None:
                continue
            if isinstance(compact_item, str) and not compact_item.strip():
                continue
            if isinstance(compact_item, (list, dict)) and not compact_item:
                continue
            compact_list.append(compact_item)
        return compact_list
    return value


def compact_stagehand_steps(steps: Any) -> List[Dict[str, Any]]:
    """
    Compact and validate stagehand steps for DB persistence.
    """
    if not isinstance(steps, list):
        return []
    out: List[Dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        compact_step = compact_payload(step)
        if isinstance(compact_step, dict) and compact_step:
            out.append(compact_step)
    return out