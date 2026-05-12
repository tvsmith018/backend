import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BaseCommentConsumer(AsyncWebsocketConsumer):

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))