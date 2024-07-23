import os
from django.db import models
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy
import re
import json
import pandas as pd
import numpy as np
from django.template.defaultfilters import truncatechars
from authentication.models import Lab
from brain.models import AtlasModel, Animal
from django_mysql.models import EnumField

LAUREN_ID = 16
MANUAL = 1
CORRECTED = 2
POINT_ID = 52
LINE_ID = 53
POLYGON_ID = 54
UNMARKED = 'UNMARKED'


##### Imports from the brainsharer version
        
class MouselightNeuron(models.Model):
    id = models.BigAutoField(primary_key=True)
    idstring = models.CharField(max_length=64,null=False)
    sample_date = models.DateTimeField(null=True)
    sample_strain = models.CharField(max_length=255,null=True)
    virus_label = models.CharField(max_length=255,null=True) 
    fluorophore_label = models.CharField(max_length=255,null=True)
    annotation_space = models.CharField(
        max_length=20,
        choices=[
            ("ccfv3_25um","Allen Mouse Common Coordinate Framework v3, 25 micron isotropic"),
            ("ccfv3_hierarch_25um","Hierarchical region labeling for Allen Mouse Common Coordinate Framework v3, 25 micron isotropic"),
            ("pma_20um","Princeton Mouse Brain Atlas, 20 micron isotropic"),
            ("pma_hierarch_20um","Hierarchical region labeling for Princeton Mouse Brain Atlas, 20 micron isotropic")
        ],
        default="ccfv3_25um",
    )
    soma_atlas_id = models.PositiveIntegerField(null=True)
    axon_endpoints_dict = models.JSONField(default=dict)
    axon_branches_dict = models.JSONField(default=dict)
    dendrite_endpoints_dict = models.JSONField(default=dict)
    dendrite_branches_dict = models.JSONField(default=dict)

    class Meta:
        managed = False
        verbose_name = "MouseLight Neuron"
        verbose_name_plural = "MouseLight Neurons"
        db_table = 'mouselight_neuron'

    def __str__(self):
        return u'{}'.format(self.idstring)

class ViralTracingLayer(models.Model):
    id = models.BigAutoField(primary_key=True)
    brain_name = models.CharField(max_length=128,null=False)
    virus = models.CharField(max_length=32,null=False)
    timepoint = models.CharField(max_length=32,null=False)
    primary_inj_site = models.CharField(max_length=32,null=True)
    frac_inj_lob_i_v = models.FloatField(null=True) # fraction of injection in Lobules I-V
    frac_inj_lob_vi_vii = models.FloatField(null=True) # fraction of injection in Lobules VI and VII 
    frac_inj_lob_viii_x = models.FloatField(null=True) # fraction of injection in Lobules VIII-X
    frac_inj_simplex = models.FloatField(null=True) # fraction of injection in Simplex
    frac_inj_crusi = models.FloatField(null=True) # fraction of injection in Crus I
    frac_inj_crusii = models.FloatField(null=True) # fraction of injection in Crus II
    frac_inj_pm_cp = models.FloatField(null=True) # fraction of injection in Paramedian lobule and Copula Pyramidis

    class Meta:
        managed = False
        verbose_name = "Tom Pisano Viral Tracing Experiment Brain"
        verbose_name_plural = "Viral Tracing Brain"
        db_table = 'viral_tracing_layer'

    def __str__(self):
        return u'{}'.format(self.brain_name)
