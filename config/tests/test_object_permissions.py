from django.test import SimpleTestCase

from common.permissions import can_access_conversation, can_access_user_profile


class ObjectPermissionHelperTests(SimpleTestCase):
    def test_profile_permission_allows_owner(self):
        self.assertTrue(can_access_user_profile(actor_id=1, target_user_id=1))

    def test_profile_permission_blocks_non_owner(self):
        self.assertFalse(can_access_user_profile(actor_id=1, target_user_id=2))

    def test_profile_permission_allows_staff_override(self):
        self.assertTrue(can_access_user_profile(actor_id=1, target_user_id=2, is_staff=True))

    def test_conversation_permission_allows_participants(self):
        self.assertTrue(can_access_conversation(actor_id=10, sender_id=10, receiver_id=22))
        self.assertTrue(can_access_conversation(actor_id=22, sender_id=10, receiver_id=22))

    def test_conversation_permission_blocks_non_participant(self):
        self.assertFalse(can_access_conversation(actor_id=7, sender_id=10, receiver_id=22))
