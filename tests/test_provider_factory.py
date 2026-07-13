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


def test_create_lirc():

    provider = ProviderFactory.create("lirc")

    assert provider is not None


def test_invalid_provider():

    with pytest.raises(ValueError):

        ProviderFactory.create("invalid")
