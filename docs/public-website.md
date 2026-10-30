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

- **Academic programs**: edit descriptions, department, duration, career pathways, brochure, featured status, and public visibility.
- **News and events**: use Published and Published at to control release. Future-dated stories are hidden until their date arrives. Featured news is prioritized on the homepage.
- **Admission steps**: add ordered instructions and optional official external links. Until steps are added, the admissions page shows general guidance to explore programs, prepare requirements, and contact the college.
- **Campus services**: manage the links in the Services menu and Students page. Existing service links serve as a fallback until the first service record is created. After that, only published service records appear; hiding all records hides all service links.
- **Campus offices**: publish office descriptions, contact details, location, and hours for the Contact directory.
- **Page contents**: edit page banners and introductory copy. Sort order chooses the first banner for a page and orders the About sections.
- **Downloads, admission requirements, student resources, faculty entries**: each now has a Published control.
- **FAQs**: answers containing placeholder `lorem ipsum` text are excluded publicly. Replace those answers with official content before publishing them.

Use genuine CCB photography and verified institutional copy. No programs, admission deadlines, official mission statements, or office contact details were invented. Existing page copy is preserved; review production content separately, including generic headings or old editorial notes in stored page content.

## Local review and deployment

1. Back up the target database before deployment. Local work created `db.before-public-redesign.sqlite3` if a local database was present.
2. Install the existing requirements and run `python manage.py migrate` (migration 0012).
3. Run `python manage.py collectstatic --noinput`.
4. Review every public page, mobile navigation, light/dark themes, searches, downloads, and an inquiry submission in a browser.
5. Deploy through the existing Render workflow. Production continues using PostgreSQL, Cloudinary uploads, and existing email configuration. No production deployment was performed during this work.

The service-worker cache version was incremented and document requests now prefer the network, so returning visitors receive current content. Offline requests can show previously viewed public pages. Normal public HTTP caching is limited to five minutes without a stale-while-revalidate extension.

## Verification

Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test website`, and `python manage.py audit_download_files`.

The test suite covers public rendering, draft and scheduled-news visibility, program and news details, search escaping, directory filtering, filtered pagination, editable admissions/services/offices, and sitemap visibility. Two old favicon assertions were updated to match the already-existing direct ICO response and multi-size icon markup.

## Homepage slideshow and parallax

Add published **Page contents** records with Page set to **Home** and a banner image. Sort order determines the slideshow sequence; the first published Home record still supplies the heading and introduction. All published Home banners are included. With one banner, that image stays visible. Existing campus/welcome images are used only when no banners are published.

Backgrounds crossfade every eight seconds with a 1.2-second fade between images. The slideshow is fully automatic with no on-page controls, and continues during hover and keyboard focus. Autoplay pauses in hidden tabs and while the hero is outside the viewport. Broken images are skipped. Without JavaScript, the first image stays visible.

Page banners and the Home hero have subtle scroll parallax on desktop. Small screens use static positioning. Reduced-motion preferences disable parallax, crossfades, and autoplay so visitors see a static image.
