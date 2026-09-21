from .base import *

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

if SECRET_KEY == "unsafe-development-only-key":
    raise RuntimeError("DJANGO_SECRET_KEY must be configured in production")

