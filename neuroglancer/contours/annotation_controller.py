"""This package handles the conversion of polygon points to neuroglancer json state and vise versa
"""

import numpy as np
from statistics import mode
from scipy.interpolate import splprep, splev
from neuroglancer.annotation_layer import random_string
hexcolor = "#FF0000"

def next_item(odic, key):
    try:
        k = list(odic)[list(odic.keys()).index(key) + 1]
        result = odic[k]
    except IndexError:
        result = next(iter(odic.values()))
    return result 


def create_polygons(rows, description=None) -> list:
    """
    Takes all the polygon x,y,z data and turns them into
    Neuroglancer polygons
    :param rows: list of object PolygonSequence
    
    """
    polygon_index_to_id = {}
    volumes = {}
    annotation_layer_json = []
    volume_id = random_string()

    for row in rows:
        if row.polygon_index not in polygon_index_to_id:
            polygon_index_to_id[row.polygon_index] = random_string()

        polygon_id = polygon_index_to_id[row.polygon_index]
        if volume_id not in volumes:
            volumes[volume_id] = {}
        if polygon_id not in volumes[volume_id]:
            volumes[volume_id][polygon_id] = []
        volumes[volume_id][polygon_id].append(row)

    for volume_id, polygons_in_volume in volumes.items():      
        for polygon_id, polygon_points in polygons_in_volume.items():   
            volumes[volume_id][polygon_id] = sort_polygon_points_and_get_coordinates(polygon_points)

    for volume_id, polygons in volumes.items():
        annotation_layer_json += create_volume_json(volume_id, polygons, description = description) # does not use polygon_index
    
    return annotation_layer_json



def create_volume_json(volume_id, polygons, description = None):
    """_summary_

    Args:
        volume_id (_type_): _description_
        polygons (_type_): _description_
        i (_type_): _description_

    Returns:
        _type_: _description_
    """

    volume_json = []
    one_point = list(polygons.values())[0][0] 
    parent_annotataions, _ = create_parent_annotation_json(len(polygons), volume_id, one_point, _type='volume', child_ids=list(polygons.keys()),description=description)
    volume_json.append(parent_annotataions)
    for polygon_id, polygon_points in polygons.items(): 
        volume_json += create_polygon_json(polygon_id, polygon_points,parent_id=volume_id)
    return volume_json


def parse_polygon_points(polygon_points):
    """This takes a list of query results from the annotations_points table or the polygon sequence 
    table and group them into dictionaries according to their grouping of polygons and values.  
    points are grouped into polygons, and polygons are grouped into volumes
    TODO  This function seems to rely on the fact that points are ordered by the ordering column in the database.  
    This need to be improved to resolve potential bugs

    :param polygon_points (list): list of query results from the annotations points table or the polygon sequence table

    :return polygons[dict]: dictionary polygons indexed by the polygon id, those are annotation points entry without a volume_id column
    :return volumes[dict]: dictionary of volumes, indexed by the volume id.  the value corresponding to each id is the same as the polygon id
    """

    polygons = {}
    volumes = {}
    for point in polygon_points:
        polygon_id = point.polygon_id
        if point.volume_id is not None:
            volume_id = point.volume_id
            if not volume_id in volumes:
                volumes[volume_id] = {}
            if not polygon_id in volumes[volume_id]:
                volumes[volume_id][polygon_id] = []
            volumes[volume_id][polygon_id].append(point)
        else:
            if not polygon_id in polygons:
                polygons[polygon_id] = []
            polygons[polygon_id].append(point)
    for polygon_id, polygon_points in polygons.items(): 
        polygons[polygon_id] = sort_polygon_points_and_get_coordinates(polygon_points)
    for volume_id, polygons_in_vloume in volumes.items():      
        for polygon_id, polygon_points in polygons_in_vloume.items():   
            volumes[volume_id][polygon_id] = sort_polygon_points_and_get_coordinates(polygon_points)
    return polygons, volumes

def sort_polygon_points_and_get_coordinates(polygon_points):
    polygon_points = np.array(polygon_points)
    orders = [i.point_order for i in polygon_points]
    sort_id = np.argsort(orders)
    polygon_points = polygon_points[sort_id]
    return [[i.x, i.y, i.z] for i in polygon_points]

def create_parent_annotation_json(npoints, id, source, _type, child_ids=None,parent_id = None, description = None):
    """create the json entry for a parent annotation.  The parent annotation need to have a 
    specific id and the list of id for all the children

    Args:
        npoints (int): number of points in this parent annotation
        parent_id (int): id of parent annotation
        source (list of x,y,z): the source coordinate
        _type (string): annotation type: this could be polygon or volumes
        child_ids (list, optional): list of id of child annotations that belong to the parent annotation. Defaults to None.

    Returns:
        _type_: _description_
    """

    parent_annotation = {}
    if child_ids is None:
        child_ids = [random_string() for _ in range(npoints)]
    parent_annotation["source"] = source
    parent_annotation["childAnnotationIds"] = child_ids
    if parent_id is not None:
        parent_annotation["parentAnnotationId"] = parent_id
    if description is not None:
        parent_annotation["description"] = description
    parent_annotation["type"] = _type
    parent_annotation["id"] = id
    parent_annotation["props"] = [hexcolor]
    return parent_annotation, child_ids


def create_polygon_json(polygon_id, polygon_points,parent_id = None):
    """create the neuroglancer json state for polygon points

    Args:
        polygon_id (str): id of polygon
        polygon_points (list): list of coordinates of a polygon

    Returns:
        dict: the neuroglancer json for the polygon in python dictionary form
    """

    polygon_json = []
    npoints = len(polygon_points)
    parent_annotation, child_ids = create_parent_annotation_json(npoints, polygon_id, polygon_points[0], _type='polygon',parent_id=parent_id)
    polygon_json.append(parent_annotation)
    for point in range(npoints - 1):
        line = {}
        line["pointA"] = polygon_points[point]
        line["pointB"] = polygon_points[point + 1]
        line["type"] = "line"
        line["id"] = child_ids[point]
        line["parentAnnotationId"] = polygon_id
        line["props"] = [hexcolor]
        polygon_json.append(line)
    line = {}
    line["pointA"] = polygon_points[-1]
    line["pointB"] = polygon_points[0]
    line["type"] = "line"
    line["id"] = child_ids[-1]
    line["parentAnnotationId"] = polygon_id
    line["props"] = [hexcolor]
    polygon_json.append(line)
    return polygon_json

def interpolate2d(points, new_len):
    """Interpolates a list of tuples to the specified length. The points param
    must be a list of tuples in 2d
    
    :param points: list of floats
    :param new_len: integer you want to interpolate to. This will be the new length of the array
    There can't be any consecutive identical points or an error will be thrown
    unique_rows = np.unique(original_array, axis=0)
    """

    pu = points.astype(int)
    indexes = np.unique(pu, axis=0, return_index=True)[1]
    points = np.array([points[index] for index in sorted(indexes)])

    tck, u = splprep(points.T, u=None, s=3, per=1)
    u_new = np.linspace(u.min(), u.max(), new_len)
    x_array, y_array = splev(u_new, tck, der=0)
    arr_2d = np.concatenate([x_array[:, None], y_array[:, None]], axis=1)
    return arr_2d


def interpolate2dXXX(points:list, new_len:int) -> list:
    """Interpolates a list of tuples to the specified length. The points param
    must be a list of tuples in 2d
    
    :param points: list of floats
    :param new_len: integer you want to interpolate to. This will be the new length of the array
    There can't be any consecutive identical points or an error will be thrown
    unique_rows = np.unique(original_array, axis=0)
    """

    points = np.array(points)
    lastcolumn = np.round(points[:, -1])
    z = mode(lastcolumn)
    points2d = np.delete(points, -1, axis=1)
    pu = points2d.astype(int)
    indexes = np.unique(pu, axis=0, return_index=True)[1]
    points = np.array([points2d[index] for index in sorted(indexes)])
    addme = points2d[0].reshape(1, 2)
    points2d = np.concatenate((points2d, addme), axis=0)

    tck, u = splprep(points2d.T, u=None, s=3, per=1)
    u_new = np.linspace(u.min(), u.max(), new_len)
    x_array, y_array = splev(u_new, tck, der=0)
    arr_2d = np.concatenate([x_array[:, None], y_array[:, None]], axis=1)
    arr_3d = np.c_[ arr_2d, np.zeros(new_len) + z ] 
    return list(map(tuple, arr_3d))

 
def onSegment(p:tuple, q:tuple, r:tuple) -> bool:
    """Given three collinear points p, q, r, the function checks if point q lies on line segment 'pr' 
    
    :param p:
    :param q:
    :param r:
    """
     
    if ((q[0] <= max(p[0], r[0])) & 
        (q[0] >= min(p[0], r[0])) & 
        (q[1] <= max(p[1], r[1])) & 
        (q[1] >= min(p[1], r[1]))):
        return True
         
    return False

 
def orientation(p:tuple, q:tuple, r:tuple) -> int:
    """To find orientation of ordered triplet (p, q, r).
    # The function returns following values
    # 0 --> p, q and r are collinear
    # 1 --> Clockwise
    # 2 --> Counterclockwise
    
    :param p:
    :param q:
    :param r:
    """
     
    val = (((q[1] - p[1]) * 
            (r[0] - q[0])) - 
           ((q[0] - p[0]) * 
            (r[1] - q[1])))
            
    if val == 0:
        return 0
    if val > 0:
        return 1  # Collinear
    else:
        return 2  # Clock or counterclock

 
def doIntersect(p1, q1, p2, q2):
    """
    # Find the four orientations needed for 
    # general and special cases    
    
    :param p1:
    :param q1:
    :param p2:
    :param q2:
    """
     
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
 
    # General case
    if (o1 != o2) and (o3 != o4):
        return True
     
    # Special Cases
    # p1, q1 and p2 are collinear and
    # p2 lies on segment p1q1
    if (o1 == 0) and (onSegment(p1, p2, q1)):
        return True
 
    # p1, q1 and p2 are collinear and
    # q2 lies on segment p1q1
    if (o2 == 0) and (onSegment(p1, q2, q1)):
        return True
 
    # p2, q2 and p1 are collinear and
    # p1 lies on segment p2q2
    if (o3 == 0) and (onSegment(p2, p1, q2)):
        return True
 
    # p2, q2 and q1 are collinear and
    # q1 lies on segment p2q2
    if (o4 == 0) and (onSegment(p2, q1, q2)):
        return True
 
    return False

 
def is_inside_polygon(points:list) -> bool:
    """Returns true if the point p lies 
    # inside the polygon[] with n vertices    
    
    :param points:
    """
     
    n = len(points)
    coords = np.array(points)
    coords = np.unique(coords, axis=0)
    center = list(coords.mean(axis=0))
     
    # There must be at least 3 vertices
    # in polygon
    if n < 3:
        return False
         
    # Define Infinite (Using INT_MAX 
    # caused overflow problems)
    INT_MAX = 10000  # Create a point for line segment
    # from p to infinite
    extreme = (INT_MAX, center[1])
    count = i = 0
     
    while True:
        _next = (i + 1) % n
         
        # Check if the line segment from 'p' to 
        # 'extreme' intersects with the line 
        # segment from 'polygon[i]' to 'polygon[next]'
        if (doIntersect(points[i],
                        points[_next],
                        center, extreme)):
                             
            # If the point 'p' is collinear with line 
            # segment 'i-next', then check if it lies 
            # on segment. If it lies, return true, otherwise false
            if orientation(points[i], center,
                           points[_next]) == 0:
                return onSegment(points[i], center,
                                 points[_next])
                                  
            count += 1
             
        i = _next
         
        if (i == 0):
            break
         
    # Return true if count is odd, false otherwise
    return (count % 2 == 1)

def sort_from_center(polygon:list) -> list:
    """Get the center of the unique points in a polygon and then use math.atan2 to get
    the angle from the x-axis to the x,y point. Use that to sort.
    This only works with convex shaped polygons.
    
    :param polygon:
    """

    coords = np.array(polygon)
    coords = np.unique(coords, axis=0)
    center = coords.mean(axis=0)
    centered = coords - center
    angles = -np.arctan2(centered[:, 1], centered[:, 0])
    sorted_coords = coords[np.argsort(angles)]
    return list(map(tuple, sorted_coords))


def zCrossProduct(a, b, c):
    """Used in the in_convex function below
    
    :param a:
    :param b:
    :param c:
    """

    return (a[0] - b[0]) * (b[1] - c[1]) - (a[1] - b[1]) * (b[0] - c[0])


def is_convex(vertices:list) -> list:
    """Tests if a polygon has all convex angles
    
    :param vertices:
    """

    if len(vertices) < 4:
        return True
    signs = [zCrossProduct(a, b, c) > 0 for a, b, c in zip(vertices[2:], vertices[1:], vertices)]
    return all(signs) or not any(signs)
