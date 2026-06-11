"""Lightweight imports for tests that avoid constructing the full app stack."""
from __future__ import annotations

from importlib import import_module
from types import ModuleType


def load_core_ref_analyzer() -> ModuleType:
    return import_module("src.agents.shared.core_ref_analyzer")


def load_metadata_models() -> ModuleType:
    return import_module("src.agents.metadata_agent.models")


def load_reference_assignment() -> ModuleType:
    return import_module("src.agents.shared.reference_assignment")


def load_research_context_builder() -> ModuleType:
    return import_module("src.agents.shared.research_context_builder")
