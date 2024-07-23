"""This is the module that the user will use to connect to the database. This can be defined in either
a web page or in a REST API call. This module is the 'V' in the MVC framework for the brain.
"""
from django.shortcuts import render
from brain.models import Animal, Section
from brain.forms import AnimalForm
from rest_framework import status
from django.http import Http404, JsonResponse
from rest_framework import views
from rest_framework.response import Response
from brain.serializers import AnimalSerializer
from brain.models import ScanRun


def image_list(request):
    """A method to provide a list of all active animals in a nice dropdown menu format.
    
    :return: HTML for the dropdown menu"""
    prep_id = request.GET.get('prep_id')
    form = AnimalForm()  # A form bound to the GET data
    animals = Animal.objects.filter(prep_id=prep_id).order_by('prep_id')
    sections = None
    title = 'Select an animal from the dropdown menu.'
    if prep_id:
        title = 'Thumbnail images for: {}'.format(prep_id)
        sections = Section.objects.filter(
            prep_id=prep_id).order_by('file_name')
    return render(request, 'list.html', {'animals': animals, 'sections': sections, 'form': form, 'prep_id': prep_id, 'title': title})


class AnimalList(views.APIView):
    """List all animals for the REST API.
    """

    def get(self, request, format=None):
        """Gets all active animals ordered by the prep_id (animal name).
        
        :return: serialized animal objects
        """
        animals = Animal.objects.filter(active=True).order_by('prep_id')
        serializer = AnimalSerializer(animals, many=True)
        return Response(serializer.data)


class AnimalDetail(views.APIView):
    """
    Returns the animal string. It is used with this URL:
    http://server/animal/DKXX and it returns all animal info.
    """

    def get_object(self, pk):
        """This method safely gets an animal object.
        
        :param pk: animal name as the primary key.
        :return: Either the object or a useful error message."""
        try:
            return Animal.objects.get(pk=pk)
        except Animal.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        """This method safely gets the object and serializes it.
        
        :param pk: animal name as the primary key.
        :return: a HTTP response with the serialized data."""
        animal = self.get_object(pk)
        serializer = AnimalSerializer(animal)
        return Response(serializer.data)



class ScanResolution(views.APIView):
    """A simple class to return the x,y,z scan resolution.
    """

    def get(self, request, prep_id='Atlas', format=None):
        """This fetches the xy and z scan resolution for an animal.
        
        :param request: HTTP request
        :param prep_id: name of the animal, defaults to 'Atlas'
        :param format: None
        :return: a simple dictionary containing the xy and z resolution. 
        """
        result = ScanRun.objects.filter(prep_id=prep_id).first()
        if result:
            response = {'resolution': [
                result.resolution, result.resolution, result.zresolution]}
        else:
            response = {'resolution': None}
        return JsonResponse(response)
