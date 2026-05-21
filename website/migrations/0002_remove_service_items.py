from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ServiceItem",
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
                unique=True,
            ),
        ),
    ]
