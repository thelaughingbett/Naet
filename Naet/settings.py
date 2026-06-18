import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=Csv()
)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'django_celery_beat',

    "base.apps.BaseConfig"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware'
]

ROOT_URLCONF = 'Naet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Naet.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    ('base', BASE_DIR / 'base/static')
]

MEDIA_ROOT = BASE_DIR / 'user-upload/'
MEDIA_URL = 'media/'

AUTH_USER_MODEL = 'base.User'


# Ensure this only runs in local development
DEBUG = True

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = '127.0.0.1'       # Use 'localhost' or 'mailpit' if using Docker networks
    EMAIL_PORT = 1025              # Mailpit's default SMTP port
    EMAIL_USE_TLS = False          # Mailpit does not use encryption by default
    EMAIL_USE_SSL = False
    EMAIL_HOST_USER = ''           # No authentication needed
    EMAIL_HOST_PASSWORD = ''
    DEFAULT_FROM_EMAIL = 'testing@yourdomain.local'

# 1. Direct django-sms to use its built-in official Twilio wrapper
SMS_BACKEND = 'sms.backends.twilio.SmsBackend'

# 2. Add credentials (Use your real ones in production, dummy ones work for MessagePit)
TWILIO_ACCOUNT_SID = os.environ.get(
    'TWILIO_ACCOUNT_SID', 'AC_prod_or_local_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'prod_or_local_token')
DEFAULT_FROM_SMS = os.environ.get('TWILIO_NUMBER', '+15550001111')

# 3. CRITICAL INTERCEPT FOR NATIVE MESSAGEPIT
if DEBUG:
    # Forces the official Twilio SDK client to talk to your native local port
    os.environ['TWILIO_BASE_URL'] = 'http://127.0.0'

DEFAULT_FROM_SMS = '+15550001111'
SMS_SENDER_ID = '+15550001111'

# M-Pesa (Daraja API)
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', '')
MPESA_PASSKEY = config('MPESA_PASSKEY', '')
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL', '')

# Bank webhook
BANK_WEBHOOK_SECRET = config('BANK_WEBHOOK_SECRET', '')

# settings.py

SCHOOL_EMAIL_DOMAIN = 'institute.ac.ke'
SCHOOL_EMAIL_STRATEGY = 'default'

# or point to a custom function in your codebase
# SCHOOL_EMAIL_STRATEGY = 'base.utils.my_custom_strategy'


# # Optional: Route user sessions to Redis for an extra speed boost
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"

# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
#         'LOCATION': BASE_DIR / 'cache',
#     }
# }

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # Connects to the port exposed by Docker onto your local machine
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "local_django_dev",
        "TIMEOUT": 300,  # Expires keys automatically after 5 minutes

    }
}


# Celery Broker settings (Points to Dockerized Redis)
CELERY_BROKER_URL = "redis://127.0.0.1:6379/2"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/2"

# Optional configuration optimization settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'


# Switch Celery Beat to look inside the SQL Database for schedules
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

CELERY_BEAT_SCHEDULE = {
    'sync-news-feeds': {
        'task':     'base.modules.news.tasks.sync_news_feeds',
        'schedule': 60 * 30,   # every 30 minutes
    },
    'sync-event-feeds': {
        'task':     'events.tasks.sync_event_feeds',
        'schedule': 60 * 30,   # every 30 minutes
    },
}


# Modules Config
TIMETABLE_MODULE_CONFIG = {
    'DAYS':  (
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ),
    'SLOTS': (
        ('08:00-10:00', '1st Slot (08:00 - 10:00)'),
        ('10:00-12:00', '2nd Slot (10:00 - 12:00)'),
        ('12:00-13:00', '3rd Slot (12:00 - 13:00)'),
        ('13:00-15:00', '4th Slot (13:00 - 15:00)'),
        ('15:00-17:00', '5th Slot (15:00 - 17:00)'),
        ('17:00-19:00', '6th Slot (17:00 - 19:00)'),
    ),
    'EXAM_SLOTS':  [
        ('08:00-11:00', '1st Slot (08:00 – 11:00)'),
        ('11:00-14:00', '2nd Slot (11:00 – 14:00)'),
        ('14:00-17:00', '3rd Slot (14:00 – 17:00)'),
        ('17:00-20:00', '4th Slot (17:00 – 20:00)'),
        ('20:00-23:00', '5th Slot (20:00 – 23:00)'),
    ],
    'STRATEGY': 'base.modules.timetabling.weekly_schedule.strategies.examples.GreedyStrategy.GreedyStrategy',
    'EXAM_STRATEGY': 'base.modules.timetabling.exam_timetable.strategies.examples.greedy.GreedyExamGenerator'

}

RESULTS_MODULE_CONFIG = {


    # default — Excel import
    "STRATEGY": 'base.modules.results.strategies.excel.ExcelResultsStrategy',

    # swap to LMS push (used by the API view, not the management command)
    # RESULTS_STRATEGY = 'base.modules.results.strategies.lms.LMSPushStrategy'

    # Excel-specific settings
    'EXCEL_SHEET': 0,  # first sheet
    'EXCEL_HEADER_ROW': 1   # headers on row 1, data from row 2
}

MESSAGEPIT_WEBHOOK_URL = 'http://localhost:8300'


STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
