import os

settings_module = (
    "tablechat.settings.production"
    if os.environ.get("VERCEL")
    else "tablechat.settings.development"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)

# Vercel attend un gestionnaire ASGI exporté sous le nom ``app``.
app = application
