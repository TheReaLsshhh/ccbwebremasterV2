from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0002_remove_service_items"),
    ]

    operations = [
        migrations.CreateModel(
            name="AboutBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "About branch",
                "verbose_name_plural": "About branches",
                "ordering": ["sort_order", "title"],
            },
        ),
    ]
