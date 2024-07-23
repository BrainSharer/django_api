from collections import defaultdict
import numpy as np
import os
from cloudvolume import CloudVolume
import cv2
from scipy.interpolate import splev, splprep
from django.db.models import Count

from brain.models import ScanRun
from neuroglancer.contours.ng_segment_maker import NgConverter
from neuroglancer.models import AnnotationLabel, AnnotationSession
from neuroglancer.models import DEBUG


M_UM_SCALE = 1000000
COLOR = 1

def get_label_ids(label: str):

    labels = label.split('\n')
    labels = [label.strip() for label in labels]
    if DEBUG:
        print(f'labels: {labels} type={type(labels)} len={len(labels)}')

    try:
        label_objects = AnnotationLabel.objects.filter(label__in=labels)
    except AnnotationLabel.DoesNotExist:
        return []

    return [label.id for label in label_objects]


def get_exact_match(model_class, m2m_field, ids):
    """
    Retrieves instances of the given `model_class` that have an exact match
    for the provided `ids` in the many-to-many field `m2m_field`.
    https://stackoverflow.com/questions/5301996/how-to-do-many-to-many-django-query-to-find-book-with-2-given-authors

    Args:
        model_class (class): The model class to query.
        m2m_field (str): The name of the many-to-many field to filter on.
        ids (list): A list of IDs to match in the many-to-many field.

    Returns:
        QuerySet: A queryset containing instances of `model_class` that have
        an exact match for the provided `ids` in the many-to-many field `m2m_field`.
    """
    query = model_class.objects.annotate(count=Count(m2m_field))\
                .filter(count=len(ids))
    for _id in ids:
        query = query.filter(**{m2m_field: _id})
    return query

def get_session(request_data: dict):
    """
    Retrieves an annotation session based on the provided request data.

    Args:
        request_data (dict): A dictionary containing the request data.

    Returns:
        AnnotationSession: The retrieved annotation session.

    """
    annotation_session = None
    if 'id' in request_data and isinstance(request_data.get('id'), str) and request_data.get('id').isdigit():
        ## We simply get the annotation session based on its ID
        id = int(request_data.get('id'))
        try:
            annotation_session = AnnotationSession.objects.get(pk=id)
        except AnnotationSession.DoesNotExist:
            annotation_session = None

    if annotation_session is not None:
        return annotation_session
    else:
        animal = request_data.get('animal')
        label = request_data.get('label')
        annotator = request_data.get('annotator')
        annotation_session = None

        labels = label.split('\n')
        if DEBUG:
            print(f'labels: {labels} type={type(labels)} len={len(labels)}')

        try:
            label_objects = AnnotationLabel.objects.filter(label__in=labels)
        except AnnotationLabel.DoesNotExist:
            print('error')

        label_ids = [label.id for label in label_objects]

        matches = get_exact_match(AnnotationSession, 'labels', label_ids)

        annotation_session = matches.filter(active=True)\
            .filter(animal=animal)\
            .filter(annotator=annotator)\
            .order_by('-created').first()
        
        if DEBUG:
            print(f"get_session: animal: {animal}, label: {label}, annotator: {annotator} label IDS: {label_ids}")

            
    return annotation_session


class AnnotationSessionManager():
    """
    A class that manages annotation sessions and provides methods for creating polygons and volumes.

    Attributes:
        resolution (float): The resolution of the scan run.
        isotropic (int): The isotropic value for the volume.
        downsample_factor (float): The downsample factor for the volume.
        zresolution (int): The z-resolution of the volume.
        label (str): The label associated with the annotation session.
        color (int): The color value associated with the label.

    Methods:
        create_polygons(data: dict) -> dict:
            Creates a dictionary of polygons from the given data.

        create_volume(polygons, origin, section_size) -> numpy.ndarray:
            Creates a volume from a collection of polygons.

        get_origin_and_section_size(structure_contours) -> Tuple[numpy.ndarray, numpy.ndarray]:
            Calculates the origin and section size based on the given structure contours.

        create_segmentation_folder(volume, animal, label, offset) -> str:
            Creates a segmentation folder for a given volume, animal, label, and offset.

        fetch_color_by_label(label) -> int:
            Fetches the color value associated with the given label.
    """

    def __init__(self, scan_run: ScanRun, label: str) -> None:
        self.resolution = scan_run.resolution
        self.isotropic = 10 # set volume to be isotropic @ 10um
        self.downsample_factor = self.isotropic / self.resolution 
        self.zresolution = self.isotropic
        self.label = label

        self.color = self.fetch_color_by_label(self.label)


    def create_polygons(self, data: dict):
        """
        This gets the row data from the annnotation_session table and creates a dictionary of polygons.
        This dictionary is then used to create a volume.

        Args:
            data (dict): The data containing polygon information.
            self.resolution (float): The scale factor for x and y coordinates.

        Returns:
            dict: A dictionary containing the polygons grouped by section.

        """
        polygons = defaultdict(list)
        # first test data to make sure it has the right keys    
        try:
            polygon_data = data['childJsons']
        except KeyError:
            return "No childJsons key in data. Check the data you are sending."
        
        for polygon in polygon_data:
            try:
                lines = polygon['childJsons']
            except KeyError:
                return "No data. Check the data you are sending."
            x0,y0,z0 = lines[0]['pointA']
            x0 = x0 * M_UM_SCALE / self.resolution / self.downsample_factor
            y0 = y0 * M_UM_SCALE / self.resolution / self.downsample_factor
            z0 = int(round(z0 * M_UM_SCALE / self.zresolution))
            for line in lines:
                x,y,z = line['pointA']
                x = x * M_UM_SCALE / self.resolution / self.downsample_factor
                y = y * M_UM_SCALE / self.resolution / self.downsample_factor
                z = z * M_UM_SCALE / 10
                xy = (x, y)
                section = int(np.round(z))
                polygons[section].append(xy)
            polygons[z0].append((x0, y0))

        _min = min(polygons.keys())
        _max = max(polygons.keys())
        points = []
        for expanded_section in range(_min, _max):
            if expanded_section in polygons.keys():
                points.append(polygons[expanded_section])
            else:
                polygons[expanded_section] = polygons[expanded_section - 1]
        
        return polygons


    def create_volume(self, polygons, origin, section_size):
        """
        Create a volume from a collection of polygons. Each section contains a polygon which is composed of a list of lines.
        Each line is composed of two points. All these points are fetched in the correct order and used to create the volume.
        Create an isotropic volume at 10um. @ delta Z / 2 
        
        Here are the steps:
            1. For each section get the points of the polygon

            2. Subtract the origin from the points so we create a box the size of the biggest polygon

            3. Create a slice of the volume with the size of the section

            4. Draw the polygon on the slice with opencv

            5. Append the slice to the volume (box)

            6. Return an array of integers (0 and 1s)


        Args:
            polygons (dict): A dictionary of polygons, where the keys are polygon IDs and the values are lists of points.
            origin (tuple): The origin of the volume.
            section_size (tuple): The size of the sections in the volume.

        Returns:
            numpy.ndarray: The created volume as a 3D numpy array.

        """
        volume = []
        for _, points in sorted(polygons.items()):
            points = np.array(points) - origin[:2]
            points = (points).astype(np.int32)
            volume_slice = np.zeros(section_size, dtype=np.uint16)
            volume_slice = cv2.polylines(volume_slice, [points], isClosed=True, color=self.color, thickness=1)
            volume_slice = cv2.fillPoly(volume_slice, pts=[points], color=self.color)
            volume.append(volume_slice)
        volume = np.array(volume)
        volume = np.swapaxes(volume, 0, 2)
        return volume.astype(np.uint16)


    def get_origin_and_section_size(self, structure_contours):
        """
        Calculate the origin and section size based on the given structure contours.

        Parameters:
        - structure_contours: dict
        A dictionary containing structure contours, where the keys are section numbers and the values are lists of points.

        Returns:
        - origin: numpy.ndarray
        An array representing the origin of the section, in the format [x, y, z].
        - section_size: numpy.ndarray
        An array representing the size of the section, in the format [width, height].
        """
        section_mins = []
        section_maxs = []
        for _, points in structure_contours.items():
            points = np.array(points)
            section_mins.append(np.min(points, axis=0))
            section_maxs.append(np.max(points, axis=0))
        min_z = min([int(i) for i in structure_contours.keys()])
        min_x, min_y = np.min(section_mins, axis=0)
        max_x, max_y = np.max(section_maxs, axis=0)

        xspan = max_x - min_x
        yspan = max_y - min_y
        origin = np.array([min_x, min_y, min_z])
        # flipped yspan and xspan 19 Oct 2023
        section_size = np.array([yspan, xspan]).astype(int)
        return origin, section_size


    def create_segmentation_folder(self, volume, animal, label, offset):
        """
        Creates a segmentation folder for a given volume, animal, label, and offset.

        Args:
            volume (str): The volume to be used for segmentation.
            animal (str): The name of the animal.
            label (str): The label for the segmentation.
            offset (tuple): The offset for the segmentation.

        Returns:
            str: The name of the created folder.
        """
        folder_name = f'{animal}_{label}'
        path = '/var/www/brainsharer/structures'
        output_dir = os.path.join(path, folder_name)
        self.resolution = self.resolution * 1000 * self.downsample_factor  # neuroglancer wants it in nm
        self.zresolution = self.zresolution * 1000
        scales = [int(self.resolution), int(self.resolution), int(self.zresolution)]

        maker = NgConverter(volume=volume, scales=scales, offset=offset)
        segment_properties = {self.color: label}
        maker.reset_output_path(output_dir)
        maker.init_precomputed(output_dir)

        cloudpath = f'file://{output_dir}'
        cloud_volume = CloudVolume(cloudpath, 0)
        maker.add_segment_properties(cloud_volume=cloud_volume, segment_properties=segment_properties)
        maker.add_segmentation_mesh(cloud_volume.layer_cloudpath, mip=0)
        return folder_name
    
    @staticmethod
    def fetch_color_by_label(label):
        """
        Fetches the color associated with a given label.

        Args:
            label (str): The label for which to fetch the color.

        Returns:
            int: The color associated with the label. If the label is not found in the `allen_structures` dictionary,
                 the default color is returned.

        """
        allen_structures = {
            'SC': 851,
            'IC': 811,
            'AP': 207,
            'RtTg': 146,
            'SNR_L': 381,
            'SNR_R': 381,
            'PBG_L': 874,
            'PBG_R': 874,
            '3N_L': 35,
            '3N_R': 35,
            '4N_L': 115,
            '4N_R': 115,
            'SNC_L': 374,
            'SNC_R': 374,
            'VLL_L': 612,
            'VLL_R': 612,
            '5N_L': 621,
            '5N_R': 621,
            'LC_L': 147,
            'LC_R': 147,
            'DC_L': 96,
            'DC_R': 96,
            'Sp5C_L': 429,
            'Sp5C_R': 429,
            'Sp5I_L': 437,
            'Sp5I_R': 437,
            'Sp5O_L': 445,
            'Sp5O_R': 445,
            '6N_L': 653,
            '6N_R': 653,
            '7N_L': 661,
            '7N_R': 661,
            '7n_L': 798,
            '7n_R': 798,
            'Amb_L': 135,
            'Amb_R': 135,
            'LRt_L': 235,
            'LRt_R': 235,
        }   
        color = 1
        return allen_structures.get(str(label), color)

def interpolate2d(points, new_len):
    """Interpolates a list of tuples to the specified length. The points param
    must be a list of tuples in 2d
    
    :param points: list of floats
    :param new_len: integer you want to interpolate to. This will be the new length of the array
    There can't be any consecutive identical points or an error will be thrown
    unique_rows = np.unique(original_array, axis=0)
    """

    pu = np.array(points, dtype=np.float64)
    indexes = np.unique(pu, axis=0, return_index=True)[1]
    points = np.array([points[index] for index in sorted(indexes)])

    tck, u = splprep(points.T, u=None, s=3, per=1)
    u_new = np.linspace(u.min(), u.max(), new_len)
    x_array, y_array = splev(u_new, tck, der=0)
    arr_2d = np.concatenate([x_array[:, None], y_array[:, None]], axis=1)
    return arr_2d
