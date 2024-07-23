"""
"""

import os
import datetime
from brainsharer.local_settings import SECRET_KEY, DATABASES, GOOGLE_OAUTH2_CLIENT_SECRET, \
    GITHUB_OAUTH2_CLIENT_SECRET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG = False
ALLOWED_HOSTS = ['brainsharer.org', 'www.brainsharer.org', 'localhost']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_plotly_dash.apps.DjangoPlotlyDashConfig',
    'django.contrib.sites',
    'authentication',
    'brain',
    'mouselight',
    'neuroglancer',
    'rest_framework',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'authentication.cookiemiddleware.CookieMiddleware'
]

ROOT_URLCONF = 'brainsharer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR + '/templates/',],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'brainsharer.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
         'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(hours=100),
    'ROTATE_REFRESH_TOKENS': True,
}

AUTH_USER_MODEL = 'authentication.User'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend'
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

BASE_BACKEND_URL = 'https://www.brainsharer.org'
BASE_FRONTEND_URL = 'https://www.brainsharer.org'
CORS_ALLOWED_ORIGINS = ['https://www.brainsharer.org', 'https://brainsharer.org']
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
DEFAULT_FROM_EMAIL = "drinehart@physics.ucsd.edu"
EMAIL_HOST = "smtp.ucsd.edu"
FORCE_SCRIPT_NAME = '/brainsharer/'
#FOR HOSTING IN SUBDIRECTORY
GITHUB_OAUTH2_CLIENT_ID = '3ad4b114f66ffb3b6ed8'
GOOGLE_OAUTH2_CLIENT_ID = '821517150552-71h6bahua9qul09l90veb8g3hii6ed25.apps.googleusercontent.com'
HOST = "brainsharer.org"
INTERNAL_IPS = ['127.0.0.1']
LANGUAGE_CODE = 'en-us'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'share')
MEDIA_URL = '/share/'
NEUROGLANCER_PROD_HOST = "https://www.brainsharer.org/ng"
NG_URL = "https://www.brainsharer.org/ng"
SILENCED_SYSTEM_CHECKS = ['mysql.E001']
SITE_ID = 2
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'assets'),)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
USER_ID = 1
USE_X_FORWARDED_HOST = True
