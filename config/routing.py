"""WebSocket URL routing for Channels.

Phase 2: add notification consumers for IT and Faculty domains.
"""

from django.urls import path
from channels.generic.websocket import AsyncWebsocketConsumer
from apps.notifications.consumers import NotificationConsumer

class DummyEventConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept and immediately close to silently handle stray frontend connections
        await self.accept()
        await self.close()

websocket_urlpatterns = [
    path("ws/events/", DummyEventConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
