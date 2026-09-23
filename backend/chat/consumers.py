import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.access import can_use_private_messaging, email_verification_satisfied
from accounts.models import UserBlock
from accounts.services import session_group_name
from .models import Conversation
from .services import publish_pending_events

logger = logging.getLogger(__name__)


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    AUTHENTICATION_REQUIRED = 4401
    ACCESS_FORBIDDEN = 4403
    EMAIL_VERIFICATION_REQUIRED = 4404

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.user = self.scope.get("user")
        close_code = await self.authorization_close_code()
        if close_code:
            await self.close(code=close_code)
            return
        self.conversation_group = f"conversation_{self.conversation_id}"
        self.session_group = session_group_name(self.scope["session"].session_key)
        await self.channel_layer.group_add(self.conversation_group, self.channel_name)
        await self.channel_layer.group_add(self.session_group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "ready"})
        await self.retry_pending_events()

    async def disconnect(self, close_code):
        if hasattr(self, "conversation_group"):
            for group in (self.conversation_group, self.session_group):
                try:
                    await self.channel_layer.group_discard(group, self.channel_name)
                except Exception as exc:
                    # Le groupe Redis expire de lui-même. Une indisponibilité
                    # pendant le nettoyage ne doit pas transformer une fermeture
                    # normale du navigateur en erreur ASGI.
                    logger.warning(
                        "Nettoyage du groupe WebSocket différé (%s).",
                        type(exc).__name__,
                    )

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            if not await self.session_is_valid():
                await self.close(code=self.AUTHENTICATION_REQUIRED)
            elif close_code := await self.authorization_close_code():
                await self.close(code=close_code)
            else:
                # Vercel n'exécute pas le worker Docker permanent. Le ping du
                # client fournit une relance bornée lorsque Redis revient sans
                # attendre une nouvelle connexion ou un nouvel envoi.
                await self.retry_pending_events()
                await self.send_json({"type": "pong"})

    async def chat_message(self, event):
        if not await self.session_is_valid():
            await self.close(code=self.AUTHENTICATION_REQUIRED)
            return
        if close_code := await self.authorization_close_code():
            await self.close(code=close_code)
            return
        await self.send_json({"type": "message.created", "message": event["message"]})

    async def session_revoked(self, event):
        await self.close(code=self.AUTHENTICATION_REQUIRED)

    async def access_changed(self, event):
        if close_code := await self.authorization_close_code():
            await self.close(code=close_code)

    @database_sync_to_async
    def authorization_close_code(self):
        if not can_use_private_messaging(self.user):
            if (
                self.user
                and self.user.is_authenticated
                and self.user.is_active
                and not email_verification_satisfied(self.user)
            ):
                return self.EMAIL_VERIFICATION_REQUIRED
            return self.AUTHENTICATION_REQUIRED
        conversation = Conversation.objects.filter(pk=self.conversation_id).filter(
            user_low=self.user
        ).first() or Conversation.objects.filter(pk=self.conversation_id, user_high=self.user).first()
        if conversation is None:
            return self.ACCESS_FORBIDDEN
        if UserBlock.objects.filter(
            blocker_id__in=(conversation.user_low_id, conversation.user_high_id),
            blocked_id__in=(conversation.user_low_id, conversation.user_high_id),
        ).exists():
            return self.ACCESS_FORBIDDEN
        return None

    @database_sync_to_async
    def session_is_valid(self):
        session = self.scope.get("session")
        return bool(self.user.is_active and session and session.session_key and Session.objects.filter(session_key=session.session_key, expire_date__gt=timezone.now()).exists())

    @database_sync_to_async
    def retry_pending_events(self):
        return publish_pending_events(conversation_id=self.conversation_id)
