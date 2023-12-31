from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from planetarium.models import AstronomyShow, ShowTheme
from planetarium.serializers import (
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
)

ASTRONOMY_SHOW_URL = reverse("planetarium:astronomyshow-list")


def sample_astronomy_show(**params) -> AstronomyShow:
    defaults = {
        "title": "Sample astronomy show",
        "description": "Some description",
    }
    defaults.update(params)

    return AstronomyShow.objects.create(**defaults)


def detail_url(astronomy_show_id):
    return reverse("planetarium:astronomyshow-detail", args=[astronomy_show_id])


class UnauthenticatedAstronomyShowApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ASTRONOMY_SHOW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAstronomyShowApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@mate.com",
            "secretpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_astronomy_show()
        sample_astronomy_show_with_show_theme = sample_astronomy_show()

        show_theme = ShowTheme.objects.create(name="Test ShowTheme")

        sample_astronomy_show_with_show_theme.show_theme.add(show_theme)

        res = self.client.get(ASTRONOMY_SHOW_URL)

        astronomy_show = AstronomyShow.objects.all()
        serializer = AstronomyShowListSerializer(astronomy_show, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_astronomy_show_by_title(self):
        astronomy_show1 = sample_astronomy_show(title="First astronomy_show")
        astronomy_show2 = sample_astronomy_show(title="Second astronomy_show")

        res = self.client.get(ASTRONOMY_SHOW_URL, {"title": f"{astronomy_show1.title}"})

        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_astronomy_show_by_show_theme(self):
        astronomy_show1 = sample_astronomy_show(title="First astronomy_show")
        astronomy_show2 = sample_astronomy_show(title="Second astronomy_show")
        astronomy_show3 = sample_astronomy_show(title="Show without show_theme")

        show_theme1 = ShowTheme.objects.create(name="Space")
        show_theme2 = ShowTheme.objects.create(name="Sun")

        astronomy_show1.show_theme.add(show_theme1)
        astronomy_show2.show_theme.add(show_theme2)

        res = self.client.get(
            ASTRONOMY_SHOW_URL, {"show_theme": f"{show_theme1.id},{show_theme2.id}"}
        )

        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)
        serializer3 = AstronomyShowListSerializer(astronomy_show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_astronomy_show_detail(self):
        astronomy_show1 = sample_astronomy_show(title="First movie")
        show_theme1 = ShowTheme.objects.create(name="Space")

        astronomy_show1.show_theme.add(show_theme1)

        url = detail_url(astronomy_show1.id)

        res = self.client.get(url)

        serializer = AstronomyShowDetailSerializer(astronomy_show1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_astronomy_show_forbidden(self):
        payload = {
            "title": "Another astronomy_show",
            "description": "Some new description",
        }

        res = self.client.post(ASTRONOMY_SHOW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAstronomyShowApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_admin@test.com", "secretAdminPass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_put_or_delete_astronomy_show_not_allowed(self):
        astronomy_show = sample_astronomy_show()

        url = detail_url(astronomy_show.id)

        res1 = self.client.put(url)
        res2 = self.client.delete(url)

        self.assertEqual(res1.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(res2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
