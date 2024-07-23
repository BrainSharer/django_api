import os
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'localsettingsfordocumentationsonotimportant'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'authentication',
    'brain',
    'mouselight',
    'neuroglancer',
    'rest_framework',
    'django_extensions',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_plotly_dash.middleware.BaseMiddleware',
    'django_plotly_dash.middleware.ExternalRedirectionMiddleware',
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

##### django extensions graph models
GRAPH_MODELS = {
  'app_labels': ["brain", "neuroglancer", "mouselight"],
  'group_models': True,
}
AUTH_USER_MODEL = 'authentication.User'
BASE_BACKEND_URL = 'http://localhost:8000'
BASE_FRONTEND_URL = 'http://localhost:4200'
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
DEFAULT_FROM_EMAIL = "drinehart@physics.ucsd.edu"
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
GITHUB_OAUTH2_CLIENT_ID = '3ad4b114f66ffb3b6ed8'
GOOGLE_OAUTH2_CLIENT_ID = '821517150552-71h6bahua9qul09l90veb8g3hii6ed25.apps.googleusercontent.com'
HTTP_HOST = "http://localhost/brainsharer"
INTERNAL_IPS = ['127.0.0.1']
LANGUAGE_CODE = 'en-us'
LOGIN_REDIRECT_URL = BASE_FRONTEND_URL
LOGOUT_REDIRECT_URL = BASE_FRONTEND_URL
MEDIA_ROOT = os.path.join(BASE_DIR, 'share')
MEDIA_URL = '/share/'
NG_URL = "http://localhost/brainsharer/ng"
SILENCED_SYSTEM_CHECKS = ['mysql.E001']
SITE_ID = 2
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'assets'),)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_L10N = True
