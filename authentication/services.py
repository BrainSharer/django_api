import datetime
from typing import Any, Dict, Tuple
import requests
from django.db import transaction
from django.core.management.utils import get_random_secret_key
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.utils import get_now
from authentication.models import User
from django.contrib.auth import login

GITHUB_ACCESS_TOKEN_OBTAIN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_INFO_URL = 'https://api.github.com/user'
GITHUB_USER_EMAIL_INFO_URL = 'https://api.github.com/user/emails'

GOOGLE_ID_TOKEN_INFO_URL = 'https://www.googleapis.com/oauth2/v3/tokeninfo'
GOOGLE_ACCESS_TOKEN_OBTAIN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'



def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def user_create(email, password=None, **extra_fields) -> User:
    extra_fields = {
        'is_staff': False,
        'is_superuser': False,
        **extra_fields
    }

    user = User(email=email, **extra_fields)

    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()

    user.full_clean()
    user.save()

    return user


def user_create_superuser(email, password=None, **extra_fields) -> User:
    extra_fields = {
        **extra_fields,
        'is_staff': True,
        'is_superuser': True
    }

    user = user_create(email=email, password=password, **extra_fields)

    return user


def user_record_login(*, user: User) -> User:
    user.last_login = get_now()
    user.save()

    return user


@transaction.atomic
def user_change_secret_key(*, user: User) -> User:
    user.secret_key = get_random_secret_key()
    user.full_clean()
    user.save()

    return user


@transaction.atomic
def user_get_or_create(*, email: str, **extra_data) -> Tuple[User, bool]:
    user = User.objects.filter(email=email).first()

    if user:
        return user, False

    return user_create(email=email, **extra_data), True


def jwt_login(*, response: HttpResponse, user: User, request: HttpRequest) -> HttpResponse:
    refresh_access_cookies(response=response, user=user)
    user_record_login(user=user)
    user.backend = 'allauth.account.auth_backends.AuthenticationBackend'
    login(request, user)
    return response


def refresh_access_cookies(response: HttpResponse, user: User) -> None:
    token = get_tokens_for_user(user)    
    set_cookie_with_token(response, 'access', token['access'])    
    set_cookie_with_token(response, 'id', user.id)
    set_cookie_with_token(response, 'username', user.username)
    if user.lab is not None:
        set_cookie_with_token(response, 'lab', user.lab.lab_name)
    else:
        set_cookie_with_token(response, 'lab', "NA")


##### Github stuff, deprecated as github doesn't work well
def github_get_access_token(*, code: str, redirect_uri: str) -> str:
    """
    See: https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
    params to send to Github:
        client_id:	string	Required. The client ID you received from GitHub for your OAuth App.
        client_secret:	string	Required. The client secret you received from GitHub for your OAuth App.
        code:	string	Required. The code you received as a response to Step 1.
        redirect_uri:	string	The URL in your application where users are sent after authorization.

    Args:
        * (undefined):
        code (str):
        redirect_uri (str):

    Returns:
        str

    """
    data = {
        'client_id': settings.GITHUB_OAUTH2_CLIENT_ID,
        'client_secret': settings.GITHUB_OAUTH2_CLIENT_SECRET,
        'code': code,
        'redirect_uri': redirect_uri
    }

    headers = {'Accept': 'application/json'}
    response = requests.post(GITHUB_ACCESS_TOKEN_OBTAIN_URL, data=data, headers=headers)

    if not response.ok:
        raise ValidationError('Failed to obtain access token from Github.')
    print('response json')
    print(response.json())
    access_token = response.json()['access_token']
    return access_token


def github_get_user_info(*, access_token: str) -> Dict[str, Any]:
    """
    Description of github_get_user_info

    Args:
        * (undefined):
        access_token (str):

    Returns:
        Dict[str, Any]

    """
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get(GITHUB_USER_INFO_URL, headers=headers)

    if not response.ok:
        raise ValidationError('Failed to obtain user info from Github.')

    return response.json()

##### Google stuff
def google_validate_id_token(*, id_token: str) -> bool:
    # Reference: https://developers.google.com/identity/sign-in/web/backend-auth#verify-the-integrity-of-the-id-token
    response = requests.get(
        GOOGLE_ID_TOKEN_INFO_URL,
        params={'id_token': id_token}
    )

    if not response.ok:
        raise ValidationError('id_token is invalid.')

    audience = response.json()['aud']

    if audience != settings.GOOGLE_OAUTH2_CLIENT_ID:
        raise ValidationError('Invalid audience.')

    return True


def google_get_access_token(*, code: str, redirect_uri: str) -> str:
    # Reference: https://developers.google.com/identity/protocols/oauth2/web-server#obtainingaccesstokens
    data = {
        'code': code,
        'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }

    response = requests.post(GOOGLE_ACCESS_TOKEN_OBTAIN_URL, data=data)

    if not response.ok:
        raise ValidationError('Failed to obtain access token from Google.')

    access_token = response.json()['access_token']

    return access_token


def google_get_user_info(*, access_token: str) -> Dict[str, Any]:
    # Reference: https://developers.google.com/identity/protocols/oauth2/web-server#callinganapi
    response = requests.get(
        GOOGLE_USER_INFO_URL,
        params={'access_token': access_token}
    )

    if not response.ok:
        raise ValidationError('Failed to obtain user info from Google.')

    return response.json()

def set_cookie_with_token(response, name, token):
    expires = get_expiry()
    params = {
        'expires': expires,
        'path': '/',
        'secure': False,
        'httponly': False
    }

    response.set_cookie(name, token, **params)

def get_expiry():
    expiry = datetime.datetime.utcnow()
    expiry += datetime.timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES)
    return expiry.strftime('%a, %d-%b-%Y %T GMT')