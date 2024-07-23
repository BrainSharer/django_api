from django.http import Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import logout
from django.conf import settings

from rest_framework import generics, viewsets
from rest_framework import permissions
from rest_framework.response import Response
from authentication.forms import LocalSignUpForm
from rest_framework_simplejwt.views import TokenObtainPairView

from authentication.models import Lab, User
from authentication.serializers import LabSerializer, MyTokenObtainPairSerializer, RegisterSerializer, \
    UserSerializer, ValidateUserSerializer


def logout_view(request):
    logout(request)
    response = HttpResponseRedirect(settings.LOGOUT_REDIRECT_URL)    
    response.delete_cookie("access")
    response.delete_cookie("refresh")
    response.delete_cookie('id')
    response.delete_cookie('username')
    response.delete_cookie('lab')
    return response


class LabViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows the neuroglancer states to be viewed or edited.
    Note, the update, and insert methods are over ridden in the serializer.
    It was more convienent to do them there than here.
    """
    queryset = Lab.objects.all()
    serializer_class = LabSerializer
    permission_classes = [permissions.AllowAny]


class RegisterView(generics.CreateAPIView):
    """
    Description of RegisterView
    This is when a person registers to become a user on the registration page. 
    This must be allowed to accept posts so
    we allow unauthenticated access

    Inheritance:
        generics.CreateAPIView:

    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, username):
        print('UserView does this get called??')
        user = {'id':0}
        username = str(username).replace('"','').strip()
        try:
           queryset = User.objects.filter(username=username)
        except User.DoesNotExist:
            raise Http404
        if queryset is not None and len(queryset) > 0:
            user = queryset[0]

        serializer = UserSerializer(user, many=False)
        return Response(serializer.data)


class ValidateUserView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = ValidateUserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        print('ValidateUserView does this get called??')
        queryset = User.objects.all()
        username = self.request.query_params.get('username')
        if username is not None:
            return queryset.filter(username=username)

        email = self.request.query_params.get('email')
        if email is not None:
            return queryset.filter(email=email)

        return User.objects.filter(pk=0)

class LocalSignUpView(generic.CreateView):
    form_class = LocalSignUpForm
    #success_url = settings.LOGIN_URL
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer