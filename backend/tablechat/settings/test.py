from .base import *

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
