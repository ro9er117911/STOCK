from __future__ import annotations

import importlib
import sys


def test_package_import_is_lazy() -> None:
    original_package = sys.modules.get("stock_research")
    original_pipeline = sys.modules.get("stock_research.pipeline")

    try:
        sys.modules.pop("stock_research", None)
        sys.modules.pop("stock_research.pipeline", None)

        module = importlib.import_module("stock_research")

        assert "stock_research.pipeline" not in sys.modules
        assert module.__all__ == ["bootstrap_baselines", "build_dashboard", "draft_refreshes", "poll_events"]
    finally:
        sys.modules.pop("stock_research", None)
        sys.modules.pop("stock_research.pipeline", None)
        if original_package is not None:
            sys.modules["stock_research"] = original_package
        if original_pipeline is not None:
            sys.modules["stock_research.pipeline"] = original_pipeline


def test_package_exports_load_pipeline_on_demand() -> None:
    original_package = sys.modules.get("stock_research")
    original_pipeline = sys.modules.get("stock_research.pipeline")

    try:
        sys.modules.pop("stock_research", None)
        sys.modules.pop("stock_research.pipeline", None)

        module = importlib.import_module("stock_research")
        exported = module.bootstrap_baselines

        assert callable(exported)
        assert "stock_research.pipeline" in sys.modules
    finally:
        sys.modules.pop("stock_research", None)
        sys.modules.pop("stock_research.pipeline", None)
        if original_package is not None:
            sys.modules["stock_research"] = original_package
        if original_pipeline is not None:
            sys.modules["stock_research.pipeline"] = original_pipeline
