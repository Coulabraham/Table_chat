from django.urls import path
from .consumers import GameConsumer

websocket_urlpatterns = [path("ws/games/<uuid:game_id>/", GameConsumer.as_asgi())]

