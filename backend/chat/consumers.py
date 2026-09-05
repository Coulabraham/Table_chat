import time
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db import IntegrityError

from .models import Conversation, Message
from .serializers import MessageSerializer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"
        self.sent_at = []
        if not self.scope["user"].is_authenticated or not await self.can_access():
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        if content.get("type") != "chat.message":
            return
        now = time.monotonic()
        self.sent_at = [stamp for stamp in self.sent_at if now - stamp < 10]
        if len(self.sent_at) >= 5:
            await self.send_json({"type": "chat.error", "message": "Vous envoyez des messages trop rapidement."})
            return
        text = str(content.get("content", "")).strip()
        if not text or len(text) > 1000:
            await self.send_json({"type": "chat.error", "message": "Le message doit contenir entre 1 et 1 000 caractères."})
            return
        self.sent_at.append(now)
        message = await self.create_message(text, content.get("client_id") or str(uuid.uuid4()))
        await self.channel_layer.group_send(self.group_name, {"type": "broadcast_message", "message": message})

    async def broadcast_message(self, event):
        await self.send_json({"type": "chat.message", "message": event["message"]})

    @database_sync_to_async
    def can_access(self):
        return Conversation.objects.filter(pk=self.conversation_id, memberships__user=self.scope["user"]).exists()

    @database_sync_to_async
    def create_message(self, content, client_id):
        try:
            message, _ = Message.objects.get_or_create(
                conversation_id=self.conversation_id,
                author=self.scope["user"],
                client_id=client_id,
                defaults={"content": content},
            )
        except (IntegrityError, ValueError):
            message = Message.objects.get(conversation_id=self.conversation_id, author=self.scope["user"], client_id=client_id)
        return MessageSerializer(message).data

