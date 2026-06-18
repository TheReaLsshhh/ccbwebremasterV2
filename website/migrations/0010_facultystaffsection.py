from django.db import migrations, models
import django.db.models.deletion


def create_default_faculty_sections(apps, schema_editor):
    FacultyStaffSection = apps.get_model("website", "FacultyStaffSection")
    FacultyStaffEntry = apps.get_model("website", "FacultyStaffEntry")

    leadership_section, _created = FacultyStaffSection.objects.get_or_create(
        title="College Leaders",
        defaults={
            "eyebrow_label": "Leadership",
            "layout": "leadership",
            "sort_order": 10,
            "published": True,
        },
    )
    directory_section, _created = FacultyStaffSection.objects.get_or_create(
        title="Faculty and Staff",
        defaults={
            "eyebrow_label": "Directory",
            "layout": "directory",
            "sort_order": 20,
            "published": True,
        },
    )

    FacultyStaffEntry.objects.filter(is_leadership=True, section__isnull=True).update(
        section=leadership_section
    )
    FacultyStaffEntry.objects.filter(is_leadership=False, section__isnull=True).update(
        section=directory_section
    )


def restore_faculty_leadership_flags(apps, schema_editor):
    FacultyStaffEntry = apps.get_model("website", "FacultyStaffEntry")

    for entry in FacultyStaffEntry.objects.select_related("section"):
        entry.is_leadership = bool(entry.section and entry.section.layout == "leadership")
        entry.save(update_fields=["is_leadership"])


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0009_staffsecurityprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="FacultyStaffSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200, unique=True)),
                ("eyebrow_label", models.CharField(default="Directory", max_length=80)),
                (
                    "layout",
                    models.CharField(
                        choices=[("leadership", "Leadership cards"), ("directory", "Directory rows")],
                        default="directory",
                        max_length=20,
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("published", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Faculty or staff section",
                "verbose_name_plural": "Faculty and staff sections",
                "ordering": ["sort_order", "title"],
            },
        ),
        migrations.AddField(
            model_name="facultystaffentry",
            name="section",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="people",
                to="website.facultystaffsection",
            ),
        ),
        migrations.RunPython(create_default_faculty_sections, restore_faculty_leadership_flags),
        migrations.AlterField(
            model_name="facultystaffentry",
            name="section",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="people",
                to="website.facultystaffsection",
            ),
        ),
        migrations.RemoveField(
            model_name="facultystaffentry",
            name="is_leadership",
        ),
        migrations.AlterModelOptions(
            name="facultystaffentry",
            options={
                "ordering": ["section__sort_order", "name"],
                "verbose_name": "Faculty or staff entry",
                "verbose_name_plural": "Faculty and staff",
            },
        ),
    ]
