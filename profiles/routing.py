from django.urls import re_path

from profiles.consumer.profilefollow import ProfileFollowConsumer
from profiles.consumer.profilephoto import ProfilePhotoConsumer
from profiles.consumer.profilepost import ProfilePostConsumer
from profiles.consumer.profilesettings import ProfileSettingsConsumer


websocket_urlpatterns = [
    re_path(r"ws/profiles/posts/$", ProfilePostConsumer.as_asgi()),
    re_path(r"ws/profiles/follows/$", ProfileFollowConsumer.as_asgi()),
    re_path(r"ws/profiles/photos/$", ProfilePhotoConsumer.as_asgi()),
    re_path(r"ws/profiles/settings/$", ProfileSettingsConsumer.as_asgi()),
]
