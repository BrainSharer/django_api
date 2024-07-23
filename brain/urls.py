from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from brain import views

urlpatterns = [
    path('animals', views.AnimalList.as_view()),
    path('animal/<str:pk>', views.AnimalDetail.as_view()),
    path('resolution/<str:prep_id>', views.ScanResolution.as_view()),
]