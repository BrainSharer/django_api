from django.db import models
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy
import re
import json
import pandas as pd
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
DEBUG = settings.DEBUG

class NeuroglancerState(models.Model):
    """Model corresponding to the neuroglancer json states stored in the neuroglancer_state table.
    This name was used as the original verion of Neuroglancer stored all the data in the URL.
    """
    
    id = models.BigAutoField(primary_key=True)
    neuroglancer_state = models.JSONField(verbose_name="Neuroglancer State")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, null=False,
                              blank=False, db_column="FK_user_id",
                               verbose_name="User")
    #####TODO lab = models.ForeignKey(Lab, models.CASCADE, null=True, db_column="FK_user_id", verbose_name='Lab')
    public = models.BooleanField(default = False, db_column='active')
    readonly = models.BooleanField(default = False, verbose_name='Read only')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, editable=False, null=False, blank=False)
    user_date = models.CharField(max_length=25, null=True, blank=True, default='123456789')
    comments = models.CharField(max_length=255)
    description = models.TextField(max_length=2001, blank=True, null=True)

    @property
    def short_description(self):
        return truncatechars(self.neuroglancer_state, 50)

    @property
    def escape_url(self):
        return escape(self.neuroglancer_state)
    
    @property
    def user(self):
        first_name = "NA"
        if self.owner is not None and self.owner.first_name is not None:
            first_name = self.owner.first_name
        return first_name

    @property
    def animal(self):
        """Find the animal within the url between data/ and /neuroglancer_data:
        data/MD589/neuroglancer_data/C1
        
        :return: the first match if found, otherwise NA
        """
        animal = "NA"
        pattern = 'data/(\w*)/www/neuroglancer_data'
        neuroglancer_json = self.neuroglancer_state
        image_layers = [layer for layer in neuroglancer_json['layers'] if layer['type'] == 'image']
        if len(image_layers) > 0:
            first_image_layer = json.dumps(image_layers[0])
            match = re.search(pattern, first_image_layer)
            if match is not None and match.group(1) is not None:
                animal = match.group(1)
            else:
                pattern = 'data/(\w*)/neuroglancer_data'
                match = re.search(pattern, first_image_layer)
                if match is not None and match.group(1) is not None:
                    animal = match.group(1)

        return animal

    @property
    def lab(self):
        '''
        The primary lab of the user
        :param obj: animal model
        '''
        lab = "NA"
        if self.owner is not None and self.owner.lab is not None:
            lab = self.owner.lab
        return lab

    @property
    def point_frame(self):
        df = None
        if self.neuroglancer_state is not None:
            point_data = self.find_values('annotations', self.neuroglancer_state)
            if len(point_data) > 0:
                d = [row['point'] for row in point_data[0]]
                df = pd.DataFrame(d, columns=['X', 'Y', 'Section'])
                df = df.round(decimals=0)
        return df

    @property
    def points(self):
        result = None
        dfs = []
        if self.neuroglancer_state is not None:
            json_txt = self.neuroglancer_state
            layers = json_txt['layers']
            for layer in layers:
                if 'annotations' in layer:
                    name = layer['name']
                    annotation = layer['annotations']
                    d = [row['point'] for row in annotation if 'point' in row and 'pointA' not in row]
                    df = pd.DataFrame(d, columns=['X', 'Y', 'Section'])
                    df['Section'] = df['Section'].astype(int)
                    df['Layer'] = name
                    structures = [row['description'] for row in annotation if 'description' in row]
                    if len(structures) != len(df):
                        structures = ['' for row in annotation if 'point' in row and 'pointA' not in row]
                    df['Description'] = structures
                    df = df[['Layer', 'Description', 'X', 'Y', 'Section']]
                    df = df.drop_duplicates()
                    dfs.append(df)
            if len(dfs) == 0:
                result = None
            elif len(dfs) == 1:
                result = dfs[0]
            else:
                result = pd.concat(dfs)
        return result

    @property
    def layers(self):
        layer_list = []
        if self.neuroglancer_state is not None:
            json_txt = self.neuroglancer_state
            layers = json_txt['layers']
            for layer in layers:
                if 'annotations' in layer:
                    layer_name = layer['name']
                    layer_list.append(layer_name)
        return layer_list

    class Meta:
        managed = True
        verbose_name = "Neuroglancer state"
        verbose_name_plural = "Neuroglancer states"
        ordering = ('comments', 'created')
        db_table = 'neuroglancer_state'

    def __str__(self):
        return u'{}'.format(self.comments)

    @property
    def point_count(self):
        result = "display:none;"
        if self.points is not None:
            df = self.points
            df = df[(df.Layer == 'PM nucleus') | (df.Layer == 'premotor')]
            if len(df) > 0:
                result = "display:inline;"
        return result


    def find_values(self, id, json_repr):
        results = []

        def _decode_dict(a_dict):
            try:
                results.append(a_dict[id])
            except KeyError:
                pass
            return a_dict

        json.loads(json_repr, object_hook=_decode_dict)  # Return value ignored.
        return results


class Points(NeuroglancerState):
    """Model corresponding to the annotation points table in the database
    """
    
    class Meta:
        managed = False
        proxy = True
        verbose_name = 'Points'
        verbose_name_plural = 'Points'

class CellType(models.Model):
    """Model corresponding to the cell type table in the database
    """
    
    id = models.BigAutoField(primary_key=True)
    cell_type = models.CharField(max_length=200)
    description = models.TextField(max_length=2001)
    active = models.IntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = False
        db_table = 'cell_type'
        verbose_name = 'Cell Type'
        verbose_name_plural = 'Cell Types'
    def __str__(self):
        return f'{self.cell_type}'

class BrainRegion(AtlasModel):
    """This class model is for the brain regions or structures in the brain.
    """
    
    id = models.BigAutoField(primary_key=True)
    abbreviation = models.CharField(max_length=200)
    description = models.TextField(max_length=2001, blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'brain_region'
        verbose_name = 'Brain region'
        verbose_name_plural = 'Brain regions'

    def __str__(self):
        return f'{self.description} {self.abbreviation}'
    
def get_region_from_abbreviation(abbreviation):
    if abbreviation is None or abbreviation == '':
        abbreviation = 'polygon'
    brainRegion = BrainRegion.objects.filter(abbreviation=abbreviation).first()
    return brainRegion

    
class SearchSessions(models.Model):
    id = models.BigAutoField(primary_key=True)
    animal_abbreviation_username = models.CharField(max_length=2001, null=False, db_column="animal_abbreviation_username", verbose_name="Animal")
    label_type = models.CharField(max_length=100, blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'v_search_sessions'
        verbose_name = 'Search session'
        verbose_name_plural = 'Search sessions'

class AnnotationLabel(AtlasModel):
    id = models.BigAutoField(primary_key=True)
    label_type = EnumField(choices=['brain region', 'cell'], blank=False, null=False, default='brain region')
    label = models.CharField(max_length=50, blank=False, null=False)
    description = models.TextField(max_length=2001, blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'annotation_label'
        verbose_name = 'Annotation label'
        verbose_name_plural = 'Annotation labels'

    def __str__(self):
        return f'{self.label}'

class AnnotationSession(AtlasModel):
    """This model describes a user session in Neuroglancer."""
    id = models.BigAutoField(primary_key=True)
    animal = models.ForeignKey(Animal, models.CASCADE, null=True, db_column="FK_prep_id", verbose_name="Animal")
    #neuroglancer_model = models.ForeignKey(NeuroglancerState, models.CASCADE, null=True, db_column="FK_state_id", verbose_name="Neuroglancer state")
    #label = models.ForeignKey(AnnotationLabel, models.CASCADE, null=True, db_column="FK_label_id", verbose_name="Brain region")
    labels = models.ManyToManyField(AnnotationLabel, related_name="labels", db_column="annotation_session_id",  verbose_name="Annotation label")
    annotator = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, db_column="FK_user_id",
                               verbose_name="Annotator", blank=False, null=False)
    annotation = models.JSONField(verbose_name="Annotation")

    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'annotation_session'
        verbose_name = 'Annotation session'
        verbose_name_plural = 'Annotation sessions'

    @property
    def annotation_type(self):
        annotation_type = "NA"
        if self.annotation is not None:
            if 'cell' in self.annotation:
                annotation_type = 'cell'
            elif 'point' in self.annotation:
                annotation_type = 'point/COM'
            elif 'volume' in self.annotation:
                annotation_type = 'volume'
            else:
                annotation_type = 'NA'
        return annotation_type






