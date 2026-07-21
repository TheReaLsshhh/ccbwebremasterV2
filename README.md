# City College of Bayawan Website

A Django-powered public website and admin-managed content system for **City College of Bayawan**.

## Features

- Public-facing pages for Home, Academics, Admissions, Services, News, Downloads, Students, Faculty, About, and Contact
- Django Admin for managing page copy, downloads, announcements, faculty/staff entries, services, and contact details
- File uploads for brochures, forms, and downloadable resources
- Contact form with map embed support
- Deployment-ready settings for local development and Render

## Suggested Navigation Labels

The site uses these shortened labels in the main navigation:

- Home
- Academics
- Admissions
- Services
- News
- Downloads
- Students
- Faculty
- About
- Contact

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Content Management

Production admin URL (default): `https://ccbacad.dpdns.org/ccb-office/`

The old `/admin/` path returns **404** on purpose. Bookmark the hidden URL above.

After creating a superuser (see below), manage:

| Admin section | Controls on the public site |
|---------------|-----------------------------|
| **Site settings** | Site name, tagline, contact email/phone, address, Facebook, map embed, footer |
| **Page contents** | Hero title, text, and banner per page (Home, Academics, News, Downloads, etc.) |
| **Academic programs** | Academics page and featured programs on Home |
| **Admission requirements** | Admissions page list and files |
| **News and events** | News page, home carousel (featured items) |
| **Downloads** | Download cards and files |
| **Student resources** | Students page links and attachments |
| **Faculty and staff** | Faculty page (leadership vs directory) |
| **Contact inquiries** | Messages from the contact form (read-only; mark resolved) |

### Admin on Render

1. Open your web service → **Shell**.
2. Create the first admin account:
   ```bash
   python manage.py createsuperuser
   ```
3. Log in at `/ccb-office/` on your production domain (not `/admin/`).
4. On first login, set your **6-digit admin PIN** when prompted.
5. Ensure **`CLOUDINARY_URL`** is set — uploads are stored in Cloudinary, not on the Render disk.

**Admin security enabled:**
- Hidden path: `/ccb-office/` (configurable via `ADMIN_URL`)
- `/admin/` returns 404 to confuse scanners
- **2FA:** password + 6-digit PIN on every login
- **Rate limits:** 2 password attempts and 2 PIN attempts per IP every 15 minutes

**Set or reset a PIN from Render Shell:**
```bash
python manage.py set_admin_pin your_username 482913
```

Optional env vars:
- `ADMIN_URL=ccb-office` (default)
- `ADMIN_LOGIN_RATE_LIMIT_ATTEMPTS=2`
- `ADMIN_PIN_RATE_LIMIT_ATTEMPTS=2`

### Admin cannot save (Add / Edit / Delete does nothing)

If you can open admin but **Save** fails or you are sent back to login, check these on the Render **Environment** tab:

| Variable | Required value (example) |
|----------|---------------------------|
| `ALLOWED_HOSTS` | `ccbwebremasterv2.onrender.com,.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://ccbwebremasterv2.onrender.com,https://*.onrender.com` |
| `DATABASE_URL` | Linked Postgres internal URL (not SQLite) |
| `SECRET_KEY` | Set once; do not change after going live or all sessions reset |
| `CLOUDINARY_URL` | Required before uploading files in admin |

Also confirm your user is a **superuser** (Render Shell: `python manage.py createsuperuser`).

After changing env vars, **Save** and **Manual Deploy**. On save you should see a green success banner; a **403 Forbidden** page usually means `CSRF_TRUSTED_ORIGINS` is wrong or missing.

## Deployment Notes

Production stack (Render only):

- **Render Web Service** — Django app, templates, static files (WhiteNoise)
- **Render PostgreSQL** — database
- **Cloudinary** — uploaded images and downloadable files (required on Render; local disk is not persistent)
- **Brevo** — contact verification and office notification email

The contact form saves an inquiry first, sends a verification link to the visitor, and emails the office only after the visitor verifies their email address.

### Deploy on Render (step by step)

#### 1. Push code

Commit and push this repository to GitHub (or GitLab/Bitbucket). Render deploys from your connected repo.

#### 2. PostgreSQL database

1. In [Render Dashboard](https://dashboard.render.com/), click **New +** → **PostgreSQL**.
2. Create the database and copy the **Internal Database URL** (use this for `DATABASE_URL` on the web service in the same region).

#### 3. Web service

**Option A — Blueprint (recommended if starting fresh)**

1. **New +** → **Blueprint**.
2. Connect this repo; Render reads `render.yaml`.
3. When prompted, set secrets that are marked `sync: false` (`DATABASE_URL`, `CLOUDINARY_URL`, email credentials, etc.).

**Option B — Manual web service (if you already have `ccbwebremasterv2`)**

1. Open your existing **Web Service** → **Settings**.
2. Confirm:
   - **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start command:** `gunicorn ccbwebsite.wsgi:application`
3. **Environment** → update variables (see table below).
4. **Manual Deploy** → **Deploy latest commit** (or push to the connected branch for auto-deploy).

#### 4. Required environment variables

Set these on the Render web service (**Environment** tab):

| Variable | Example / notes |
|----------|-----------------|
| `DEBUG` | `False` |
| `SECRET_KEY` | Long random string (Render can generate one) |
| `DATABASE_URL` | From your Render Postgres service |
| `ALLOWED_HOSTS` | `.onrender.com,your-service.onrender.com` — add your custom domain when ready, e.g. `citycollegeofbayawan.edu.ph,www.citycollegeofbayawan.edu.ph` |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com,https://your-service.onrender.com` — add `https://yourdomain.com,https://www.yourdomain.com` with custom domain |
| `CLOUDINARY_URL` | From Cloudinary dashboard (or separate `CLOUDINARY_*` keys) |
| `EMAIL_HOST` | `smtp-relay.brevo.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | Brevo SMTP login |
| `EMAIL_HOST_PASSWORD` | Brevo SMTP password |
| `DEFAULT_FROM_EMAIL` | `City College of Bayawan <no-reply@citycollegeofbayawan.edu.ph>` |
| `CONTACT_INQUIRY_RECIPIENT` | `citycollegeofbayawan@gmail.com` |

Optional: `ADMIN_URL` (non-default admin path), `TIME_ZONE`, `SECURE_HSTS_PRELOAD`.

**Remove** any Vercel hostname from `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` after you stop using Vercel.

#### 5. Custom domain (public URL)

1. Web service → **Settings** → **Custom Domains** → add `www.yourdomain.com` (and apex if needed).
2. At your DNS provider, add the records Render shows (usually CNAME to `*.onrender.com`).
3. Wait for SSL (**Certificate** shows active).
4. Add the domain(s) to `ALLOWED_HOSTS` and `https://...` entries to `CSRF_TRUSTED_ORIGINS`, then redeploy.

#### 6. Turn off Vercel

1. Point marketing links and PageSpeed tests to your **Render** URL or custom domain (not `*.vercel.app`).
2. In Vercel: remove the project or disconnect the domain so traffic does not proxy to Render anymore.
3. This repo no longer includes `vercel.json`.

#### 7. Verify after deploy

- Open `/` and a few pages under `templates/website/` (downloads, contact, news).
- Run `createsuperuser` in Render Shell if needed; log in to `/admin/`, upload a test image (Cloudinary).
- Submit the contact form and complete email verification.

### Local production check (optional)

```bash
set DEBUG=False
set ALLOWED_HOSTS=127.0.0.1,localhost
set CSRF_TRUSTED_ORIGINS=https://127.0.0.1,https://localhost
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn ccbwebsite.wsgi:application
```

## Important Note

This scaffold includes the Django models and app structure, but because this workspace did not have a working Python runtime available in the shell, migrations were not executed here. Run `python manage.py makemigrations` and `python manage.py migrate` on your machine once Python is available.
