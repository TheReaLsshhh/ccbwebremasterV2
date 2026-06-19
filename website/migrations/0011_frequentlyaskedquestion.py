from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0010_facultystaffsection"),
    ]

    operations = [
        migrations.CreateModel(
            name="FrequentlyAskedQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("question", models.CharField(max_length=255)),
                ("answer", models.TextField()),
                (
                    "layout",
                    models.CharField(
                        choices=[
                            ("home", "Home"),
                            ("academics", "Academics"),
                            ("admissions", "Admissions"),
                            ("news", "News"),
                            ("downloads", "Downloads"),
                            ("students", "Students"),
                            ("faculty", "Faculty"),
                            ("about", "About"),
                            ("contact", "Contact"),
                        ],
                        help_text="Choose the public page where this FAQ should appear.",
                        max_length=30,
                        verbose_name="Layout page",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("published", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Frequently asked question",
                "verbose_name_plural": "Frequently asked questions",
                "ordering": ["layout", "sort_order", "question"],
            },
        ),
    ]
