from django.urls import include, path
from rest_framework import routers
from authentication.views import LabViewSet, LocalSignUpView, UserView, ValidateUserView, logout_view
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from authentication.apis import GithubLoginApi, GoogleLoginApi
app_name = 'authentication'

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'labs', LabViewSet, basename='labs')


urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('validate/', ValidateUserView.as_view(), name='auth_validate'),
    path('user/<str:username>', UserView.as_view(), name='fetch_user'),
    path('api-token-auth/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api-token-refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("local/signup/", LocalSignUpView.as_view(), name="signup"),
    path("local/signout/", logout_view, name="signout"),
    path('github/', GithubLoginApi.as_view(), name='login-with-github'),
    path('google/', GoogleLoginApi.as_view(), name='login-with-google'),
]
