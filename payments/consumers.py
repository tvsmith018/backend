import json

from channels.generic.websocket import AsyncWebsocketConsumer


class PaymentStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = f"billing_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection.ready",
                    "message": "Payment event stream connected.",
                }
            )
        )

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def payment_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
