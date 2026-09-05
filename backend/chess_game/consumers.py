import uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.exceptions import APIException

from .models import ChessState
from .services import apply_move, serialize_state


class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.group_name = f"game_{self.game_id}"
        if not self.scope["user"].is_authenticated or not await self.can_access():
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "game.state", "state": await self.get_state()})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        if content.get("type") == "game.sync":
            await self.send_json({"type": "game.state", "state": await self.get_state()})
            return
        if content.get("type") != "game.move":
            await self.send_json({"type": "error", "message": "Événement inconnu."})
            return
        try:
            state = await self.make_move(
                content.get("uci", ""),
                content.get("request_id") or str(uuid.uuid4()),
                content.get("revision"),
            )
        except APIException as exc:
            await self.send_json({"type": "game.error", "message": exc.detail})
            return
        await self.channel_layer.group_send(self.group_name, {"type": "broadcast_state", "state": state})

    async def broadcast_state(self, event):
        await self.send_json({"type": "game.state", "state": event["state"]})

    @database_sync_to_async
    def can_access(self):
        return ChessState.objects.filter(game_id=self.game_id, game__participants__user=self.scope["user"]).exists()

    @database_sync_to_async
    def get_state(self):
        return serialize_state(ChessState.objects.select_related("game").get(game_id=self.game_id))

    @database_sync_to_async
    def make_move(self, uci, request_id, revision):
        return apply_move(game_id=self.game_id, user=self.scope["user"], uci=uci, request_id=request_id, expected_revision=revision)

