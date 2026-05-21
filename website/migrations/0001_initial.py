from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AcademicProgram",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("award", models.CharField(blank=True, max_length=200)),
                ("description", models.TextField()),
                ("brochure_file", models.FileField(blank=True, null=True, upload_to="academics/")),
                ("is_featured", models.BooleanField(default=False)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AdmissionRequirement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("document_file", models.FileField(blank=True, null=True, upload_to="admissions/")),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "title"]},
        ),
        migrations.CreateModel(
            name="ContactInquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("is_resolved", models.BooleanField(default=False)),
            ],
            options={"verbose_name_plural": "Contact inquiries", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DownloadItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.CharField(choices=[("academic", "Academic"), ("form", "Form"), ("policy", "Policy"), ("announcement", "Announcement")], default="form", max_length=30)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("file", models.FileField(upload_to="downloads/")),
                ("is_featured", models.BooleanField(default=False)),
            ],
            options={"ordering": ["category", "title"]},
        ),
        migrations.CreateModel(
            name="FacultyStaffEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("role", models.CharField(max_length=200)),
                ("department", models.CharField(blank=True, max_length=200)),
                ("bio", models.TextField(blank=True)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("profile_image", models.ImageField(blank=True, null=True, upload_to="faculty/")),
                ("is_leadership", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Faculty or staff entry",
                "verbose_name_plural": "Faculty and staff",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="NewsEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("summary", models.TextField()),
                ("content", models.TextField(blank=True)),
                ("event_date", models.DateField(default=django.utils.timezone.now)),
                ("location", models.CharField(blank=True, max_length=200)),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="news/")),
                ("attachment", models.FileField(blank=True, null=True, upload_to="news/")),
                ("is_featured", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                "verbose_name": "News or event",
                "verbose_name_plural": "News and events",
                "ordering": ["-published_at"],
            },
        ),
        migrations.CreateModel(
            name="PageContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("page", models.CharField(choices=[("home", "Home"), ("academics", "Academics"), ("admissions", "Admissions"), ("services", "Services"), ("students", "Students"), ("faculty", "Faculty"), ("about", "About"), ("contact", "Contact")], max_length=30, unique=True)),
                ("hero_title", models.CharField(max_length=200)),
                ("hero_text", models.TextField(blank=True)),
                ("body_title", models.CharField(blank=True, max_length=200)),
                ("body_text", models.TextField(blank=True)),
                ("cta_text", models.CharField(blank=True, max_length=80)),
                ("cta_url", models.CharField(blank=True, max_length=255)),
                ("banner_image", models.ImageField(blank=True, null=True, upload_to="pages/")),
                ("published", models.BooleanField(default=True)),
            ],
            options={"ordering": ["page"]},
        ),
        migrations.CreateModel(
            name="ServiceItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("audience", models.CharField(choices=[("general", "General"), ("student", "Students"), ("faculty", "Faculty & Staff")], default="general", max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("link_url", models.URLField(blank=True)),
                ("attachment", models.FileField(blank=True, null=True, upload_to="services/")),
            ],
            options={"ordering": ["audience", "title"]},
        ),
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("site_name", models.CharField(default="City College of Bayawan", max_length=200)),
                ("tagline", models.CharField(blank=True, default="Empowering learners. Building futures.", max_length=255)),
                ("hero_notice", models.CharField(blank=True, default="Admissions are open for the upcoming term.", max_length=255)),
                ("primary_email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("office_hours", models.CharField(blank=True, max_length=255)),
                ("facebook_url", models.URLField(blank=True)),
                ("map_embed_url", models.URLField(blank=True, help_text="Use a Google Maps embed URL for the Contact page iframe.")),
                ("footer_text", models.CharField(blank=True, default="City College of Bayawan", max_length=255)),
            ],
            options={"verbose_name_plural": "Site settings"},
        ),
        migrations.CreateModel(
            name="StudentResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("link_url", models.URLField(blank=True)),
                ("attachment", models.FileField(blank=True, null=True, upload_to="students/")),
            ],
            options={"ordering": ["title"]},
        ),
    ]
