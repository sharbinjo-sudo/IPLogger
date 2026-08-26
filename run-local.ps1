$env:DJANGO_DEBUG = "True"
$env:DJANGO_FORCE_HTTPS = "False"
$env:DJANGO_USE_SECURE_COOKIES = "False"
$env:DJANGO_USE_WHITENOISE = "False"

python manage.py runserver 127.0.0.1:8010
