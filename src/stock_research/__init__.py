"""Automation helpers for the stock research project."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["bootstrap_baselines", "build_dashboard", "draft_refreshes", "poll_events"]

if TYPE_CHECKING:
    from .pipeline import bootstrap_baselines, build_dashboard, draft_refreshes, poll_events


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from . import pipeline

    return getattr(pipeline, name)
