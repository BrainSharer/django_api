from django.urls import path
from brain.views import SlideViewSet, AnimalList, AnimalDetail, ScanResolution

urlpatterns = [
    path('animals', AnimalList.as_view()),
    path('animal/<str:pk>', AnimalDetail.as_view()),
    path('resolution/<str:prep_id>', ScanResolution.as_view()),
    path('slides', SlideViewSet.as_view({'get': 'list'})),
]
