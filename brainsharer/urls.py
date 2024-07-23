"""
include('django.contrib.auth.urls') this needs to be in this urls.py
and not in an app urls.py

"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('local/', include('django.contrib.auth.urls')), 
    #path('accounts/', include('allauth.urls')),
    path('', include('authentication.urls')),
    path('', include('brain.urls')),
    path('', include('mouselight.urls')),
    path('', include('neuroglancer.urls')),
]

urlpatterns +=  static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += path('__debug__/', include(debug_toolbar.urls)),

