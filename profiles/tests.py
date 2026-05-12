import asyncio
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from asgiref.sync import async_to_sync

from profiles.consumer.profilepost import ProfilePostConsumer
from profiles.models import ProfilePost, ProfilePostShare

User = get_user_model()


class ProfileMeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="profile@example.com",
            firstname="Pro",
            lastname="File",
            password="Password123!",
            dob=date(1998, 1, 1),
            bio="bio",
        )

    def test_profile_me_requires_authentication(self):
        response = self.client.get("/profiles/me/")
        self.assertEqual(response.status_code, 401)

    def test_profile_me_returns_envelope_for_authenticated_user(self):
        login_response = self.client.post(
            "/authorized/login/",
            {
                "email": "profile@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        access_token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get("/profiles/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertEqual(data["user"]["email"], "profile@example.com")
        self.assertEqual(data["user"]["firstname"], "Pro")
        self.assertIn("settings", data)
        self.assertIn("stats", data)


class _DummyChannelLayer:
    def __init__(self):
        self.messages = []

    async def group_send(self, group_name, payload):
        self.messages.append((group_name, payload))
        await asyncio.sleep(0)


class ProfilePostShareDeleteFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            firstname="Source",
            lastname="Owner",
            password="Password123!",
            dob=date(1990, 1, 1),
            bio="owner bio",
        )
        self.sharer = User.objects.create_user(
            email="sharer@example.com",
            firstname="Share",
            lastname="User",
            password="Password123!",
            dob=date(1991, 1, 1),
            bio="sharer bio",
        )
        self.source_post = ProfilePost.objects.create(
            user=self.owner,
            body="original source post",
        )
        ProfilePostShare.objects.create(post=self.source_post, user=self.sharer)
        self.shared_wrapper_post = ProfilePost.objects.create(
            user=self.sharer,
            body="",
            metadata={
                "is_share_post": True,
                "share_origin_id": str(self.source_post.id),
                "share_origin_snapshot": {
                    "id": str(self.source_post.id),
                    "body": self.source_post.body,
                },
            },
        )

    def _build_consumer(self):
        consumer = ProfilePostConsumer()
        consumer.group_name = "profile_posts_feed"
        consumer.channel_layer = _DummyChannelLayer()
        return consumer

    def test_deleting_shared_wrapper_removes_share_relation_and_decrements_count(self):
        consumer = self._build_consumer()

        async_to_sync(consumer._handle_delete)(
            {
                "action": "delete_post",
                "post_id": str(self.shared_wrapper_post.id),
                "user_id": str(self.sharer.id),
            }
        )

        self.source_post.refresh_from_db()
        self.assertEqual(self.source_post.share_count, 0)
        self.assertFalse(ProfilePostShare.objects.filter(post=self.source_post, user=self.sharer).exists())
        self.assertFalse(ProfilePost.objects.filter(id=self.shared_wrapper_post.id).exists())

        share_messages = [
            payload
            for _, payload in consumer.channel_layer.messages
            if payload.get("type") == "profile.share.message"
        ]
        self.assertTrue(share_messages)
        latest_share_payload = share_messages[-1]["payload"]
        self.assertEqual(latest_share_payload.get("eventType"), "profile_post_unshared")
        self.assertEqual(latest_share_payload.get("postId"), str(self.source_post.id))
        self.assertEqual(latest_share_payload.get("shareCount"), 0)
        self.assertTrue(latest_share_payload.get("deleted"))

    def test_deleting_non_share_post_does_not_remove_existing_share_relation(self):
        consumer = self._build_consumer()
        regular_post = ProfilePost.objects.create(
            user=self.sharer,
            body="normal post",
        )

        async_to_sync(consumer._handle_delete)(
            {
                "action": "delete_post",
                "post_id": str(regular_post.id),
                "user_id": str(self.sharer.id),
            }
        )

        self.source_post.refresh_from_db()
        self.assertEqual(self.source_post.share_count, 1)
        self.assertTrue(ProfilePostShare.objects.filter(post=self.source_post, user=self.sharer).exists())
