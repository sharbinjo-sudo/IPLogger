# IP Logger

This Django project serves a public homepage at `/` and records each visitor's public IP address, user agent, and visit timestamp for legitimate security and analytics purposes. A private dashboard at `/iplogs/` shows the collected records, but only to authenticated Django staff users.

The homepage clearly discloses that public IP addresses are logged. The project does not request camera, microphone, GPS, file, contact, or private-network access, and it does not use browser fingerprinting or WebRTC local-IP discovery.

## Production Push Notes

Before pushing this repository or deploying it publicly:

- Do not commit `.env`, `db.sqlite3`, logs, or any local virtual environment files.
- Rotate any secrets that may already have been exposed in prompts, screenshots, terminal history, or local files.
- Change any temporary admin credentials before production use.
- Set `DJANGO_DEBUG=False` in production.
- Replace the development `DJANGO_SECRET_KEY` with a long random secret stored outside Git.
- Set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to your real production domains.
- Use HTTPS and enable `DJANGO_USE_SECURE_COOKIES=True`.
- If you are behind Nginx, Cloudflare, or another proxy, review `DJANGO_TRUSTED_PROXY_HOPS` carefully before trusting forwarded IP headers.
- Use a managed `DATABASE_URL` on Render instead of the local SQLite file.

## Architecture

- `iplogger/`: Django project configuration, settings, root URLs, ASGI, and WSGI.
- `tracker/`: Visitor model, admin registration, views, reusable IP detection helper, tests, and templates.
- SQLite is used for development by default.
- Authentication uses Django's built-in auth system and password hashing.

## Request Flow

Homepage flow:

```text
Visitor
↓
GET /
↓
Django receives request
↓
Client IP determined
↓
Visitor saved to database
↓
index.html returned
↓
Visitor sees website
```

Dashboard flow:

```text
User
↓
GET /iplogs/
↓
Django authentication
↓
Is user authenticated?
↓
Is user staff?
↓
YES → show visitor records
NO → deny/redirect
```

## Installation on Windows

From the project root:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

If you are preparing for a production deployment rather than local development, avoid using SQLite unless that is a deliberate choice for your hosting environment.

Application URLs:

- Homepage: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
- Private IP dashboard: `http://127.0.0.1:8000/iplogs/`

## Creating the Admin Account Securely

The setup credential supplied in the prompt should be treated as temporary and changed before any real deployment. Credentials that appear in prompts, shell history, screenshots, logs, or source control can be exposed.

### Option 1: Interactive `createsuperuser`

Use Django's built-in command and enter the password interactively so it is never embedded in source code:

```powershell
python manage.py createsuperuser
```

If you want to use the email address as the username with Django's default user model, enter:

- Username: `sharbinjo@gmail.com`
- Email address: `sharbinjo@gmail.com`

Then type the password interactively when prompted.

### Option 2: Environment-based bootstrap command

Set environment variables in your shell or `.env`, then run:

```powershell
python manage.py bootstrap_admin
```

Required variables:

- `DJANGO_ADMIN_EMAIL`
- `DJANGO_ADMIN_PASSWORD`

The command creates or updates a staff superuser using the email value as the Django username. It does not print the password.

Important:
If you already created a superuser manually, this project does not remove or alter unrelated existing superusers unless you explicitly run the bootstrap command against the configured account.

## Database and Models

The `Visitor` model stores:

- `ip_address` using `GenericIPAddressField`
- `user_agent` using `TextField`
- `visited_at` using `DateTimeField(auto_now_add=True)`

Indexes are added for `visited_at` and `ip_address` to support dashboard sorting and filtering.

## Access Control

- `/iplogs/` requires an authenticated user.
- Anonymous users are redirected to `/admin/login/`.
- Authenticated non-staff users receive HTTP 403.
- Authenticated staff users can view the dashboard.
- Django admin is also protected by built-in authentication.

## Testing

Run the test suite with:

```powershell
python manage.py test
```

The tests cover:

- Homepage availability
- Visitor record creation
- Local IP storage
- Anonymous access redirect for `/iplogs/`
- Authenticated non-staff denial for `/iplogs/`
- Staff access for `/iplogs/`
- Pagination
- Dashboard statistics
- IP search/filtering

## Deployment Notes

Typical production stack:

- Gunicorn as the WSGI server
- Nginx as the reverse proxy
- HTTPS termination at Nginx or your load balancer
- Environment variables for secrets and host configuration
- `collectstatic` for static files when you add external static assets

## Render Deployment

This project is now prepared for Render with:

- `render.yaml` for a Blueprint deployment
- `build.sh` for migrations and static collection during build
- `gunicorn` as the process Render runs
- `whitenoise` for serving collected static files
- `dj-database-url` so Render PostgreSQL can be configured from `DATABASE_URL`

### Render environment variables

Use these values in Render:

- `DJANGO_DEBUG=False`
- `DJANGO_USE_SECURE_COOKIES=True`
- `DJANGO_TRUSTED_PROXY_HOPS=1`
- `DJANGO_ALLOWED_HOSTS=your-service-name.onrender.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-service-name.onrender.com`
- `DJANGO_SECRET_KEY` as a generated secret
- `DATABASE_URL` from your Render PostgreSQL database

### Render deploy steps

1. Push this repo to GitHub.
2. Create a new Render Blueprint from the repository, or create a web service manually.
3. If using the included `render.yaml`, let Render provision both the web service and PostgreSQL database.
4. Confirm the final Render domain and keep `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` aligned with it.
5. After deploy, create or verify your staff account without deleting existing superusers.

### Manual Render commands

If you configure the Render web service by hand:

- Build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
- Start command: `gunicorn iplogger.wsgi:application`

### Render database note

Render's filesystem is not suitable for durable SQLite production storage. This project now reads `DATABASE_URL`, so a managed Render PostgreSQL database should be used in production.

### Suggested production workflow

1. Create a fresh `.env` on the server with production-only values.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run `python manage.py migrate`.
4. Create or verify your staff/superuser account securely.
5. Run `python manage.py collectstatic`.
6. Serve Django through Gunicorn behind Nginx.
7. Enable HTTPS and secure cookies.
8. Confirm `/iplogs/` is only accessible to authenticated staff users.

Example high-level flow:

1. Nginx accepts HTTPS traffic.
2. Nginx forwards requests to Gunicorn.
3. Gunicorn serves the Django app.
4. Django logs the request IP according to the trusted proxy configuration.

### Example environment settings

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
DJANGO_USE_SECURE_COOKIES=True
DJANGO_TRUSTED_PROXY_HOPS=1
```

### Gunicorn example

```powershell
gunicorn iplogger.wsgi:application --bind 127.0.0.1:8001
```

On Linux servers you would typically run Gunicorn through `systemd` or a process manager rather than from an interactive shell.

### Reverse proxy and IP handling

When Django sits behind Nginx, Cloudflare, or a load balancer, the IP visible in `REMOTE_ADDR` may be the proxy rather than the original client. This project defaults to `REMOTE_ADDR` and only consults forwarding headers when you explicitly configure trusted proxy hops.

Important security points:

- Do not blindly trust `X-Forwarded-For` from arbitrary clients.
- Only trust forwarding headers when your app is behind a proxy you control or explicitly trust.
- With multiple proxy layers, configure the correct number of trusted hops.
- Cloudflare and other CDNs may supply vendor-specific headers, but you should only honor them after validating your proxy chain design.

In this project, `DJANGO_TRUSTED_PROXY_HOPS` controls whether the app inspects `X-Forwarded-For`. If it is `0`, only `REMOTE_ADDR` is used. If it is greater than `0`, the helper selects the appropriate address from the forwarded chain based on the configured hop count. This is safer than always trusting the left-most or right-most value without context, but you should still validate your infrastructure carefully in production.

## Security Checklist

- `SECRET_KEY` comes from environment variables.
- `DEBUG` is environment-driven.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are configurable.
- Django security middleware is enabled.
- Clickjacking protection is enabled through `XFrameOptionsMiddleware`.
- CSRF middleware is enabled.
- Secure cookies can be enabled with `DJANGO_USE_SECURE_COOKIES=True` for HTTPS deployments.
- Password hashing uses Django's built-in secure hashers.
- `/iplogs/` is protected by authentication and a staff authorization check.
- `.gitignore` excludes local secrets, database files, caches, logs, and build artifacts from normal commits.

## Privacy Notes

The homepage discloses IP logging. The application intentionally avoids collecting unnecessary personal data such as GPS, camera, microphone, contacts, local files, passwords, fingerprinting signals, or private/local IP addresses. If you deploy this publicly, review applicable privacy, retention, and disclosure requirements for your jurisdiction and audience.
