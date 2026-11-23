from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    def test_register_creates_user(self):
        response = self.client.post(
            reverse("register"),
            {"username": "newuser", "password": "StrongPass123"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertNotIn("password", response.data)

    def test_password_is_hashed(self):
        self.client.post(
            reverse("register"),
            {"username": "newuser", "password": "StrongPass123"},
        )
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, "StrongPass123")
        self.assertTrue(user.check_password("StrongPass123"))

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="newuser", password="StrongPass123")
        response = self.client.post(
            reverse("register"),
            {"username": "newuser", "password": "AnotherPass123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse("register"), {"username": "newuser", "password": "12345678"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="StrongPass123"
        )

    def test_login_returns_tokens(self):
        response = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "StrongPass123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_rejected(self):
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "WrongPass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_new_access(self):
        tokens = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "StrongPass123"},
        ).data
        response = self.client.post(
            reverse("refresh"), {"refresh": tokens["refresh"]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class MeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="StrongPass123"
        )

    def test_me_requires_token(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user_role(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")
        self.assertEqual(response.data["role"], "user")

    def test_staff_user_has_moderator_role(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.data["role"], "moderator")

    def test_superuser_has_admin_role(self):
        admin = User.objects.create_superuser(
            username="boss", password="StrongPass123"
        )
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.data["role"], "admin")

class LogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="StrongPass123"
        )
        self.tokens = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "StrongPass123"},
        ).data

    def test_logout_blacklists_refresh(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("logout"), {"refresh": self.tokens["refresh"]}
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        again = self.client.post(
            reverse("refresh"), {"refresh": self.tokens["refresh"]}
        )
        self.assertEqual(again.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_refresh(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("logout"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        response = self.client.post(
            reverse("logout"), {"refresh": self.tokens["refresh"]}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
