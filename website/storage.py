from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage


class CCBMediaCloudinaryStorage(MediaCloudinaryStorage):
    """Cloudinary image storage with safe fallbacks for Django admin.

    Prevents 500 errors when:
    - Cloudinary is unreachable
    - A stored file name is empty or in an unexpected format
    - Admin tries to render an image field for a record with no image
    """

    def exists(self, name):
        if not name:
            return False
        try:
            return super().exists(name)
        except Exception:
            return True

    def url(self, name):
        if not name:
            return ""
        try:
            return super().url(name)
        except Exception:
            return ""

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except Exception as exc:
            raise OSError(f"Cloudinary image upload failed: {exc}") from exc

    def delete(self, name):
        if not name:
            return
        try:
            super().delete(name)
        except Exception:
            pass


class CCBRawCloudinaryStorage(RawMediaCloudinaryStorage):
    """Cloudinary raw-file storage for non-image uploads (PDF, Word, Excel).

    Uses Cloudinary's 'raw' resource type so PDFs, Word docs and Excel sheets
    are accepted and can be downloaded directly via a public URL.
    """

    def exists(self, name):
        if not name:
            return False
        try:
            return super().exists(name)
        except Exception:
            return True

    def url(self, name):
        if not name:
            return ""
        try:
            return super().url(name)
        except Exception:
            return ""

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except Exception as exc:
            raise OSError(f"Cloudinary raw upload failed: {exc}") from exc

    def delete(self, name):
        if not name:
            return
        try:
            super().delete(name)
        except Exception:
            pass
