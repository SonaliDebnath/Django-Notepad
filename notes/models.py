import uuid
from django.db import models
from django.contrib.auth.models import User


class Note(models.Model):
    COLOR_CHOICES = [
        ('blue', 'Blue'),
        ('purple', 'Purple'),
        ('cyan', 'Cyan'),
        ('pink', 'Pink'),
        ('green', 'Green'),
        ('orange', 'Orange'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes', null=True, blank=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    color_tag = models.CharField(max_length=10, choices=COLOR_CHOICES, default='blue')
    pinned = models.BooleanField(default=False)
    share_token = models.UUIDField(null=True, blank=True, unique=True)
    is_shared = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def word_count(self):
        return len(self.body.split())
