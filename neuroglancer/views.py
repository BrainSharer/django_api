"""This is the module that the user will use to connect to the database.
This can be defined in either a web page or in a REST API call. This module
is the 'V' in the MVC framework for the Neuroglancer app
portion of the portal.
"""

from rest_framework import viewsets, views, permissions, status
from django.http import JsonResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.pagination import LimitOffsetPagination
from timeit import default_timer as timer

from brain.models import ScanRun
from neuroglancer.annotation_session_manager import AnnotationSessionManager, get_label_ids
from neuroglancer.models import AnnotationLabel, AnnotationSession, \
    NeuroglancerState, SearchSessions
from neuroglancer.serializers import AnnotationLabelModelSerializer, AnnotationModelSerializer, AnnotationSearchSerializer, AnnotationSessionDataSerializer, \
    LabelSerializer, NeuroglancerNoStateSerializer, NeuroglancerStateSerializer
from neuroglancer.models import DEBUG


DEFAULT_ANIMAL = 'AtlasV8'

@api_view(['GET'])
def get_labels(request):
    labels = AnnotationLabel.objects.filter(active=True).order_by('label_type').order_by('label').all()
    serializer = AnnotationLabelModelSerializer(labels, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def search_label(request, search_string=None):
    data = []
    if search_string:
        labels = AnnotationLabel.objects\
            .filter(label__icontains=search_string).order_by('label')
        for row in labels:
            data.append({"id": row.id, "label_type": row.label_type, "label": row.label})
        if DEBUG:
            print(f'labels query: {labels.query}')
            print(f'data: {data}')
    serializer = LabelSerializer(data, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def search_annotation(request, search_string=None):
    data = []
    if search_string:
        rows = SearchSessions.objects\
            .filter(animal_abbreviation_username__icontains=search_string)\
        .order_by('-updated').order_by('animal_abbreviation_username').distinct()
        print(rows.query)
        for row in rows:
            data.append({
                "id": row.id,
                "animal_abbreviation_username": row.animal_abbreviation_username,
                "updated": row.updated
            })
        
    serializer = AnnotationSearchSerializer(data, many=True)
    return Response(serializer.data)

class Segmentation(views.APIView):
    """Method to create a 3D volume from existing annotation
    """

    permission_classes = [permissions.IsAuthenticated]

    
    def get(self, request, session_id):
        """Simpler version that does not use slurm or subprocess script
        """
        if DEBUG:
            start_time = timer()
        try:
            annotationSession = AnnotationSession.objects.get(pk=session_id)
        except AnnotationSession.DoesNotExist:
            return Response({"msg": f"Annotation data does not exist"}, status=status.HTTP_404_NOT_FOUND)
        try:
            scan_run = ScanRun.objects.get(prep=annotationSession.animal)
        except ScanRun.DoesNotExist:
            return Response({"msg": f"Scan run data does not exist"}, status=status.HTTP_404_NOT_FOUND)

        label = annotationSession.labels.first()
        annotation_session_manager = AnnotationSessionManager(scan_run, label)
        polygons = annotation_session_manager.create_polygons(annotationSession.annotation)
        if not isinstance(polygons, dict):
            return Response({"msg": polygons}, status=status.HTTP_404_NOT_FOUND)
        origin, section_size = annotation_session_manager.get_origin_and_section_size(polygons)
        volume = annotation_session_manager.create_volume(polygons, origin, section_size)
        del polygons
        if volume is None or volume.shape[0] == 0:
            return Response({"msg": "Volume could not be created"}, status=status.HTTP_404_NOT_FOUND)        
        folder_name = annotation_session_manager.create_segmentation_folder(volume, annotationSession.animal, 
                                                 label, origin.tolist())
        del volume
        segmentation_save_folder = f"precomputed://{settings.HTTP_HOST}/structures/{folder_name}"
        if DEBUG:
            end_time = timer()
            total_elapsed_time = round((end_time - start_time), 2)
            print(f'Creating segmentation took {total_elapsed_time} seconds.')

        return JsonResponse({'url': segmentation_save_folder, 'name': folder_name})

##### Annotation API view

class AnnotationPrivateViewSet(APIView):
    """
    A viewset for viewing and editing user instances.
    """

    queryset = AnnotationSession.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id=None):
        if DEBUG:
            print('AnnotationPrivateViewSet.get')
        session = {}
        if session_id:
            try:
                data = AnnotationSession.objects.get(pk=session_id)
            except AnnotationSession.DoesNotExist:
                return Response({"details": "Annotation record does not exist"}, status=status.HTTP_404_NOT_FOUND)
            
            session['id'] = data.id
            session['annotation'] = data.annotation
        else:
            return Response({"details": "Session ID is missing."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AnnotationSessionDataSerializer(session, many=False)
        return Response(serializer.data)


    def post(self, request):
        if DEBUG:
            print('AnnotationPrivateViewSet.post')
        # check to make sure the serializer is valid, if so return the ID, if not, return error code.    
        if 'id' in request.data:
            del request.data['id']
        if 'label' not in request.data:
            return Response({"detail": "Label is required"}, status=status.HTTP_400_BAD_REQUEST)
        if 'animal' not in request.data or request.data['animal'] == None:
            return Response({"detail": "Animal is required"}, status=status.HTTP_400_BAD_REQUEST)
        if DEBUG:
            print(request.data)
        label_ids = get_label_ids(request.data.get('label'))
        request.data.update({'labels': label_ids})
        if 'animal' not in request.data or request.data['animal'] == 'NA':
            request.data.update({'animal': DEFAULT_ANIMAL})

        serializer = AnnotationModelSerializer(data=request.data)

        # check to make sure the serializer is valid, if so return the ID, if not, return error code.
        if serializer.is_valid():
            serializer.save()
            return Response({'id': serializer.data.get('id')}, status=status.HTTP_201_CREATED)
        else:
            if DEBUG:
                print(f'AnnotationPrivateViewSet.post serializer errors: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, session_id):
        if DEBUG:
            print('AnnotationPrivateViewSet.put')

        try:
            existing_session = AnnotationSession.objects.get(pk=session_id)
        except AnnotationSession.DoesNotExist:
            return Response({"detail": f"Annotation data does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        label_ids = get_label_ids(request.data.get('label'))
        if DEBUG:
            print(f'label_ids: {label_ids}')
            print(f'annotation animal {existing_session.animal}')
        request.data.update({'labels': label_ids})
        if 'animal' not in request.data or request.data['animal'] == 'NA':
            request.data.update({'animal': existing_session.animal})

        serializer = AnnotationModelSerializer(existing_session, data=request.data, partial=False)
        # check to make sure the serializer is valid, if so return the ID, if not, return error code.
        if serializer.is_valid():
            serializer.save()
            return Response({'id': serializer.data.get('id')}, status=status.HTTP_200_OK)
        else:
            if DEBUG:
                print(f'AnnotationPrivateViewSet.put serializer errors: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


##### Neuroglancer views


class NeuroglancerPublicViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows the neuroglancer states to be viewed by the public.
    Note, the update, and insert methods are over ridden in the serializer.
    It was more convienent to do them there than here.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = LimitOffsetPagination
    serializer_class = NeuroglancerNoStateSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given animal,
        by filtering against a `animal` query parameter in the URL.
        """

        queryset = NeuroglancerState.objects.only('id').filter(public=True).order_by('comments')
        description = self.request.query_params.get('description')
        lab = self.request.query_params.get('lab')
        if description is not None:
            queryset = queryset.filter(description__icontains=description)
        if lab is not None and int(lab) > 0:
            queryset = queryset.filter(lab=lab)

        return queryset

class NeuroglancerPrivateViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = NeuroglancerStateSerializer
    queryset = NeuroglancerState.objects.all()


