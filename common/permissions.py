def can_access_user_profile(*, actor_id: int, target_user_id: int, is_staff: bool = False) -> bool:
    if is_staff:
        return True
    return actor_id == target_user_id


def can_access_conversation(
    *,
    actor_id: int,
    sender_id: int,
    receiver_id: int,
    is_staff: bool = False,
) -> bool:
    if is_staff:
        return True
    return actor_id in {sender_id, receiver_id}
