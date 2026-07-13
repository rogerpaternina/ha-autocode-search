import pytest

from custom_components.autocode_search.providers.factory import (
    ProviderFactory,
)


def test_create_smartir():

    provider = ProviderFactory.create("smartir")

    assert provider is not None


def test_create_irdb():

    provider = ProviderFactory.create("irdb")

    assert provider is not None
    assert provider.__class__.__name__ == "IRDBProvider"


def test_create_memory_requires_codes() -> None:
    """The memory provider requires explicit codes."""
    provider = ProviderFactory.create("memory", codes=["code-1"])

    assert provider.count() == 0


def test_create_memory_without_codes_raises() -> None:
    """The memory provider rejects creation without codes."""

    with pytest.raises(ValueError):
        ProviderFactory.create("memory")


def test_create_lirc():

    provider = ProviderFactory.create("lirc")

    assert provider is not None


def test_invalid_provider():

    with pytest.raises(ValueError):

        ProviderFactory.create("invalid")
