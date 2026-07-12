import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
