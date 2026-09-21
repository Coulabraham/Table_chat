from .base import *

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://testserver")
