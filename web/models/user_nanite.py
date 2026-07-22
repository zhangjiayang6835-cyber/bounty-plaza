from django.db import models
from django.contrib.auth import get_user_model
from .nanite import NaniteType, NaniteProgram

User = get_user_model()

class UserNanite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nanite_type = models.ForeignKey(NaniteType, on_delete=models.CASCADE)
    cloud_id = models.IntegerField(default=1)
    safety_threshold = models.IntegerField(default=50)
    research_points = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s {self.nanite_type.name}"

class UserNaniteProgram(models.Model):
    user_nanite = models.ForeignKey(UserNanite, on_delete=models.CASCADE)
    program = models.ForeignKey(NaniteProgram, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_nanite.user.username}'s {self.program.name} program"