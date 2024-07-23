"""This module defines the serializers for the REST API endpoints for Neuroglancer.
"""

from rest_framework import serializers
from rest_framework.exceptions import APIException
import logging

from authentication.models import User

logging.basicConfig()
logger = logging.getLogger(__name__)


class NeuronSerializer(serializers.Serializer):
    """
    Serializes a list of brain atlas segment Ids
    Used for the Mouselight data
    """
    segmentId = serializers.ListField()

class AnatomicalRegionSerializer(serializers.Serializer):
    """
    Serializes a list of brain atlas region names
    Used for the Mouselight data
    """
    segment_names = serializers.ListField()

class ViralTracingSerializer(serializers.Serializer):
    """
    Serializes a list of tracing brain urls
    Used for the Mouselight data
    """
    brain_names = serializers.ListField()
    frac_injections = serializers.ListField()
    primary_inj_sites = serializers.ListField()
    brain_urls = serializers.ListField()
