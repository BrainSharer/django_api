"""This module defines the serializers for the REST API endpoints for Neuroglancer.
"""

from rest_framework import serializers
from rest_framework.exceptions import APIException
from neuroglancer.models import AnnotationLabel, AnnotationSession, NeuroglancerState
from authentication.models import User



class AnnotationModelSerializer(serializers.ModelSerializer):
    class Meta:
        model=AnnotationSession
        fields='__all__'

class AnnotationLabelModelSerializer(serializers.ModelSerializer):
    class Meta:
        model=AnnotationLabel
        fields='__all__'

class AnnotationSessionDataSerializer(serializers.Serializer):
    """This one feeds the data import of annotations.
    """

    id = serializers.IntegerField()
    annotation = serializers.JSONField()

class AnnotationSessionSerializer(serializers.Serializer):
    """This one feeds the data import of annotations.
    """

    id = serializers.IntegerField()
    animal_abbreviation_username = serializers.CharField()


class LabelSerializer(serializers.Serializer):
    """A serializer class for the brain region model."""
    id = serializers.IntegerField()
    label_type = serializers.CharField()
    label = serializers.CharField()

class NeuroglancerNoStateSerializer(serializers.ModelSerializer):
    """Override method of entering a url into the DB.
    This serializer ignores the JSON state as it is a really big
    field to serialize when unneccessary.
    """
    animal = serializers.CharField(required=False)
    lab = serializers.CharField(required=False)
    user = serializers.CharField(required=False)

    class Meta:
        model = NeuroglancerState
        ordering = ['-created']
        exclude = ('neuroglancer_state', )

class NeuroglancerStateSerializer(serializers.ModelSerializer):
    """Override method of entering a url into the DB.
    The url *probably* can't be in the NeuroglancerState when it is returned
    to neuroglancer as it crashes neuroglancer.
    """
    animal = serializers.CharField(required=False)
    lab = serializers.CharField(required=False)

    class Meta:
        model = NeuroglancerState
        ordering = ['-created']
        fields = '__all__'

    def create(self, validated_data):
        """This method gets called when a user clicks New in Neuroglancer
        """
        obj = NeuroglancerState(
            neuroglancer_state=validated_data['neuroglancer_state'],
            user_date=validated_data['user_date'],
            comments=validated_data['comments'],
        )
        if 'owner' in validated_data:
            owner = validated_data['owner']
            obj = self.save_neuroglancer_state(obj, owner)
        return obj

    def update(self, obj, validated_data):
        """This gets called when a user clicks Save in Neuroglancer
        This is a very fast method. Even with a large set of polygons, 
        it only took around 0.25 seconds on a home computer.
        """
        
        obj.neuroglancer_state = validated_data.get('neuroglancer_state', obj.neuroglancer_state)
        
        obj.user_date = validated_data.get('user_date', obj.user_date)
        obj.comments = validated_data.get('comments', obj.comments)
        if 'owner' in validated_data:
            owner = validated_data['owner']
            obj = self.save_neuroglancer_state(obj, owner)
        return obj

    def save_neuroglancer_state(self, obj, owner):
        """This method takes care of tasks that are in both create and update
        
        :param obj: the neuroglancerModel object
        :param owner: the owner object from the validated_data
        
        """
        try:
            obj.owner = owner
        except User.DoesNotExist:
            logger.error('Owner was not in validated data')
        try:
            obj.save()
        except APIException:
            logger.error('Could not save Neuroglancer model')
        # obj.neuroglancer_state = None
        return obj

