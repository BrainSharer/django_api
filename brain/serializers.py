"""This module defines the serializers for the REST API endpoints.
"""
from rest_framework import serializers
from brain.models import Animal

class AnimalSerializer(serializers.ModelSerializer):
    """This is a model serializer which means it will serialize all data
    for an animal in a nice HTTP response for the REST API"""
    class Meta:
        model = Animal
        fields = '__all__'
