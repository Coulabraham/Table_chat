from .base import *

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

if SECRET_KEY == "unsafe-development-only-key":
    raise RuntimeError("DJANGO_SECRET_KEY must be configured in production")

if os.environ.get("VERCEL") and not os.environ.get("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL must be configured on Vercel")

if os.environ.get("VERCEL") and not os.environ.get("REDIS_URL"):
    raise RuntimeError("REDIS_URL must be configured on Vercel")

if os.environ.get("VERCEL") and not os.environ.get("CACHE_URL"):
    raise RuntimeError("CACHE_URL must be configured on Vercel")
