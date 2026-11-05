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


class PageContentAdminForm(forms.ModelForm):
    class Meta:
        from .models import PageContent
        model = PageContent
        fields = "__all__"

    class Media:
        css = {"all": ("admin/css/banner-image-crop.css",)}
        js = ("admin/js/banner-image-crop.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "banner_image" in self.fields:
            self.fields["banner_image"].widget.attrs["data-current-image"] = (
                self.instance.banner_image.url if self.instance.banner_image else ""
            )
        for prefix, minimum, maximum in (("banner", 240, 640), ("banner_mobile", 200, 480)):
            for suffix, low, high, step in (("position_x", 0, 100, 1), ("position_y", 0, 100, 1), ("zoom", 1, 3, .01), ("height", minimum, maximum, 1)):
                name = f"{prefix}_{suffix}"
                if name in self.fields:
                    self.fields[name].widget.attrs.update({"min": low, "max": high, "step": step, "class": "banner-crop-value"})
