from cloudinary_storage.storage import MediaCloudinaryStorage


class CCBMediaCloudinaryStorage(MediaCloudinaryStorage):
    """Cloudinary media storage with safer existence checks for Django admin."""

    def exists(self, name):
        try:
            return super().exists(name)
        except Exception:
            # Avoid admin 500s when Cloudinary is unreachable or returns an error.
            return True
