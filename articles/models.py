from django.db import models
from user.models import User

def article_img_path(instance, filename):
    return "articles/{0}".format(filename)

def avatar_img_path(instance, filename):
    return "avatar_author/{0}".format(filename)

class Articles(models.Model):
    image1x1 = models.ImageField(upload_to=article_img_path, null=True, blank=True)
    image4x3 = models.ImageField(upload_to=article_img_path, null=True, blank=True)
    image16x9 = models.ImageField(upload_to=article_img_path, null=True, blank=True)
    title = models.CharField(max_length=200, null=False, blank=False)
    altImage = models.CharField(max_length=200, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, null=False, blank=False)
    briefsummary = models.TextField(null=False, blank=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    badgeColor = models.CharField(max_length=200, null=True, blank=True)
    featuredType = models.CharField(max_length=200, null=True, blank=True)
    videoLink = models.CharField(max_length=300, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.title
