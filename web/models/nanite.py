from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NaniteType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    research_points_required = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class NaniteProgram(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    code = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name