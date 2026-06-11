from django.core.management.base import BaseCommand

from website.models import (
    AcademicProgram,
    AdmissionRequirement,
    DownloadItem,
    StudentResource,
)
from website.views import _cloudinary_download_candidates, _cloudinary_url_is_available


FILE_FIELDS = (
    (AcademicProgram, "brochure_file", "name"),
    (AdmissionRequirement, "document_file", "title"),
    (DownloadItem, "file", "title"),
    (StudentResource, "attachment", "title"),
)


class Command(BaseCommand):
    help = "Check public download file URLs and report missing Cloudinary files."

    def handle(self, *args, **options):
        missing_count = 0
        checked_count = 0

        for model, file_field_name, label_field_name in FILE_FIELDS:
            for instance in model.objects.all():
                file_field = getattr(instance, file_field_name)
                if not file_field:
                    continue

                try:
                    url = file_field.url
                except Exception as exc:
                    missing_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"{model.__name__} #{instance.pk}: cannot build URL for "
                            f"{file_field_name} ({exc})"
                        )
                    )
                    continue

                if "res.cloudinary.com" not in url:
                    continue

                checked_count += 1
                if any(
                    _cloudinary_url_is_available(candidate)
                    for candidate in _cloudinary_download_candidates(url)
                ):
                    continue

                missing_count += 1
                label = getattr(instance, label_field_name)
                self.stdout.write(
                    self.style.ERROR(
                        f"{model.__name__} #{instance.pk} ({label}): missing {file_field_name} "
                        f"-> {file_field.name}"
                    )
                )

        if missing_count:
            self.stdout.write(
                self.style.WARNING(
                    f"Checked {checked_count} Cloudinary files; {missing_count} missing. "
                    "Reupload those files in the admin dashboard."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Checked {checked_count} Cloudinary files; none missing.")
            )
