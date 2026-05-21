# City College of Bayawan Website

A Django-powered public website and admin-managed content system for **City College of Bayawan**.

## Features

- Public-facing pages for Home, Academics, Admissions, Services, News, Downloads, Students, Faculty, About, and Contact
- Django Admin for managing page copy, downloads, announcements, faculty/staff entries, services, and contact details
- File uploads for brochures, forms, and downloadable resources
- Contact form with map embed support
- Deployment-ready settings for local development, Render, and Vercel

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

After creating a superuser, log in to `/admin/` and manage:

- `Site settings`
- `Page contents`
- `Academic programs`
- `Admission requirements`
- `Services`
- `News and events`
- `Downloads`
- `Student resources`
- `Faculty and staff`
- `Contact inquiries`

## Deployment Notes

Recommended production stack for this project:

- Render: Django backend and PostgreSQL database
- Cloudinary: uploaded images and downloadable files
- Brevo: outgoing email for contact verification and office notifications
- Vercel: only use for a separated frontend later; this Django template app can run fully on Render

### Render

- Create a new Web Service
- Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start command: `gunicorn ccbwebsite.wsgi:application`
- Add `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`
- Add `CLOUDINARY_URL` so uploaded files persist outside the Render filesystem
- Add Brevo SMTP values:
  - `EMAIL_HOST=smtp-relay.brevo.com`
  - `EMAIL_PORT=587`
  - `EMAIL_USE_TLS=True`
  - `EMAIL_HOST_USER`
  - `EMAIL_HOST_PASSWORD`
  - `DEFAULT_FROM_EMAIL`
  - `CONTACT_INQUIRY_RECIPIENT=citycollegeofbayawan@gmail.com`

The contact form saves an inquiry first, sends a verification link to the visitor, and emails the office only after the visitor verifies their email address.

### Vercel

- Vercel is not recommended for this current Django-template version because uploaded media and migrations are easier to manage on Render.
- Use Vercel later if the public frontend is split into a separate React/Next.js app that calls the Render backend.

## Important Note

This scaffold includes the Django models and app structure, but because this workspace did not have a working Python runtime available in the shell, migrations were not executed here. Run `python manage.py makemigrations` and `python manage.py migrate` on your machine once Python is available.
