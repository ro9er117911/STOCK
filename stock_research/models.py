from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Event:
    event_id: str
    ticker: str
    source_type: str
    occurred_at: str
    title: str
    source_url: str
    affected_assumption_ids: list[str]
    marginal_impact: str
    threshold_breach: bool
    requires_refresh: bool
    decision: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
