from urllib.parse import urlencode
from rest_framework import serializers
from rest_framework.views import APIView
from django.urls import reverse
from django.conf import settings
from django.shortcuts import redirect

from authentication.mixins import ApiErrorsMixin, PublicApiMixin
from authentication.services import user_get_or_create, \
    jwt_login, github_get_access_token, github_get_user_info, \
        google_get_access_token, google_get_user_info




class GithubLoginApi(PublicApiMixin, ApiErrorsMixin, APIView):
    """
    Description of GithubLoginApi
    sample: access_token=XXX123&scope=repo%2Cgist&token_type=bearer
    Inheritance:
        PublicApiMixin:
        ApiErrorsMixin:
        APIView:

    """
    class InputSerializer(serializers.Serializer):
        code = serializers.CharField(required=False)
        scope = serializers.CharField(required=False)
        token_type = serializers.CharField(required=False)

    def get(self, request, *args, **kwargs):
        input_serializer = self.InputSerializer(data=request.GET)
        input_serializer.is_valid(raise_exception=True)

        validated_data = input_serializer.validated_data

        code = validated_data.get('code')
        scope = validated_data.get('scope')
        token_type = validated_data.get('token_type')
        error = validated_data.get('error')

        login_url = f'{settings.BASE_FRONTEND_URL}'

        if error or not code:
            params = urlencode({'error': error})
            return redirect(f'{login_url}?{params}')
        domain = settings.BASE_BACKEND_URL
        api_uri = reverse('authentication:login-with-github')
        redirect_uri = f'{domain}{api_uri}'
        access_token = github_get_access_token(code=code, redirect_uri=redirect_uri)

        user_data = github_get_user_info(access_token=access_token)
        # Github users often hide their email, if so we create a fake one. 
        # I'm just testing if the length is at the very least 4.
        # Github will either send an empty string or a valid email
        if user_data['email'] is None or '@' not in user_data['email']:
            valid_email = f"{user_data['login']}@ihavenopublicemail.org"
            user_data['email'] = valid_email
            print('no email found, creating=', valid_email)
        else:
            print('found email=', user_data['email'])

        profile_data = {
            'email': user_data['email'],
            'username': user_data['login'],
            'first_name': user_data.get('name', ''),
            'last_name': user_data.get('company', ''),
        }



        # We use get-or-create logic here for the sake of the example.
        user, _ = user_get_or_create(**profile_data)
        response = redirect(settings.BASE_FRONTEND_URL)
        response = jwt_login(response=response, user=user, request=request)

        return response

class GoogleLoginApi(PublicApiMixin, ApiErrorsMixin, APIView):
    """This class is used when a user logins with the Google link
    the url is: /google/
    """
    
    class InputSerializer(serializers.Serializer):
        code = serializers.CharField(required=False)
        error = serializers.CharField(required=False)

    def get(self, request, *args, **kwargs):
        input_serializer = self.InputSerializer(data=request.GET)
        input_serializer.is_valid(raise_exception=True)
        validated_data = input_serializer.validated_data
        code = validated_data.get('code')
        error = validated_data.get('error')
        login_url = f'{settings.BASE_FRONTEND_URL}'

        if error or not code:
            params = urlencode({'error': error})
            return redirect(f'{login_url}?{params}')
        domain = settings.BASE_BACKEND_URL
        api_uri = reverse('authentication:login-with-google')
        redirect_uri = f'{domain}{api_uri}'
        access_token = google_get_access_token(code=code, redirect_uri=redirect_uri)
        user_data = google_get_user_info(access_token=access_token)

        profile_data = {
            'email': user_data['email'],
            'username': user_data['email'],
            'first_name': user_data.get('given_name', ''),
            'last_name': user_data.get('family_name', ''),
        }
        # We use get-or-create logic here for the sake of the example.
        user, _ = user_get_or_create(**profile_data)
        response = redirect(settings.BASE_FRONTEND_URL)
        response = jwt_login(response=response, user=user, request=request)

        return response
