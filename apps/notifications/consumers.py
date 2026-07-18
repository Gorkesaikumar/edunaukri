import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.authentication.services.web_jwt_service import WebJWTService

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # We need to authenticate the user from headers or cookies
        self.user = await self.get_user()
        
        if self.user and self.user.is_authenticated:
            self.group_name = f"user_{self.user.pk}_notifications"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # We don't expect the client to send messages here, but we can handle ping/pong if needed
        pass

    async def notification_message(self, event):
        """Handler for 'notification.message' events sent to the group."""
        message = event.get("message", {})
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))

    @database_sync_to_async
    def get_user(self):
        # Attempt to resolve the user using Django's standard session or WebJWTService
        from django.contrib.auth.models import AnonymousUser
        user = self.scope.get("user", AnonymousUser())
        if user.is_authenticated:
            return user
        
        # If headers/cookies exist, maybe we can resolve it via WebJWTService manually
        # Normally Channels AuthMiddlewareStack populates scope['user'] if session auth is used
        return user
