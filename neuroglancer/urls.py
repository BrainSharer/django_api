from django.urls import path, include
from neuroglancer.views import AnnotationPrivateViewSet, NeuroglancerPrivateViewSet, NeuroglancerPublicViewSet,  \
    create_state, Segmentation, get_labels, search_annotation, search_label

from rest_framework import routers
app_name = 'neuroglancer'

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'neuroglancer', NeuroglancerPrivateViewSet, basename='neuroglancer') # private portal data
router.register(r'neuroglancer/', NeuroglancerPrivateViewSet, basename='neuroglancer') # private portal data
router.register(r'neuroglancers', NeuroglancerPublicViewSet, basename='neuroglancers') # public data

annotation_urls = [
    path('annotations/labels', get_labels, name='get_labels'),
    path('annotations/labels/', search_label, name='search_labels'),
    path('annotations/labels/<str:search_string>', search_label, name='search_labels'),
    path('annotations/segmentation/<int:session_id>', Segmentation.as_view(),name = 'create_segmentation'),
    path('annotations/search', search_annotation, name='search_annotations'),
    path('annotations/search/', search_annotation, name='search_annotations'),
    path('annotations/search/<str:search_string>', search_annotation, name='search_annotations'),
    path('annotations/api/<int:session_id>', AnnotationPrivateViewSet.as_view(), name='annotation_session_get_put'),
    path('annotations/api/', AnnotationPrivateViewSet.as_view(), name='annotation_session_post'),


]

general_urls = [
    path('', include(router.urls)),
    path('createstate', create_state)
]

urlpatterns = annotation_urls + general_urls