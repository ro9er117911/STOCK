"""Automation helpers for the stock research project."""

from .pipeline import bootstrap_baselines, build_dashboard, draft_refreshes, poll_events

__all__ = ["bootstrap_baselines", "build_dashboard", "draft_refreshes", "poll_events"]
