"""Database models for hello world greetings and audit history."""

from django.db import models


class GreetingRecord(models.Model):
    """Persistent audit log of issued hello world greetings."""

    recipient = models.CharField(max_length=100, default="World")
    message = models.CharField(max_length=255)
    language = models.CharField(max_length=10, default="en")
    format_type = models.CharField(max_length=20, default="text")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        """Model metadata options."""

        ordering = ["-created_at"]
        verbose_name = "Greeting Record"
        verbose_name_plural = "Greeting Records"

    def __str__(self) -> str:
        """Return human-readable representation of greeting record."""
        display = f"GreetingRecord(recipient={self.recipient}, language={self.language})"
        return display
