from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0003_aboutbranch"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AboutBranch",
        ),
    ]
