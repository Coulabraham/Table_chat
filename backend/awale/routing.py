from django.urls import path

from .consumers import AwaleConsumer

websocket_urlpatterns = [path("ws/awale/games/<uuid:game_id>/", AwaleConsumer.as_asgi())]

