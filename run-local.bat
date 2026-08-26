@echo off
set DJANGO_DEBUG=True
set DJANGO_FORCE_HTTPS=False
set DJANGO_USE_SECURE_COOKIES=False
set DJANGO_USE_WHITENOISE=False

python manage.py runserver 127.0.0.1:8010
