"""Some important static methods used throughout the Django project.
"""
import decimal
import json
import numpy as np
import os
from neuroglancer.models import BrainRegion
from brain.models import Animal, ScanRun
import logging
from django.conf import settings
from brain_atlas_toolkit import graph_tools
logging.basicConfig()
logger = logging.getLogger(__name__)
MANUAL = 1
CORRECTED = 2


def align_atlas(animal, annotator_id, source, reverse=False, reference_scales=None):
    """This prepares the data for the align_point_sets method.
    Make sure we have at least 3 points

    :param animal: the animal we are aligning to
    :param input_type_id: the int defining what type of input. Taken from the
        input_type table with  column=id
    :param owner_id: the int defining the person. Taken from the auth_user
        table column=id
    :return: a 3x3 matrix and a 1x3 matrix
    """
    atlas_centers = get_annotation_dict('atlas', 16, 'MANUAL')
    reference_centers = get_annotation_dict(animal, annotator_id, source)
    try:
        scanRun = ScanRun.objects.get(prep__prep_id=animal)
    except ScanRun.DoesNotExist:
        scanRun = None
    if len(reference_centers) > 2 and scanRun is not None:
        if reference_scales is None:
            resolution = scanRun.resolution
            reference_scales = (resolution, resolution, scanRun.zresolution)
        brain_regions = sorted(reference_centers.keys())
        common_keys = atlas_centers.keys() & reference_centers.keys()
        dst_point_set = np.array([atlas_centers[s] for s in brain_regions if s in common_keys]).T
        src_point_set = np.array([reference_centers[s] for s in brain_regions if s in common_keys]).T
        if reverse:
            copy = dst_point_set
            dst_point_set = src_point_set
            src_point_set = copy
        R, t = umeyama(src_point_set, dst_point_set)
        t = t / np.array([reference_scales]).T # production version
    else:
        R = np.eye(3)
        t = np.zeros((3,1))
    return R, t


def get_scales(prep_id):
    """A generic method to safely query and return resolutions.
    Note, since prep_id is a varchar, you can't use objects.get, you must use objects.filter

    :param prep_id: varchar of the primary key of the animal
    """

    query_set = ScanRun.objects.filter(prep_id=prep_id)

    if query_set is not None and len(query_set) > 0:
        scan_run = query_set[0]
        scale_xy = scan_run.resolution
        z_scale = scan_run.zresolution
    else:
        scale_xy = 1
        z_scale = 1
    return scale_xy, z_scale



def brain_to_atlas_transform(brain_coord, r, t):
    """Taken from abakit
    Takes an x,y,z brain coordinates, and a rotation matrix and translation vector.
    
    :param atlas_coord: tuple of x,y,z coordinates of the atlas in micrometers
    :param r: float of the rotation matrix
    :param t: vector of the translation matrix
    :return: the point in atlas coordinates in micrometers.
    """
    # Transform brain coordinates to physical space
    brain_coord = np.array(brain_coord).reshape(3, 1) # Convert to a column vector
    atlas_coord = r @ brain_coord + t
    return atlas_coord.T[0] # Convert back to a row vector


def umeyama(src, dst, with_scaling=True):
    """The Umeyama algorithm to register landmarks with rigid transform.

    See the paper 'Least-squares estimation of transformation parameters
    between two point patterns'.

    :param src: List of data points.
    :param dst: List of data points.
    :param with_scaling: A boolean determining if we should scale or not.
    """
    src = (np.array(src)).astype(np.float64)
    dst = (np.array(dst)).astype(np.float64)
    assert src.shape == dst.shape
    assert len(src.shape) == 2
    m, n = src.shape

    src_mean = np.mean(src, axis=1).reshape(-1, 1)
    dst_mean = np.mean(dst, axis=1).reshape(-1, 1)

    src_demean = src - src_mean
    dst_demean = dst - dst_mean

    u, s, vh = np.linalg.svd(dst_demean @ src_demean.T / n)

    # deal with reflection
    e = np.ones(m)
    if np.linalg.det(u) * np.linalg.det(vh) < 0:
        print("reflection detected")
        e[-1] = -1

    r = u @ np.diag(e) @ vh

    if with_scaling:
        src_var = (src_demean ** 2).sum(axis=0).mean()
        c = sum(s * e) / src_var
        r *= c

    t = dst_mean - r @ src_mean

    return r, t


def make_ontology_graph_CCFv3():
    """
    Load the allen CCFv3 ontology into a graph object
    """
    allen_ontology_file = os.path.join(settings.STATIC_ROOT,'neuroglancer/allen.json')
    with open(allen_ontology_file,'r') as infile:
        ontology_dict = json.load(infile)
    graph = graph_tools.Graph(ontology_dict)
    return graph

def make_ontology_graph_pma():
    """
    Load the Princeton Mouse Atlas ontology into a graph object
    """
    pma_ontology_file = os.path.join(settings.STATIC_ROOT,'neuroglancer/pma.json')
    with open(pma_ontology_file,'r') as infile:
        ontology_dict = json.load(infile)
    graph = graph_tools.Graph(ontology_dict)
    return graph

