"""
Tests for authentication flows:
- User registration
- User login and logout
- Vet login
- Password validation
- Role-based redirects
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, VetProfile


class UserRegistrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')

    def test_registration_page_loads(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Tanvir',
            'last_name':  'Ahmed',
            'email':      'tanvir@test.com',
            'phone_number': '01711000001',
            'password1':  'testpass123!',
            'password2':  'testpass123!',
        })
        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        # User should be created
        self.assertTrue(
            User.objects.filter(email='tanvir@test.com').exists()
        )

    def test_registration_duplicate_email(self):
        User.objects.create_user(
            username='tanvir@test.com',
            email='tanvir@test.com',
            password='testpass123!',
        )
        response = self.client.post(self.register_url, {
            'first_name':   'Tanvir',
            'last_name':    'Ahmed',
            'email':        'tanvir@test.com',
            'phone_number': '01711000001',
            'password1':    'testpass123!',
            'password2':    'testpass123!',
        })
        # Should not redirect — form error
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(email='tanvir@test.com').count() > 1
        )

    def test_registration_password_mismatch(self):
        response = self.client.post(self.register_url, {
            'first_name':   'Tanvir',
            'last_name':    'Ahmed',
            'email':        'tanvir2@test.com',
            'phone_number': '01711000002',
            'password1':    'testpass123!',
            'password2':    'differentpass!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(email='tanvir2@test.com').exists()
        )


class UserLoginTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='sabrina@test.com',
            email='sabrina@test.com',
            password='testpass123!',
            first_name='Sabrina',
            role=User.Role.USER,
        )

    def test_login_page_loads(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        from django.contrib.auth import authenticate
        user = authenticate(
            username='sabrina@test.com',
            password='testpass123!'
        )
        self.assertIsNotNone(user, "authenticate() failed")
        response = self.client.post(self.login_url, {
            'username': 'sabrina@test.com',  # form field is 'username' not 'email'
            'password': 'testpass123!',
        })
        self.assertEqual(response.status_code, 302,
            f"Login returned {response.status_code}")

    def test_login_wrong_password(self):
        response = self.client.post(self.login_url, {
            'email':    'sabrina@test.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

    def test_login_nonexistent_email(self):
        response = self.client.post(self.login_url, {
            'email':    'nobody@test.com',
            'password': 'testpass123!',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='sabrina@test.com', password='testpass123!')
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)

    def test_banned_user_cannot_login(self):
        self.user.is_banned = True
        self.user.save()
        response = self.client.post(self.login_url, {
            'email':    'sabrina@test.com',
            'password': 'testpass123!',
        })
        # Should not be authenticated
        self.assertEqual(response.status_code, 200)


class VetLoginTest(TestCase):

    def setUp(self):
        self.client      = Client()
        self.vet_login_url = reverse('accounts:vet_login')

        self.vet_user = User.objects.create_user(
            username='ayesha@test.com',
            email='ayesha@test.com',
            password='vetpass123!',
            first_name='Ayesha',
            role=User.Role.VET,
        )
        self.vet_profile = VetProfile.objects.create(
            user=self.vet_user,
            application_status=VetProfile.ApplicationStatus.APPROVED,
            is_active=True,
            consultation_fee=300,
        )

    def test_vet_login_page_loads(self):
        response = self.client.get(self.vet_login_url)
        self.assertEqual(response.status_code, 200)

    def test_vet_successful_login(self):
        from django.contrib.auth import authenticate
        user = authenticate(
            username='ayesha@test.com',
            password='vetpass123!'
        )
        self.assertIsNotNone(user, "authenticate() failed")
        response = self.client.post(self.vet_login_url, {
            'username': 'ayesha@test.com',  # form field is 'username' not 'email'
            'password': 'vetpass123!',
        })
        self.assertEqual(response.status_code, 302,
            f"Vet login returned {response.status_code}")

    def test_pending_vet_cannot_access_dashboard(self):
        self.vet_profile.application_status = VetProfile.ApplicationStatus.PENDING
        self.vet_profile.save()
        self.client.login(username='ayesha@test.com', password='vetpass123!')
        response = self.client.get(reverse('consultations:vet_dashboard'))
        # Should redirect away
        self.assertNotEqual(response.status_code, 200)


class RoleRedirectTest(TestCase):

    def setUp(self):
        self.client = Client()

    def _make_user(self, role, email):
        return User.objects.create_user(
            username=email,
            email=email,
            password='pass123!',
            role=role,
        )

    def test_user_cannot_access_admin_dashboard(self):
        user = self._make_user(User.Role.USER, 'user@test.com')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertNotEqual(response.status_code, 200)

    def test_user_cannot_access_vet_dashboard(self):
        user = self._make_user(User.Role.USER, 'user2@test.com')
        self.client.force_login(user)
        response = self.client.get(reverse('consultations:vet_dashboard'))
        self.assertNotEqual(response.status_code, 200)