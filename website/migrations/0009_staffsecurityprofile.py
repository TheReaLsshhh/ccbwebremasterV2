import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("website", "0008_remove_verification_fields_from_contactinquiry"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffSecurityProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pin_hash", models.CharField(blank=True, max_length=128)),
                ("pin_updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="security_profile",
                        to="auth.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Staff security profile",
                "verbose_name_plural": "Staff security profiles",
            },
        ),
    ]
