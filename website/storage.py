from cloudinary_storage.storage import MediaCloudinaryStorage


class CCBMediaCloudinaryStorage(MediaCloudinaryStorage):
    """Cloudinary media storage with safe fallbacks for Django admin operations.

    Prevents 500 errors when:
    - Cloudinary is unreachable
    - A stored file name is empty or in an unexpected format
    - Admin tries to render a file/image field for a record with no file
    """

    def exists(self, name):
        if not name:
            return False
        try:
            return super().exists(name)
        except Exception:
            # Cloudinary unreachable or bad name — assume exists to avoid overwriting.
            return True

    def url(self, name):
        if not name:
            return ""
        try:
            return super().url(name)
        except Exception:
            # Return empty string so admin renders a broken-link gracefully
            # instead of a 500 traceback.
            return ""

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except Exception as exc:
            raise OSError(f"Cloudinary upload failed: {exc}") from exc

    def delete(self, name):
        if not name:
            return
        try:
            super().delete(name)
        except Exception:
            # Swallow delete errors (file may already be gone on Cloudinary).
            pass
