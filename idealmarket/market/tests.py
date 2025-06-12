from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class SimpleViewTests(TestCase):
    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_admin_management_requires_login(self):
        response = self.client.get(reverse('admin_management'))
        self.assertEqual(response.status_code, 302)  # redirect to login
        user = User.objects.create_user('admin', 'a@example.com', 'pass', is_superuser=True)
        self.client.login(username='admin', password='pass')
        response = self.client.get(reverse('admin_management'))
        self.assertEqual(response.status_code, 200)

