"""Automation helpers for the stock research project."""

from .pipeline import bootstrap_baselines, draft_refreshes, poll_events

__all__ = ["bootstrap_baselines", "draft_refreshes", "poll_events"]
