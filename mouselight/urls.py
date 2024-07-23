from django.urls import path
from mouselight import views

from rest_framework import routers
app_name = 'mouselight'

router = routers.DefaultRouter(trailing_slash=False)

mouselight_urls = [
        path('mlneurons/<str:atlas_name>/<str:neuron_parts_boolstr>/soma/<str:brain_region1>',
        views.MouseLightNeuron.as_view()),

    path('mlneurons/<str:atlas_name>/<str:neuron_parts_boolstr>/soma/<str:brain_region1>/soma/<str:brain_region2>',
        views.MouseLightNeuron.as_view()),
    path('mlneurons/<str:atlas_name>/<str:neuron_parts_boolstr>/<str:filter_type1>/<str:brain_region1>/<str:operator_type1>/<int:thresh1>',
        views.MouseLightNeuron.as_view()),

    path('mlneurons/<str:atlas_name>/<str:neuron_parts_boolstr>/<str:filter_type1>/<str:brain_region1>/<str:operator_type1>/<int:thresh1>/soma/<str:brain_region2>',
        views.MouseLightNeuron.as_view()),

    path('mlneurons/<str:atlas_name>/<str:neuron_parts_boolstr>/soma/<str:brain_region1>/<str:filter_type2>/<str:brain_region2>/<str:operator_type2>/<int:thresh2>',
        views.MouseLightNeuron.as_view(),name='test'),

    path('mlneurons/<str:atlas_name>/<str:neuron_parts_boolstr>/<str:filter_type1>/<str:brain_region1>/<str:operator_type1>/<int:thresh1>/<str:filter_type2>/<str:brain_region2>/<str:operator_type2>/<int:thresh2>',
        views.MouseLightNeuron.as_view()),

    path('anatomical_regions/<str:atlas_name>',views.AnatomicalRegions.as_view()),

    path('tracing_annotations/<str:virus_timepoint>/<str:primary_inj_site>',
        views.TracingAnnotation.as_view()),

]

urlpatterns = mouselight_urls