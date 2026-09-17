"""Initial database migration for greeting record schema."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration creating GreetingRecord model table."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GreetingRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("recipient", models.CharField(default="World", max_length=100)),
                ("message", models.CharField(max_length=255)),
                ("language", models.CharField(default="en", max_length=10)),
                ("format_type", models.CharField(default="text", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Greeting Record",
                "verbose_name_plural": "Greeting Records",
                "ordering": ["-created_at"],
            },
        ),
    ]
