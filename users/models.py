from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .manager import UsersManager
from cloudinary.models import CloudinaryField


class Users(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email adress"), unique=True)
    firstname = models.CharField(max_length=100, blank=False, null=False)
    lastname = models.CharField(max_length=100, blank=False, null=False)
    bio = models.TextField(null=False, blank=False)
    dob = models.DateField(null=False, blank=False)
    avatar = CloudinaryField(
        "avatar",
        null=True,         # Allows NULL in the database
        blank=True,        # Allows the field to be empty in forms/admin
        eager=[
            {'width': 100, 'height': 100, 'crop': 'thumb', 'gravity': 'face'}
        ],
        folder=f'users_avatar'
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["firstname", "lastname", "bio", "dob"]

    objects = UsersManager()

    def __str__(self):
        return self.firstname + " " + self.lastname
    
    @property
    def avatar_url(self):
        if not self.avatar:
            return None
        if isinstance(self.avatar, str):
            return self.avatar
        return self.avatar.url
