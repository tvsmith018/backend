from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

def avatar_img_path(instance, filename):
    return "avatar_author/{0}".format(filename)

class UsersManager(BaseUserManager):

    def create_user(self, email, firstname, lastname, password, dob, bio, **extra_fields):
        if not email:
            raise ValueError(_("The email must be set"))
        
        email = self.normalize_email(email)
        user = self.model(email=email, firstname=firstname, lastname=lastname, dob=dob, bio=bio, **extra_fields)
        user.set_password(password)
        user.save()
        return user
    
    def create_superuser(self, email, firstname, lastname, password, dob, bio, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, firstname, lastname, password, dob, bio, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email adress"), unique=True)
    firstname = models.CharField(max_length=100, blank=False, null=False)
    lastname = models.CharField(max_length=100, blank=False, null=False)
    bio = models.TextField(null=False, blank=False)
    dob = models.DateField(null=False, blank=False)
    avatar = models.ImageField(upload_to=avatar_img_path)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["firstname","lastname", "bio", "dob"]

    objects = UsersManager()

    def __str__(self):
        return self.firstname + " " + self.lastname