"""This module creates the admin interface for all the Neuroglancer tools used by the user.
It lists the classes and methods used to administer the 'Neuroglancer' app in 
our database portal. This is where the end user can create, retrieve, update and delete (CRUD)
metadata associated with the 'Neuroglancer' app. It does not list the fields (database columns). Look 
in the models document for the database table model. 
"""
from django.contrib import admin
from mouselight.models import MouselightNeuron, ViralTracingLayer

@admin.register(MouselightNeuron)
class MouselightNeuronAdmin(admin.ModelAdmin):
    list_display = ('id', 'idstring', 'sample_date')

@admin.register(ViralTracingLayer)
class ViralTracingLayerAdmin(admin.ModelAdmin):
    list_display = ('brain_name', 'virus', 'timepoint', 'primary_inj_site')
    search_fields = ('brain_name', 'virus', 'timepoint', 'primary_inj_site')