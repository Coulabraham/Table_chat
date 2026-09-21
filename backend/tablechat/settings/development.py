from .base import *

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() == "true"

