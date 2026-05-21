import secrets

from django.db import migrations, models


def add_verification_tokens(apps, schema_editor):
    ContactInquiry = apps.get_model("website", "ContactInquiry")
    for inquiry in ContactInquiry.objects.filter(verification_token__isnull=True):
        inquiry.verification_token = secrets.token_urlsafe(32)
        inquiry.save(update_fields=["verification_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0006_alter_sitesettings_map_embed_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="contactinquiry",
            name="verification_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="contactinquiry",
            name="verification_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contactinquiry",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contactinquiry",
            name="notification_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(add_verification_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contactinquiry",
            name="verification_token",
            field=models.CharField(blank=True, max_length=64, unique=True),
        ),
    ]
