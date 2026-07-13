"""Shared pytest configuration for Autocode Search tests."""

from __future__ import annotations

import pytest

from custom_components.autocode_search.memory import reset_default_success_memory
from tests.ha_stubs import install_home_assistant_stubs

install_home_assistant_stubs()


@pytest.fixture(autouse=True)
def _reset_success_memory() -> None:
    reset_default_success_memory()
