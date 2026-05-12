from datetime import date

from django.contrib.auth import get_user_model
from graphql_relay.node.node import to_global_id
from rest_framework.test import APITestCase

from articles.models import Articles

User = get_user_model()


class ArticleRatingViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="rating@example.com",
            firstname="Rate",
            lastname="User",
            password="Password123!",
            dob=date(1991, 2, 2),
            bio="bio",
        )
        self.article = Articles.objects.create(
            title="Rating test article",
            altImage="alt text",
            category="news",
            briefsummary="Brief",
            author=self.user,
        )
        login = self.client.post(
            "/authorized/login/",
            {
                "email": "rating@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.access_token = login.data["access"]
        self.article_gid = to_global_id("ArticlesNode", str(self.article.pk))

    def test_get_rating_requires_auth(self):
        self.client.credentials()
        url = f"/articles/rating/{self.article_gid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_get_rating_returns_has_rated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        url = f"/articles/rating/{self.article_gid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertFalse(response.data["data"]["has_rated"])

    def test_set_rating_succeeds(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        url = f"/articles/rating/{self.article_gid}/set/"
        response = self.client.post(url, {"rate": 5}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        get_response = self.client.get(f"/articles/rating/{self.article_gid}/")
        self.assertEqual(get_response.status_code, 200)
        self.assertTrue(get_response.data["data"]["has_rated"])
