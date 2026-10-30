# Public website redesign

The public site uses the existing Django templates and deployment stack. The shared institutional design is in `static/css/institutional.css`; the original stylesheet still supplies contact, directory, and news-modal components.

## Visitor features

- Site search: `/search/?q=...`, with paginated results from published programs, news, downloads, student resources, faculty, and offices.
- Programs: searchable listing and permanent `/academics/<id>/` detail pages, including optional department, duration, career pathways, and brochure.
- News: keyword search, permanent `/news/<id>/` stories, and support for existing `/news/?open=<id>` links. A news item must be published and its publication date must have arrived to appear publicly.
- Downloads: keyword and category filters, with pagination preserving both selections.
- Admissions: ordered admission steps and a requirements checklist. Checkboxes are temporary page state; they do not save or submit an application.
- Students: searchable resources and editable campus service links.
- Faculty: name, role, and biography search plus department filtering.
- Contact: searchable office directory alongside the existing inquiry form and map.

## Content management

Use the existing Django admin. Existing records remain published after migration.

- **Site settings**: edit the institutional mantra shown beneath the header name and in the footer, the tagline, college contact details, and map.
- **Home slideshow images**: upload one image or use **Upload multiple images**, preview slides, edit order and visibility in the list, and use bulk publish/unpublish actions.
- **Academic programs**: edit descriptions, department, duration, career pathways, brochure, featured status, and public visibility.
- **News and events**: use Published and Published at to control release. Future-dated stories are hidden until their date arrives. Featured news is prioritized on the homepage.
- **Admission steps**: add ordered instructions and optional official external links. Until steps are added, the admissions page shows general guidance to explore programs, prepare requirements, and contact the college.
- **Campus services**: manage the links in the Services menu and Students page. Existing service links serve as a fallback until the first service record is created. After that, only published service records appear; hiding all records hides all service links.
- **Campus offices**: publish office descriptions, contact details, location, and hours for the Contact directory.
- **Page contents**: edit introductory headings and inner-page banners. Sort order chooses the primary introduction and orders About sections. Home background images have a separate slideshow editor.
- **Downloads, admission requirements, student resources, faculty entries**: each now has a Published control.
- **FAQs**: answers containing placeholder `lorem ipsum` text are excluded publicly. Replace those answers with official content before publishing them.

Use genuine CCB photography and verified institutional copy. No programs, admission deadlines, official mission statements, or office contact details were invented. Existing page copy is preserved; review production content separately, including generic headings or old editorial notes in stored page content.

## Local review and deployment

1. Back up the target database before deployment. Local work created `db.before-public-redesign.sqlite3` if a local database was present.
2. Install the existing requirements and run `python manage.py migrate` (including migrations 0012 and 0013).
3. Run `python manage.py collectstatic --noinput`.
4. Review every public page, mobile navigation, light/dark themes, searches, downloads, and an inquiry submission in a browser.
5. Deploy through the existing Render workflow. Production continues using PostgreSQL, Cloudinary uploads, and existing email configuration. No production deployment was performed during this work.

The service-worker cache version was incremented and document requests now prefer the network, so returning visitors receive current content. Offline requests can show previously viewed public pages. Normal public HTTP caching is limited to five minutes without a stale-while-revalidate extension.

## Verification

Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test website`, and `python manage.py audit_download_files`.

The test suite covers public rendering, draft and scheduled-news visibility, program and news details, search escaping, directory filtering, filtered pagination, editable admissions/services/offices, and sitemap visibility. Two old favicon assertions were updated to match the already-existing direct ICO response and multi-size icon markup.

## Homepage slideshow and parallax

Open **Home slideshow images** in Admin, then choose **Upload multiple images**. Select up to 20 JPG, PNG, or WebP files at a time (10 MB each). The complete batch is validated before saving. Images append after existing slides; each title, image, order, and Published flag can be changed afterward. Uncheck **Publish these images immediately** to upload drafts. Use Save after changing order or visibility in the list.

Migration 0013 copies existing Home banner references into the slideshow collection, preserving their ordering and publication flags without re-uploading or removing files. Edit the Home heading separately in **Page contents**. Adding a new slide does not add another page heading. All published slides are included, and a single published slide stays static. When no slideshow images have been configured, the existing campus/welcome images are used. If every configured slide is hidden, only the static campus fallback appears.

Backgrounds crossfade every eight seconds with a 1.2-second fade between images. The slideshow is fully automatic with no on-page controls, and continues during hover and keyboard focus. Autoplay pauses in hidden tabs and while the hero is outside the viewport. Broken images are skipped. Without JavaScript, the first image stays visible.

Page banners and the Home hero have subtle scroll parallax on desktop. Small screens use static positioning. Reduced-motion preferences disable parallax, crossfades, and autoplay so visitors see a static image.

## Updated Admin workspace

The Admin home page provides permission-aware shortcuts to slideshow images, page content, academic programs, admissions steps, news, services, offices, and site settings. The existing full model list and security controls remain available. Content lists support bulk Publish and Unpublish actions. News still honors its publication date even after a bulk Publish action.

The slideshow upload screen requires staff access, completed admin PIN verification, the HomeSlide add permission, and CSRF validation. Invalid batches create no records. Failed saves roll back records and attempt to remove newly uploaded files. Grant editors the new Home slideshow image permissions as appropriate; superusers receive access automatically. Uploaded images continue using the deployment's configured image storage (Cloudinary in production).
