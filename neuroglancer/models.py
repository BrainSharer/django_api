from collections import defaultdict

from django.db import models
from django.conf import settings
from django.utils.html import escape
import json
import numpy as np
import pandas as pd
from django.template.defaultfilters import truncatechars
from authentication.models import Lab
from brain.models import AtlasModel, Animal, ScanRun
from django_mysql.models import EnumField
from itertools import zip_longest

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
    neuroglancer_state = models.JSONField(verbose_name="Neuroglancer State", blank=False, null=False, default=dict)
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
    def polygons(self):
        """
        Convert Neuroglancer annotation layers into a polygon summary DataFrame.

        Assumptions:
        - Volume annotations have type='volume' and an 'id'.
        - Polygon annotations have type='polygon', an 'id', and a
            'parentAnnotationId' referring to a volume.
        - Line annotations have type='line', pointA=[x, y, z], and a
            'parentAnnotationId' referring to a polygon.
        - Cloud layers contain annotations with type='point' and
            point=[x, y, z].

        Returns:
            pandas.DataFrame with OUTPUT_COLUMNS.
        """
        if not self.neuroglancer_state:
            return None


        # Index all annotations in one pass.
        volume_layers = []
        cloud_layers = []
        polygons_by_id = {}
        polygon_ids_by_volume = defaultdict(list)
        lines_by_polygon = defaultdict(list)
        dimensions = self.neuroglancer_state.get("dimensions", {"x": [1], "y": [1], "z": [1]})
        x = dimensions.get("x", [1]) # default to 1 if not found
        # Resolve the XY resolution once in meters, convert to micrometers.
        xy_resolution = x[0] * 1e6  # Convert meters to micrometers
        for layer in self.neuroglancer_state.get("layers", []):
            if layer.get("type") != "annotation":
                continue

            layer_name = layer.get("name", "")
            annotations = layer.get("annotations") or []
            description = "NA"
            for annotation in annotations:
                annotation_type = annotation.get("type")

                if annotation_type == "volume" and annotation.get("id") is not None:
                    volume_id = annotation["id"]
                    description = annotation.get("description", "NA")
                    volume_layers.append((layer_name, volume_id, description))

                elif annotation_type == "polygon":
                    polygon_id = annotation.get("id")
                    parent_id = annotation.get("parentAnnotationId")

                    if polygon_id is not None:
                        polygons_by_id[polygon_id] = annotation

                        if parent_id is not None:
                            polygon_ids_by_volume[parent_id].append(polygon_id)

                elif annotation_type == "line":
                    parent_id = annotation.get("parentAnnotationId")
                    point = annotation.get("pointA")

                    if (
                        parent_id is not None
                        and point is not None
                        and len(point) >= 3
                    ):
                        lines_by_polygon[parent_id].append(point)

                elif annotation_type == "point":
                    point = annotation.get("point")

                    if point is not None and len(point) >= 3:
                        # Group points by their originating cloud layer.
                        # The group is created below from the layer's
                        # annotation list to retain empty cloud layers too.
                        pass
                elif annotation_type == "cloud":
                    cloud_id = annotation.get("id")
                    if cloud_id is None:
                        continue
                    cloud_points = [
                        a["point"]
                        for a in annotations
                        if a.get("type") == "point"
                        and a.get("point") is not None
                        and a.get("parentAnnotationId") == cloud_id
                    ]
                    descriptions = [row["description"] for row in annotations if "description" in row 
                        and 'type' in row 
                        and row['type'] == 'cloud'
                        and row['id'] == cloud_id]
                    if len(descriptions) == 0:
                        descriptions = 'unlabeled cloud'
                    else:
                        descriptions = descriptions[0].replace('\n', ', ')

                    cloud_layers.append((layer_name, descriptions, cloud_points))

        # Convert each cloud to a NumPy array once, in physical XY units.
        prepared_clouds = []

        for cloud_layer_name, cloud_name, cloud_points in cloud_layers:
            if cloud_points:
                points_array = np.asarray(cloud_points, dtype=np.float64)
                points_xy = points_array[:, :2] * xy_resolution
                points_z = points_array[:, 2]
            else:
                points_xy = np.empty((0, 2), dtype=np.float64)
                points_z = np.empty(0, dtype=np.float64)

            prepared_clouds.append((cloud_layer_name, cloud_name, points_xy, points_z))
            print(f"Prepared cloud layer '{cloud_layer_name}:{cloud_name}' with {len(points_xy)} points.")


        rows = []

        # Process only polygons belonging to each volume.
        for layer_name, volume_id, description in volume_layers:
            for polygon_id in polygon_ids_by_volume.get(volume_id, []):
                lines = lines_by_polygon.get(polygon_id, [])

                if not lines:
                    continue

                line_array = np.asarray(lines, dtype=np.float64)
                polygon_xy = line_array[:, :2] * xy_resolution

                section_value = line_array[0, 2]
                section_number = int(section_value - 0.5)
                area = polygon_area(polygon_xy)

                for cloud_layer_name, cloud_name, cloud_xy, cloud_z in prepared_clouds:
                    # Select only cloud points on this polygon's section.
                    section_mask = cloud_z == section_value
                    section_points = cloud_xy[section_mask]

                    #on_section = int(np.count_nonzero(cloud_z == section_value))
                    on_section = int(np.count_nonzero(section_mask))

                    # Count only points on this section that fall inside the polygon.
                    in_region = count_points_in_polygon(
                        section_points,
                        polygon_xy,
                    )

                    rows.append({
                        "Layer": layer_name,
                        "Volume": description,
                        "Section": section_number,
                        "Lines": len(lines),
                        "Area": area,
                        "Cloud": f'{cloud_layer_name}: {cloud_name}',
                        "cloud_points_on_section": on_section,
                        "cloud_points_in_region": in_region,
                    })
        OUTPUT_COLUMNS = [
            "Layer",
            "Volume",
            "Section",
            "Lines",
            "Area",
            "Cloud",
            "cloud_points_on_section",
            "cloud_points_in_region",
        ]        

        result = pd.DataFrame.from_records(rows, columns=OUTPUT_COLUMNS)
        result["Area"] = result["Area"].map("{:,.0f}".format)
        result.sort_values(by=['Layer', 'Volume', 'Section', 'Cloud'], inplace=True)

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

class NeuroglancerLog(models.Model):
    """This class model is for the logs associated with a Neuroglancer view.
    """
    
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, db_column="FK_user_id",
                               verbose_name="User", blank=False, null=False)
    state = models.ForeignKey(NeuroglancerState, models.CASCADE, db_column="FK_state_id",
                               verbose_name="Neuroglancer state", blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)
    note = models.TextField(max_length=2001, blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'neuroglancer_log'
        verbose_name = 'Neuroglancer log'
        verbose_name_plural = 'Neuroglancer logs'

    @property
    def username(self):
        return self.owner.username

    def __str__(self):
        return f'{self.note}'

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
                               verbose_name="Annotator", blank=False, null=False, related_name="annotator")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, db_column="FK_updated_by_id",
                               verbose_name="Updated by", blank=True, null=True, related_name="updated_by")
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

def polygon_area(points):
    """
    Calculate the area of an irregular polygon using the Shoelace formula.
    
    :param points: List of (x, y) coordinate tuples ordered clockwise or counter-clockwise.
    :return: Float representing the area of the polygon.
    """
    n = len(points)
    if n < 3:
        raise ValueError("A polygon must have at least 3 points.")
    
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]  # Wrap around to the first point
        area += (x1 * y2) - (y1 * x2)
        
    return abs(area) / 2.0

def get_annotation_type(annotations):
    volume_ids = [row['id'] for row in annotations if "id" in row and 'type' in row and row['type'] == 'volume']
    return 'volume' if volume_ids else 'cloud' if any(row['type'] == 'cloud' for row in annotations) else 'point'

def get_cloud_points_in_section(cloud_points, section):
    arr = np.array(cloud_points)
    return np.sum(arr[:, -1] == section)

def count_points_in_polygon(cloud_points, polygon, xy_resolution=1):
    """
    Counts how many points fall within a polygon using ray casting.
    
    :param cloud_points: List of tuples/lists, e.g., [(x1, y1, z1), (x2, y2, z2), ...]
    :param polygon: List of tuples/lists defining the vertices, e.g., [(x1, y1), ...]
    :param xy_resolution: Resolution for x and y coordinates
    """
    count = 0
    num_vertices = len(polygon)
    
    for px, py in cloud_points:
        px *= xy_resolution
        py *= xy_resolution
        inside = False
        p1x, p1y = polygon[0]
        
        for i in range(num_vertices + 1):
            p2x, p2y = polygon[i % num_vertices]
            
            # Check if the point is within the y-bounds of the edge
            if py > min(p1y, p2y) and py <= max(p1y, p2y):
                # Check if the point is to the left of the edge intersection
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        x_intersection = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or px <= x_intersection:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        if inside:
            count += 1
            
    return count
