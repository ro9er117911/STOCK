from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if payload:
        payload += "\n"
    path.write_text(payload, encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    existing = read_jsonl(path)
    existing.extend(rows)
    write_jsonl(path, existing)


def sha1_digest(*parts: str) -> str:
    joined = "||".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def deep_merge(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged: dict[str, Any] = {}
        for key in base.keys() | overlay.keys():
            if key in base and key in overlay:
                merged[key] = deep_merge(base[key], overlay[key])
            elif key in overlay:
                merged[key] = overlay[key]
            else:
                merged[key] = base[key]
        return merged
    if isinstance(base, list) and isinstance(overlay, list):
        identity_keys = (
            "assumption_id",
            "action_rule_id",
            "scenario_id",
            "risk_id",
            "source_id",
        )
        if all(isinstance(item, dict) for item in base + overlay):
            identity_key = next(
                (
                    key
                    for key in identity_keys
                    if any(key in item for item in base) or any(key in item for item in overlay)
                ),
                None,
            )
            if identity_key:
                base_map = {item[identity_key]: item for item in base if identity_key in item}
                overlay_map = {item[identity_key]: item for item in overlay if identity_key in item}
                merged_list: list[Any] = []
                seen: set[str] = set()
                for item in base:
                    item_id = item.get(identity_key)
                    if item_id and item_id in overlay_map:
                        merged_list.append(deep_merge(item, overlay_map[item_id]))
                        seen.add(item_id)
                    else:
                        merged_list.append(item)
                for item in overlay:
                    item_id = item.get(identity_key)
                    if item_id and item_id in seen:
                        continue
                    if item_id and item_id in base_map:
                        continue
                    merged_list.append(item)
                return merged_list
        return overlay if overlay else base
    if overlay in (None, ""):
        return base
    return overlay
