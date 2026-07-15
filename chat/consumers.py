import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room, Message, User


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = f'notify_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'room_id': event['room_id'],
            'room_name': event['room_name'],
            'sender': event['sender'],
            'message': event['message'],
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        # Cache room id and member ids on connect — avoids 2 DB hits per message
        self._room_id, self._member_ids = await self.get_room_info()

        await self.accept()

        if self.user and self.user.is_authenticated:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.channel_layer.group_add('presence', self.channel_name)

            await self.set_online_status(True)
            await self.channel_layer.group_send('presence', {
                'type': 'presence_update',
                'user_id': self.user.id,
                'full_name': self.user.full_name,
                'is_online': True,
            })

        history = await self.get_message_history()
        await self.send(text_data=json.dumps({'type': 'history', 'messages': history}))

    async def disconnect(self, close_code):
        if getattr(self, 'user', None) and self.user.is_authenticated:
            await self.set_online_status(False)
            await self.channel_layer.group_send('presence', {
                'type': 'presence_update',
                'user_id': self.user.id,
                'full_name': self.user.full_name,
                'is_online': False,
            })
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_discard('presence', self.channel_name)

    async def receive(self, text_data):
        if not getattr(self, 'user', None) or not self.user.is_authenticated:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Please log in to send messages.'}))
            return

        data = json.loads(text_data)
        msg_type = data.get('type', 'text')

        if msg_type == 'text':
            text = data.get('message', '').strip()
            if not text:
                return
            msg = await self.save_message(text=text, parent_id=data.get('parent_id'))
            await self.broadcast_message(msg)

        elif msg_type == 'file':
            msg = await self.save_message(
                text='',
                file_url=data.get('file_url'),
                file_type=data.get('file_type', 'file'),
                parent_id=data.get('parent_id')
            )
            await self.broadcast_message(msg)

    async def broadcast_message(self, msg):
        await self.channel_layer.group_send(self.room_group_name, {'type': 'chat_message', 'message': msg})
        # Use cached room id and member ids — zero extra DB hits
        for uid in self._member_ids:
            if uid == self.user.id:
                continue
            await self.channel_layer.group_send(f'notify_{uid}', {
                'type': 'send_notification',
                'room_id': self._room_id,
                'room_name': self.room_name,
                'sender': msg['username'],
                'message': msg['message'] or ('📎 File' if msg.get('file_url') else ''),
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', **event['message']}))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'user_id': event['user_id'],
            'full_name': event['full_name'],
            'is_online': event['is_online'],
        }))

    @database_sync_to_async
    def get_room_info(self):
        try:
            room = Room.objects.get(name=self.room_name)
            return room.id, list(room.members.values_list('id', flat=True))
        except Room.DoesNotExist:
            return None, []

    @database_sync_to_async
    def set_online_status(self, status):
        User.objects.filter(id=self.user.id).update(is_online=status, last_seen=timezone.now())

    @database_sync_to_async
    def save_message(self, text='', file_url=None, file_type='', parent_id=None):
        room, _ = Room.objects.get_or_create(name=self.room_name)
        m = Message.objects.create(
            room=room, sender=self.user, text=text,
            file_url=file_url, file_type=file_type, parent_id=parent_id
        )
        return {
            'id': m.id, 'message': m.text,
            'username': self.user.full_name or self.user.email,
            'sender_id': self.user.id,
            'file_url': m.file_url, 'file_type': m.file_type,
            'parent_id': m.parent_id, 'timestamp': m.timestamp.isoformat(),
        }

    @database_sync_to_async
    def get_message_history(self):
        room, _ = Room.objects.get_or_create(name=self.room_name)
        qs = room.messages.select_related('sender').order_by('timestamp')[:50]
        return [{
            'id': m.id, 'message': m.text,
            'username': m.sender.full_name or m.sender.email,
            'sender_id': m.sender.id,
            'file_url': m.file_url, 'file_type': m.file_type,
            'parent_id': m.parent_id, 'timestamp': m.timestamp.isoformat(),
        } for m in qs]