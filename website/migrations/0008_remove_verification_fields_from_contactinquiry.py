from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0007_contactinquiry_email_verification"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contactinquiry",
            name="verification_token",
        ),
        migrations.RemoveField(
            model_name="contactinquiry",
            name="verification_sent_at",
        ),
        migrations.RemoveField(
            model_name="contactinquiry",
            name="verified_at",
        ),
        migrations.RemoveField(
            model_name="contactinquiry",
            name="notification_sent_at",
        ),
    ]
