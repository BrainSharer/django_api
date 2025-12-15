from collections import defaultdict
import shutil
import numpy as np
import os
from cloudvolume import CloudVolume
import cv2
import scipy.interpolate as si
from skimage.filters import gaussian
from django.db.models import Count
from scipy.interpolate import interp1d
from scipy.spatial import cKDTree
import bisect

from brain.models import ScanRun
from neuroglancer.contours.ng_segment_maker import NgConverter
from neuroglancer.models import AnnotationLabel, AnnotationSession
from neuroglancer.models import DEBUG


M_UM_SCALE = 1000000
COLOR = 1
ISOTROPIC = 10  # set volume to be isotropic @ 10um

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
        xy_resolution (float): The resolution of the scan run.
        downsample_factor (float): The downsample factor for the volume.
        z_resolution (int): The z-resolution of the volume.
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
        # 4 lines below are from Aug 4 2025
        self.resolution = scan_run.resolution
        self.isotropic = ISOTROPIC # set volume to be isotropic @ 10um
        self.downsample_factor = self.isotropic / self.resolution 
        self.label = label
        self.color = self.fetch_color_by_label(self.label)
        print(f'AnnotationSessionManager init: resolution: {self.resolution}, isotropic: {self.isotropic}, downsample_factor: {self.downsample_factor}')

    def create_polygons(self, data: dict, interpolate: int = 0) -> dict:
        """
        This gets the row data from the annnotation_session table and creates a dictionary of polygons.
        This dictionary is then used to create a volume.

        Args:
            data (dict): The data containing polygon information.
            self.xy_resolution (float): The scale factor for x and y coordinates.

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
            # aug 4 changes
            #####TODOx0 = x0 * M_UM_SCALE / self.resolution / self.downsample_factor
            #####TODOy0 = y0 * M_UM_SCALE / self.resolution / self.downsample_factor
            x0 = x0 * M_UM_SCALE / self.isotropic
            y0 = y0 * M_UM_SCALE / self.isotropic
            z0 = int(round(z0 * M_UM_SCALE / self.isotropic))
            
            for line in lines:
                x,y,z = line['pointA']
                # aug 4 changes
                #####TODOx = x * M_UM_SCALE / self.resolution / self.downsample_factor
                #####TODOy = y * M_UM_SCALE / self.resolution / self.downsample_factor
                x = x * M_UM_SCALE / self.isotropic
                y = y * M_UM_SCALE / self.isotropic
                z = z * M_UM_SCALE / self.isotropic
                xy = (x, y)
                section = int(np.round(z))
                polygons[section].append(xy)
            polygons[z0].append((x0, y0))

        _min = min(polygons.keys())
        _max = max(polygons.keys())
        section_range = range(_min, _max)
        keys = sorted(polygons.keys())
        lpoints = max([len(polygons[k]) for k in keys]) * 10
        # Now either pad or interpolate
        if interpolate:
            print(f'Interpolating polygons to have at least {lpoints} points each.')
            for i in section_range:
                if i not in keys:
                    # find surrounding keys
                    idx = bisect.bisect_left(keys, i)

                    # handle bounds safely
                    if idx == 0:
                        value = polygons[keys[0]]
                    elif idx == len(keys):
                        value = polygons[keys[-1]]
                    else:
                        k0, k1 = keys[idx - 1], keys[idx]
                        v0, v1 = np.array(polygons[k0]), np.array(polygons[k1])
                        v0 = self.bspliner(v0, lpoints, degree=3)
                        v1 = self.bspliner(v1, lpoints, degree=3)
                        # linear interpolation
                        t = (i - k0) / (k1 - k0)
                        value = v0 + t * (v1 - v0)
                    polygons[i] = value
        else:
            for expanded_section in section_range:
                if expanded_section in keys:
                    points = self.bspliner(polygons[expanded_section], lpoints, degree=3)
                    polygons[expanded_section] = points
                else:
                    points = self.bspliner(polygons[expanded_section - 1], lpoints, degree=3)
                    polygons[expanded_section] = points


        return polygons

    def create_volume(self, polygons, origin, section_size, stdDevX=1.0, stdDevY=1.0, stdDevZ=1.0):
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
        volume = np.swapaxes(volume, 0, 2) # put it in x,y,z format
        if DEBUG:
            print(f'Volume shape before gaussian: {volume.shape} dtype={volume.dtype} with parameters stdDevX: {stdDevX}, stdDevY: {stdDevY}, stdDevZ: {stdDevZ}')
        volume = gaussian(volume, [stdDevX, stdDevY, stdDevZ])  # this is a float array
        volume[volume > 0] = self.color
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
        If the folder already exists, it will delete it and recreate it. We might
        want to change this to just return the existing folder_name

        Args:
            volume (str): The volume to be used for segmentation.
            animal (str): The name of the animal.
            label (str): The label for the segmentation.
            offset (tuple): The offset for the segmentation.

        Returns:
            str: The name of the created folder.
        """
        if (isinstance(label, AnnotationLabel)) and label is not None:
            label = label.label

        label = str(label).replace(' ', '_')
        folder_name = f'{animal}_{label}'
        path = '/var/www/brainsharer/structures'
        output_dir = os.path.join(path, folder_name)
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        self.resolution = self.resolution * 1000 * self.downsample_factor  # neuroglancer wants it in nm
        #####TODO rm self.zresolution = self.zresolution * 1000
        scales = [int(self.resolution), int(self.resolution), int(self.isotropic * 1000)]

        # Neuroglancer wants the scales in nanometers so we multiply by 1000
        #TODOscales = [int(self.xy_resolution * 1000), int(self.xy_resolution * 1000), int(self.z_resolution * 1000)]

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

    @staticmethod
    def bspliner(cv, n=100, degree=3):
        """
        Generate a B-spline curve from a set of polygon points.

        Parameters:
        cv (array-like): Array of control vertices.
        n (int, optional): Number of points to generate along the B-spline curve. Default is 100.
        degree (int, optional): Degree of the B-spline. Default is 3.

        Returns:
        numpy.ndarray: Array of points representing the B-spline curve.
        """

        cv = np.asarray(cv)
        count = len(cv)
        degree = np.clip(degree,1,count-1)

        # Calculate knot vector
        kv = np.concatenate(([0]*degree, np.arange(count-degree+1), [count-degree]*degree))

        # Calculate query range
        u = np.linspace(False,(count-degree),n)

        # Calculate result
        return np.array(si.splev(u, (kv,cv.T,degree))).T   

    @staticmethod
    def cumulative_length(points):
        """Return cumulative arc length of an ordered point list."""
        pts = np.asarray(points)
        diffs = np.diff(pts, axis=0)
        seg_lengths = np.linalg.norm(diffs, axis=1)
        cum_length = np.concatenate([[0], np.cumsum(seg_lengths)])
        return cum_length / cum_length[-1]  # normalize to [0,1]

    @staticmethod
    def resample_curve(points, num_samples):
        """Resample an ordered curve to a fixed number of points."""
        pts = np.asarray(points)
        t = AnnotationSessionManager.cumulative_length(pts)
        
        fx = interp1d(t, pts[:, 0], kind='linear')
        fy = interp1d(t, pts[:, 1], kind='linear')

        t_new = np.linspace(0, 1, num_samples)
        return np.column_stack((fx(t_new), fy(t_new)))

    @staticmethod
    def interpolate_slices(polygons, num_interp=1):
        """
        polygons: dict[z] = Nx2 array of points.
        num_interp:   number of interpolated slices between neighbors.

        Returns:
            dict[z] = Nx2 array of points.
        """
        z_values = list(polygons.keys())
        slice_points = [polygons[z] for z in z_values]


        # Find a common number of points across all slices
        n_common = max(len(pts) for pts in slice_points)

        # Step 1: resample all slices to same number of points
        resampled = [AnnotationSessionManager.resample_curve(pts, n_common) for pts in slice_points]

        output = {}

        # Insert original slices
        for z, pts in zip(z_values, resampled):
            output[z] = pts

        # Step 2: interpolate between slices
        for i in range(len(z_values) - 1):
            z0, z1 = z_values[i], z_values[i+1]
            p0, p1 = resampled[i], resampled[i+1]

            for k in range(1, num_interp + 1):
                t = k / (num_interp + 1)
                z_new = z0 + (z1 - z0) * t
                pts_new = (1 - t) * p0 + t * p1
                output[z_new] = pts_new

        # Return sorted dictionary by z
        return dict(sorted(output.items()))

def match_points(sliceA, sliceB, max_dist=None):
    """
    Match points from sliceA to sliceB using nearest-neighbor matching.
    sliceA, sliceB: (N,2) arrays
    Returns list of tuples: [(iA, iB), ...]
    """

    if len(sliceA) == 0 or len(sliceB) == 0:
        return []

    tree = cKDTree(sliceB)
    dists, idxs = tree.query(sliceA)

    matches = []
    for iA, (d,iB) in enumerate(zip(dists, idxs)):
        if max_dist is None or d <= max_dist:
            matches.append((iA, iB))

    return matches


def interpolate_between_slices(z0, pts0, z1, pts1, num_interp=1):
    """
    Linearly interpolate point pairs between z0 and z1.
    Returns dict of z → array of interpolated points.
    """

    matches = match_points(pts0, pts1)

    interpolated = {}

    # Determine the z values to fill between
    z_vals = np.linspace(z0, z1, num_interp + 2)[1:-1]  # skip endpoints

    for z in z_vals:
        alpha = (z - z0) / (z1 - z0)
        interp_pts = []

        for i0, i1 in matches:
            p0 = pts0[i0]
            p1 = pts1[i1]
            pz = (1 - alpha) * p0 + alpha * p1
            interp_pts.append(pz)

        #interpolated[z] = np.vstack(interp_pts) if interp_pts else np.zeros((0,2))
        #interpolated = np.vstack(interp_pts)
    return interp_pts