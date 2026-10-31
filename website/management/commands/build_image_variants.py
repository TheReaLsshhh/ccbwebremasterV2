from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageOps


class Command(BaseCommand):
    help = "Build responsive WebP variants for explicitly supplied local photographs."

    def add_arguments(self, parser):
        parser.add_argument("images", nargs="+", help="Photograph filenames inside static/images.")

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR) / "static" / "images"
        destination = root / "responsive"
        destination.mkdir(exist_ok=True)
        for filename in options["images"]:
            source = (root / filename).resolve()
            if source.parent != root.resolve() or not source.is_file():
                from django.core.management.base import CommandError
                raise CommandError("Use an existing photograph filename inside static/images.")
            name = source.stem
            with Image.open(source) as original:
                for width in (480, 960, 1600, 1920):
                    image = ImageOps.exif_transpose(original).convert("RGB")
                    image.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
                    image.save(destination / f"{name}-{width}.webp", "WEBP", quality=90, method=4)
        self.stdout.write(self.style.SUCCESS("Built responsive WebP assets; original images preserved."))
