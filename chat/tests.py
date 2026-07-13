import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Room


class LoginViewTests(TestCase):
    def test_login_returns_tokens(self):
        User = get_user_model()
        User.objects.create_user(
            email='test@example.com',
            phone_number='+2348000000000',
            full_name='Test User',
            password='strongpassword123',
        )

        response = self.client.post(
            reverse('login'),
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'strongpassword123',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)


class PrivateChatRoomTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user_a = self.User.objects.create_user(
            email='usera@example.com',
            phone_number='+2348000000001',
            full_name='User A',
            password='strongpassword123',
        )
        self.user_b = self.User.objects.create_user(
            email='userb@example.com',
            phone_number='+2348000000002',
            full_name='User B',
            password='strongpassword123',
        )

    def test_private_chat_creates_one_room_per_pair_of_users(self):
        self.client.force_login(self.user_a)

        first = self.client.post(
            reverse('start_private_chat'),
            data=json.dumps({'user_id': self.user_b.id}),
            content_type='application/json',
        )
        second = self.client.post(
            reverse('start_private_chat'),
            data=json.dumps({'user_id': self.user_b.id}),
            content_type='application/json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Room.objects.filter(is_group=False).count(), 1)
        self.assertEqual(Room.objects.filter(is_group=False, members=self.user_a).filter(members=self.user_b).count(), 1)

    def test_group_chat_reuses_existing_room_for_same_members(self):
        self.client.force_login(self.user_a)

        first = self.client.post(
            reverse('create_group_chat'),
            data=json.dumps({'name': 'Team', 'member_ids': [self.user_b.id]}),
            content_type='application/json',
        )
        second = self.client.post(
            reverse('create_group_chat'),
            data=json.dumps({'name': 'Team', 'member_ids': [self.user_b.id]}),
            content_type='application/json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Room.objects.filter(is_group=True).count(), 1)

    def test_list_users_only_returns_existing_contacts(self):
        self.client.force_login(self.user_a)
        room = Room.objects.create(name='dm_usera_userb', is_group=False)
        room.members.add(self.user_a, self.user_b)

        response = self.client.get(reverse('list_users'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.user_b.id)
