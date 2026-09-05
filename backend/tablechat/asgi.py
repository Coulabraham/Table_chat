import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tablechat.settings")

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

django_asgi_application = get_asgi_application()

from chat.routing import websocket_urlpatterns as chat_patterns
from chess_game.routing import websocket_urlpatterns as game_patterns

application = ProtocolTypeRouter({
    "http": django_asgi_application,
    "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(game_patterns + chat_patterns))),
})
