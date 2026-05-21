from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0004_delete_aboutbranch"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="pagecontent",
            options={"ordering": ["page", "created_at", "id"]},
        ),
        migrations.AlterField(
            model_name="pagecontent",
            name="page",
            field=models.CharField(
                choices=[
                    ("home", "Home"),
                    ("academics", "Academics"),
                    ("admissions", "Admissions"),
                    ("students", "Students"),
                    ("faculty", "Faculty"),
                    ("about", "About"),
                    ("contact", "Contact"),
                ],
                max_length=30,
            ),
        ),
    ]
