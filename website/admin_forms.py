from django import forms


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return super().clean(None, initial)
        files = data if isinstance(data, (list, tuple)) else [data]
        if len(files) > 20:
            raise forms.ValidationError("Upload up to 20 images at a time.")
        cleaned = []
        for upload in files:
            image = super().clean(upload, initial)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Each image must be 10 MB or smaller.")
            if image.image.format not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError("Use JPG, PNG, or WebP images.")
            cleaned.append(image)
        return cleaned


class HomeSlideUploadForm(forms.Form):
    images = MultipleImageField(
        help_text="Select multiple images at once. JPG, PNG, or WebP; up to 20 images, 10 MB each.",
        widget=MultipleImageInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )
    published = forms.BooleanField(required=False, initial=True, label="Publish these images immediately")
