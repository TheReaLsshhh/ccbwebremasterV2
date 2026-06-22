# Project Rules

These rules are for work on the City College of Bayawan website in this repository.

## Project Shape

- This is a Django project for the public City College of Bayawan website and its admin-managed content.
- Main Django project settings live in `ccbwebsite/`.
- The primary app is `website/`.
- Public templates live in `templates/website/`.
- Shared layout lives in `templates/base.html`.
- Site CSS lives in `static/css/site.css`.
- Uploaded media is local in development, but production uploads must use Cloudinary.

## Local Commands

- Prefer the virtualenv Python when available:
  ```powershell
  .\.venv\Scripts\python.exe manage.py check
  ```
- Use this after touching models or migrations:
  ```powershell
  .\.venv\Scripts\python.exe manage.py makemigrations --check
  ```
- Use this when download files or Cloudinary-backed file fields are involved:
  ```powershell
  .\.venv\Scripts\python.exe manage.py audit_download_files
  ```
- Use this before deployment checks that need static assets:
  ```powershell
  .\.venv\Scripts\python.exe manage.py collectstatic --noinput
  ```

## Change Discipline

- Keep changes scoped to the reported problem.
- Do not rewrite broad page structure when a template, record, or asset-path fix is enough.
- Preserve existing Django patterns unless a change clearly needs a new helper or abstraction.
- Do not change unrelated files just because they are nearby.
- If a production-only issue is reported, verify the relevant URL, template, database field, or Cloudinary path before assuming the cause.

## Admin And Security

- The production admin path is intentionally hidden by `ADMIN_URL`; `/admin/` may return 404 on purpose.
- Do not expose secrets, API keys, SMTP credentials, `SECRET_KEY`, or Cloudinary credentials in code, docs, commits, or chat.
- Keep secrets in environment variables on Render or in local `.env` files that are not committed.
- Treat `SECRET_KEY`, `DATABASE_URL`, `CLOUDINARY_URL`, email credentials, and API keys as sensitive.
- Avoid weakening CSRF, allowed-host, admin PIN, or rate-limit behavior to make local testing easier.

## Content And Branding

- Keep public copy institutionally clean and plain.
- The navbar brand is hardcoded in `templates/base.html`; footer and title text may come from site settings.
- For navbar branding, prefer the single-line `City College of Bayawan` lockup and keep the `C`, `C`, and `B` initials highlighted through CSS.
- Do not reintroduce extra location labels such as `Bayawan City` into the navbar unless explicitly requested.

## Downloads And Cloudinary

- On Render, uploaded files and images are expected to live in Cloudinary, not on the Render disk.
- If a download URL returns Cloudinary `NOT_FOUND`, check the stored file record and whether the asset actually exists before changing templates.
- Do not assume a URL-normalization change fixes a missing upload.
- Use `website/management/commands/audit_download_files.py` for download-file diagnosis.
- Prefer a local unavailable message over sending visitors directly to a third-party error page when a file is missing.

## Contact Form

- Local email validation should reject obviously bad addresses, emojis, repeated invalid punctuation, disposable domains, and malformed Gmail or `.edu.ph` addresses.
- Do not block legitimate Gmail or `.edu.ph` addresses because an external verification service is unavailable or inconclusive.
- External API failures should generally be non-blocking unless the API returns an explicit negative verdict.
- Do not paste verification API keys or SMTP credentials into code or conversation.

## Search And Indexing

- For Google Search Console questions, separate these two ideas:
  - Google can access the URL.
  - Google has indexed the URL.
- A sitemap at `/static/sitemap.xml` is acceptable if Search Console can fetch it successfully.
- Do not recommend moving the sitemap to `/sitemap.xml` unless there is a concrete issue with the current submitted sitemap.
- Requesting indexing for the homepage does not guarantee every other page is indexed immediately.

## Deployment Notes

- Production is Render plus PostgreSQL, Cloudinary, and Brevo email.
- After changing Render environment variables, redeploy the web service.
- Keep `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` aligned with the active Render or custom domains.
- Remove old Vercel hostnames once the site no longer uses Vercel.

## Before Finishing Work

- Run the smallest relevant verification command for the change.
- For Django code changes, run `manage.py check`.
- For file-download changes, also run `audit_download_files`.
- State clearly if a verification command could not be run.
