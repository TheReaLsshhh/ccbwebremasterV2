from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageOps


class Command(BaseCommand):
    help = "Build responsive WebP versions of the bundled campus photographs."

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR) / "static" / "images"
        destination = root / "responsive"
        destination.mkdir(exist_ok=True)
        for name in ("ccb", "bg2"):
            with Image.open(root / f"{name}.jpg") as original:
                for width in (480, 960, 1600, 1920):
                    image = ImageOps.exif_transpose(original).convert("RGB")
                    image.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
                    image.save(destination / f"{name}-{width}.webp", "WEBP", quality=90, method=4)
        self.stdout.write(self.style.SUCCESS("Built 8 responsive WebP assets; original images preserved."))
