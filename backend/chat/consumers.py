from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.models import UserBlock
from accounts.services import session_group_name
from .models import Conversation


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated or not await self.authorized():
            await self.close(code=4403)
            return
        self.conversation_group = f"conversation_{self.conversation_id}"
        self.session_group = session_group_name(self.scope["session"].session_key)
        await self.channel_layer.group_add(self.conversation_group, self.channel_name)
        await self.channel_layer.group_add(self.session_group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "ready"})

    async def disconnect(self, close_code):
        if hasattr(self, "conversation_group"):
            await self.channel_layer.group_discard(self.conversation_group, self.channel_name)
            await self.channel_layer.group_discard(self.session_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            if not await self.session_is_valid():
                await self.close(code=4401)
            elif not await self.authorized():
                await self.close(code=4403)
            else:
                await self.send_json({"type": "pong"})

    async def chat_message(self, event):
        if not await self.session_is_valid():
            await self.close(code=4401)
            return
        if not await self.authorized():
            await self.close(code=4403)
            return
        await self.send_json({"type": "message.created", "message": event["message"]})

    async def session_revoked(self, event):
        await self.close(code=4401)

    async def access_changed(self, event):
        if not await self.authorized():
            await self.close(code=4403)

    @database_sync_to_async
    def authorized(self):
        if not self.user.email_verified_at:
            return False
        conversation = Conversation.objects.filter(pk=self.conversation_id).filter(
            user_low=self.user
        ).first() or Conversation.objects.filter(pk=self.conversation_id, user_high=self.user).first()
        if conversation is None:
            return False
        return not UserBlock.objects.filter(
            blocker_id__in=(conversation.user_low_id, conversation.user_high_id),
            blocked_id__in=(conversation.user_low_id, conversation.user_high_id),
        ).exists()

    @database_sync_to_async
    def session_is_valid(self):
        session = self.scope.get("session")
        return bool(self.user.is_active and session and session.session_key and Session.objects.filter(session_key=session.session_key, expire_date__gt=timezone.now()).exists())
