import numpy as np
import pandas as pd

def polygons(animal, ScanRun, neuroglancer_state):
    result = None
    xy_resolution = 1.0
    if animal is not None and animal != 'NA':
        scan_run = ScanRun.objects.filter(prep_id=animal).first()
        if scan_run is not None:
            xy_resolution = scan_run.resolution
            z_resolution = scan_run.zresolution

    if neuroglancer_state is not None:
        json_txt = neuroglancer_state
        df = pd.json_normalize(json_txt, record_path=['layers'])
        df = df.loc[df['type'] == 'annotation', ['name','type', 'annotations']]
        print(df.head())
        print(df.columns)
        cloud_data = {}
        volume_data = {}
        for row in df.itertuples(index=True):
            # Access individual values using dot notation
            annotations = row.annotations
            name = row.name
            annotation_type = get_annotation_type(annotations)
            print(f"Row {row.Index} -> Name: {name}, Annotations: {type(annotations)}, Type: {annotation_type}")
            if annotation_type == 'cloud':
                cloud_data[name] = annotations
            elif annotation_type == 'volume':
                volume_data[name] = annotations
            else:
                print(f"Row {row.Index} -> Name: {name}, Annotations: {type(annotations)}, Type: {annotation_type} (not processed)")
        ##### This is for the volumes/polygons
        ##### For each volume, get all the polygons and then for each polygon, get all the points
        for volume_name, v in volume_data.items():
            volume_ids = [row['id'] for row in v if "id" in row and 'type' in row and row['type'] == 'volume']
        for v in cloud_data.values():
            cloud_points = [row['point'] for row in v if "point" in row and 'type' in row and row['type'] == 'point']
        data_list = []
        for volume_id in volume_ids:
            for v in volume_data.values():
                polygon_ids = [row['id'] for row in v if "id" in row 
                                and 'type' in row 
                                and row['type'] == 'polygon'
                                and 'parentAnnotationId' in row
                                and row['parentAnnotationId'] == volume_id]
            print(f"polygon_ids: {polygon_ids}")

            for UUID in polygon_ids:
                for v in volume_data.values():

                    lines = [row for row in v
                            if "pointA" in row
                            and "type" in row
                            and row["type"] == "line"
                            and "parentAnnotationId" in row
                            and row["parentAnnotationId"] == UUID
                ]
                print(f"UUID: {UUID}, # lines: {len(lines)}")
                section = lines[0]['pointA'][2]  # Subtracting 0.5 to get the section number
                points = [(row['pointA'][0]*xy_resolution, row['pointA'][1]*xy_resolution) for row in lines]

                area = polygon_area(points)
                points_on_section = get_cloud_points_in_section(cloud_points, section)
                points_in_region = count_points_in_polygon(cloud_points, points, xy_resolution)
                section = int(section - 0.5)  # Subtracting 0.5 to get the section number

                #cloud_points_in, cloud_points_out = get_cloud_points_in_polygon(cloud_points, points)
                # Creating a dictionary for each row mapping columns to values
                row_data = {"Layer": volume_name, "Section": section, "Points": len(lines), "Area": area, 
                            "cloud": name, "cloud_points_on_section": points_on_section, "cloud_points_in_region": points_in_region}
                data_list.append(row_data)
        result = pd.DataFrame(data_list)

    return result


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
    
    for px, py, pz in cloud_points:
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

