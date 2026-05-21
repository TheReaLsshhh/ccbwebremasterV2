from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0005_pagecontent_allow_duplicates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="map_embed_url",
            field=models.TextField(
                blank=True,
                help_text="Use a Google Maps embed URL for the Contact page iframe.",
            ),
        ),
    ]
