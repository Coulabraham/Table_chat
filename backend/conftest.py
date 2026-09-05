import pytest


@pytest.fixture(autouse=True)
def use_in_memory_channels(settings):
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
