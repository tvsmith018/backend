import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from profiles.models import ProfileFollow, ProfileImage
from profiles.services.profile_image_service import ProfileImageService
from schemas.nodes.profilenode import ProfileImageNode
from users.models import Users

AUTH_REQUIRED_MESSAGE = "Authentication required."


def resolve_profile_viewer_user_id(info):
    request = getattr(info, "context", None)
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user.id

    raw_viewer_user_id = None
    if request is not None:
        raw_viewer_user_id = (
            request.headers.get("x-profile-viewer-id")
            if hasattr(request, "headers")
            else None
        ) or request.META.get("HTTP_X_PROFILE_VIEWER_ID")
    if raw_viewer_user_id:
        try:
            return int(raw_viewer_user_id)
        except (TypeError, ValueError):
            return None
    return None


class UnfollowUser(graphene.Mutation):
    ok = graphene.Boolean(required=True)
    deleted_count = graphene.Int(required=True)

    class Arguments:
        following_user_id = graphene.Decimal(required=True)

    @classmethod
    def mutate(cls, root, info, following_user_id):
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            raise GraphQLError(AUTH_REQUIRED_MESSAGE)

        try:
            target_user_id = int(following_user_id)
        except (TypeError, ValueError):
            raise GraphQLError("Invalid following_user_id.")

        if viewer_user_id == target_user_id:
            return cls(ok=False, deleted_count=0)

        queryset = ProfileFollow.objects.filter(
            follower_id=viewer_user_id,
            following_id=target_user_id,
            status=ProfileFollow.Status.ACTIVE,
        )
        deleted_count, _ = queryset.delete()
        return cls(ok=deleted_count > 0, deleted_count=deleted_count)


class ProfilePhotoMutationPayload(graphene.ObjectType):
    ok = graphene.Boolean(required=True)
    image = graphene.Field(ProfileImageNode)
    deleted_image_id = graphene.ID()
    images_count = graphene.Int(required=True)
    avatar_url = graphene.String()
    message = graphene.String()


def parse_profile_image_id(value) -> int:
    raw = str(value or "").strip()
    if raw.isdigit():
        return int(raw)
    try:
        _, decoded = from_global_id(raw)
        return int(decoded)
    except Exception as exc:
        raise GraphQLError("Invalid image id.") from exc


class UploadProfilePhoto(graphene.Mutation):
    Output = ProfilePhotoMutationPayload

    class Arguments:
        caption = graphene.String(required=False)
        image_data = graphene.String(required=True)
        visibility = graphene.String(required=False)

    @classmethod
    def mutate(cls, root, info, image_data, caption="", visibility="public"):
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            raise GraphQLError(AUTH_REQUIRED_MESSAGE)

        visibility_value = (visibility or ProfileImage.Visibility.PUBLIC).lower()
        if visibility_value not in {
            ProfileImage.Visibility.PUBLIC,
            ProfileImage.Visibility.PRIVATE,
        }:
            raise GraphQLError("Invalid visibility value.")

        result = ProfileImageService.upload_photo(
            user_id=viewer_user_id,
            image_data=image_data,
            caption=caption or "",
            visibility=visibility_value,
        )
        return ProfilePhotoMutationPayload(
            ok=True,
            image=result["image"],
            images_count=result["images_count"],
            avatar_url=result.get("avatar_url"),
            message="Profile photo uploaded.",
        )


class SetFeaturedProfilePhoto(graphene.Mutation):
    Output = ProfilePhotoMutationPayload

    class Arguments:
        image_id = graphene.ID(required=True)

    @classmethod
    def mutate(cls, root, info, image_id):
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            raise GraphQLError(AUTH_REQUIRED_MESSAGE)

        parsed_image_id = parse_profile_image_id(image_id)
        result = ProfileImageService.set_featured_photo(
            user_id=viewer_user_id,
            image_id=parsed_image_id,
        )
        return ProfilePhotoMutationPayload(
            ok=True,
            image=result["image"],
            images_count=result["images_count"],
            avatar_url=result.get("avatar_url"),
            message="Featured profile photo updated.",
        )


class ToggleProfilePhotoVisibility(graphene.Mutation):
    Output = ProfilePhotoMutationPayload

    class Arguments:
        image_id = graphene.ID(required=True)

    @classmethod
    def mutate(cls, root, info, image_id):
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            raise GraphQLError(AUTH_REQUIRED_MESSAGE)

        parsed_image_id = parse_profile_image_id(image_id)
        result = ProfileImageService.toggle_visibility(
            user_id=viewer_user_id,
            image_id=parsed_image_id,
        )
        return ProfilePhotoMutationPayload(
            ok=True,
            image=result["image"],
            images_count=result["images_count"],
            message="Profile photo visibility updated.",
        )


class DeleteProfilePhoto(graphene.Mutation):
    Output = ProfilePhotoMutationPayload

    class Arguments:
        image_id = graphene.ID(required=True)

    @classmethod
    def mutate(cls, root, info, image_id):
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            raise GraphQLError(AUTH_REQUIRED_MESSAGE)

        parsed_image_id = parse_profile_image_id(image_id)
        result = ProfileImageService.delete_photo(
            user_id=viewer_user_id,
            image_id=parsed_image_id,
        )
        avatar_url = result.get("avatar_url")
        if avatar_url is None:
            user = Users.objects.filter(pk=viewer_user_id).first()
            avatar_url = user.avatar_url if user else None
        return ProfilePhotoMutationPayload(
            ok=True,
            deleted_image_id=str(result["deleted_id"]),
            images_count=result["images_count"],
            avatar_url=avatar_url,
            message="Profile photo removed.",
        )


class ClearProfileAvatar(graphene.Mutation):
    Output = ProfilePhotoMutationPayload

    @classmethod
    def mutate(cls, root, info):
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            raise GraphQLError(AUTH_REQUIRED_MESSAGE)

        result = ProfileImageService.clear_avatar(user_id=viewer_user_id)
        return ProfilePhotoMutationPayload(
            ok=True,
            images_count=result["images_count"],
            avatar_url=result.get("avatar_url"),
            message="Profile avatar cleared.",
        )


class Mutation(graphene.ObjectType):
    unfollow_user = UnfollowUser.Field()
    upload_profile_photo = UploadProfilePhoto.Field()
    set_featured_profile_photo = SetFeaturedProfilePhoto.Field()
    toggle_profile_photo_visibility = ToggleProfilePhotoVisibility.Field()
    delete_profile_photo = DeleteProfilePhoto.Field()
    clear_profile_avatar = ClearProfileAvatar.Field()
