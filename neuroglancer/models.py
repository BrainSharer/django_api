from django.db import models
from django.conf import settings
from django.utils.html import escape
import json
import pandas as pd
from django.template.defaultfilters import truncatechars
from authentication.models import Lab
from brain.models import AtlasModel, Animal, ScanRun
from django_mysql.models import EnumField

LAUREN_ID = 16
MANUAL = 1
CORRECTED = 2
POINT_ID = 52
LINE_ID = 53
POLYGON_ID = 54
UNMARKED = 'UNMARKED'
MICRON = "\u00b5"
XUM = f'X{MICRON}'
YUM = f'Y{MICRON}'
ZUM = f'Z{MICRON}'
DEBUG = settings.DEBUG



class NeuroglancerState(models.Model):
    """Model corresponding to the neuroglancer json states stored in the neuroglancer_state table.
    This name was used as the original verion of Neuroglancer stored all the data in the URL.
    """

    id = models.BigAutoField(primary_key=True)
    neuroglancer_state = models.JSONField(verbose_name="Neuroglancer State")
    lab = models.ForeignKey(Lab, on_delete=models.DO_NOTHING, null=True, db_column="FK_lab_id", verbose_name='Lab')
    animal = models.ForeignKey(Animal,  on_delete=models.DO_NOTHING, null=True,
                              blank=True, db_column="FK_prep_id",
                               verbose_name="Animal")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, null=False,
                              blank=False, db_column="FK_user_id",
                               verbose_name="User")
    public = models.BooleanField(default = False, db_column='public')
    active = models.BooleanField(default = False, db_column='active')
    readonly = models.BooleanField(default = False, verbose_name='Read only')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, editable=False, null=False, blank=False)
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
        xy_resolution = 1.0
        z_resolution = 1.0
        if self.animal is not None and self.animal != 'NA':
            scan_run = ScanRun.objects.filter(prep_id=self.animal).first()
            if scan_run is not None:
                xy_resolution = scan_run.resolution
                z_resolution = scan_run.zresolution
        
        if self.neuroglancer_state is not None:
            json_txt = self.neuroglancer_state
            layers = json_txt['layers']
            for layer in layers:
                if 'annotations' in layer:
                    name = layer['name']
                    annotations = layer['annotations']
                    for annotation in annotations:
                        print(annotation)
                    ##### This is for the points
                    point_ids = list(set(row["id"] for row in annotations if "id" in row 
                                         and 'point' in row and "parentAnnotationId" not in row))
                    for UUID in point_ids:
                        points = [row['point'] for row in annotations if 'point' in row and "id" in row and row["id"] == UUID]
                        descriptions = [row["description"] for row in annotations if "description" in row 
                                              and 'type' in row 
                                              and row['type'] == 'point'
                                              and 'id' in row
                                              and row['id'] == UUID]
                        if len(descriptions) == 0:
                            descriptions = 'unlabeled point'
                        else:
                            descriptions = descriptions[0].replace('\n', ', ')
                        df = create_one_dataframe(points, name, UUID, 'point', 0, descriptions, xy_resolution, z_resolution)
                        df = df[['Layer', 'Type', 'Labels', 'UUID', 'Order', 'X', 'Y', 'Section', 'Xum', 'Yum', 'Zum']]
                        dfs.append(df)
                    
                    ##### Finished with non cloud points
                    ##### This is for cloud points
                    cloud_parent_ids = list(set(row["id"] for row in annotations if "id" in row
                                         and 'type' in row
                                         and row['type'] == 'cloud'))

                    for UUID in cloud_parent_ids:
                        descriptions = [row["description"] for row in annotations if "description" in row 
                                            and 'type' in row 
                                            and row['type'] == 'cloud'
                                            and 'id' in row
                                            and row['id'] == UUID]
                        if len(descriptions) == 0:
                            descriptions = 'unlabeled cloud point'
                        else:
                            descriptions = descriptions[0].replace('\n', ', ')
                        points = [ row['point'] for row in annotations if 'point' in row and "parentAnnotationId" in row and row["parentAnnotationId"] == UUID]
                        df = create_one_dataframe(points, name, UUID, 'cloud', 0, descriptions, xy_resolution, z_resolution)
                        df = df[['Layer', 'Type', 'Labels', 'UUID', 'Order', 'X', 'Y', 'Section', 'Xum', 'Yum', 'Zum']]
                        dfs.append(df)
                    ##### Finished with cloud points

                    ##### This is for the volumes/polygons
                    ##### For each volume, get all the polygons and then for each polygon, get all the points
                    volume_ids = [row['id'] for row in annotations if "id" in row and 'type' in row and row['type'] == 'volume']
                    for volume_id in volume_ids:
                        polygon_ids = [row['id'] for row in annotations if "id" in row 
                                       and 'type' in row 
                                       and row['type'] == 'polygon'
                                       and 'parentAnnotationId' in row
                                       and row['parentAnnotationId'] == volume_id]
                        
                        # The description is associated with a volume, not a polygon
                        descriptions = [row["description"] for row in annotations if "description" in row 
                                                and 'type' in row 
                                                and row['type'] == 'volume'
                                                and row['id'] == volume_id]
                        if len(descriptions) == 0:
                            descriptions = 'unlabeled polygon'
                        else:
                            descriptions = descriptions[0].replace('\n', ', ')
                        
                        for UUID in polygon_ids:
                            lines = [row for row in annotations
                                if "pointA" in row
                                and "type" in row
                                and row["type"] == "line"
                                and "parentAnnotationId" in row
                                and row["parentAnnotationId"] == UUID
                            ]
                            first = [round(x) for x in lines[0]['pointA']]
                            last = [round(x) for x in lines[-1]['pointB']] 

                            if first != last:
                                lines = resort_points(lines)

                            points = [row['pointA'] for row in lines]
                            orders = [o for o in range(1, len(points) + 1)]
                            df = create_one_dataframe(points, name, UUID, 'volume', orders, descriptions, xy_resolution, z_resolution)
                            df = df[['Layer', 'Type', 'Labels', 'UUID', 'Order', 'X', 'Y', 'Section', 'Xum', 'Yum', 'Zum']]
                            dfs.append(df)

            if len(dfs) == 0:
                return None
            elif len(dfs) == 1:
                result = dfs[0]
            else:
                result = pd.concat(dfs)

        if DEBUG:
            print(result.head())

        result.sort_values(by=['Layer', 'Type', 'Labels', 'UUID', 'Section', 'Order', 'X', 'Y'], inplace=True)
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
        managed = False
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
    updated = models.CharField(max_length=100, blank=False, null=False)

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
        if self.annotation is not None and 'type' in self.annotation:
            annotation_type = self.annotation['type']
        return annotation_type
    

class AnnotationData(AnnotationSession):
    """Model corresponding to the annotation points table in the database
    """
    
    class Meta:
        managed = False
        proxy = True
        verbose_name = 'Exported annotation data'
        verbose_name_plural = 'Exported annotations'

class Points(NeuroglancerState):
    """Model corresponding to the annotation points table in the database
    """
    
    class Meta:
        managed = False
        proxy = True
        verbose_name = 'Layer points/polygons'
        verbose_name_plural = 'Layer points/polygons'

def resort_points(rows):
    """Reorders a list of dictionaries based on the previous value of a specified key."""

    if not rows:
        return rows

    result = [rows[0]]  # Start with the first dictionary
    for i in range(1, len(rows)):
        for j in range(i):
            if rows[i]['pointA'] == result[j]['pointB']:
                result.insert(j + 1, rows[i])
                break
        else:
            result.append(rows[i])

    return result

def create_one_dataframe(points, name, UUID, data_type='point', orders=0, descriptions="", xy_resolution=1, z_resolution=1):
    df = pd.DataFrame(points, columns=['X', 'Y', 'Section'])
    df['Section'] = df['Section'].astype(int)
    df['Layer'] = name
    df['Type'] = data_type
    df['UUID'] = UUID
    df['Order'] = orders
    df['Labels'] = descriptions
    df['Xum'] = df['X'] * xy_resolution
    df['Yum'] = df['Y'] * xy_resolution
    df['Zum'] = df['Section'] * z_resolution
    return df
