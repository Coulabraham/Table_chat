"""Entrée ASGI explicite utilisée par Vercel Services."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tablechat.settings.production")

from tablechat.asgi import application

app = application
