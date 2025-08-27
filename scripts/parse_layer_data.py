import json
import random
import re
import string
import os, sys
import argparse
from collections import Counter
from pathlib import Path
import django
import datetime
import numpy as np

PATH = Path('.').absolute().as_posix()
sys.path.append(PATH)
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brainsharer.settings')
django.setup()


from brain.models import Animal
from neuroglancer.models import NeuroglancerState, AnnotationSession


class Parsedata:
    def __init__(self, id=None, layer_type=None, layer_name=None, debug=False):
        self.id = id
        self.layer_type = layer_type
        self.layer_name = layer_name
        self.debug = debug

    def update_neuroglancer_state_animal(self):
        all_states = 0
        bad_states = 0
        good_states = 0
        if self.id > 0:
            state = NeuroglancerState.objects.get(pk=self.id)
            states = [state]
        else:
            states = NeuroglancerState.objects.all()
        for state in states:
            all_states += 1

            animal = "Allen"
            pattern = 'data/(\w*)/neuroglancer_data'
            neuroglancer_json = state.neuroglancer_state
            image_layers = [layer for layer in neuroglancer_json['layers'] if layer['type'] == 'image']
            if len(image_layers) > 0:
                first_image_layer = json.dumps(image_layers[0])
                match = re.search(pattern, first_image_layer)
                if match is not None and match.group(1) is not None:
                    animal = match.group(1)
                    print(state.id, state.comments, animal)
                    good_states += 1
                    animal_object = Animal.objects.get(pk=animal)
                    NeuroglancerState.objects.filter(pk=state.id).update(animal=animal_object, updated=state.updated)

                else:
                    print(f"\tAnimal not found in {state.comments} {state.id}")
                    NeuroglancerState.objects.filter(pk=state.id).update(readonly=True, updated=state.updated)
                    bad_states += 1
        print(f"Total states {all_states} with {good_states} good and {bad_states} bad, bad+good={good_states+bad_states}")    



    def fix_neuroglancer_state(self):
        if self.id > 0:
            state = NeuroglancerState.objects.get(pk=self.id)
            states = [state]
        else:
            # These IDs are from Marissa
            # ids = [586,593,651,658,669,682,688,704,804,623,610,727,774,785,800,755,772,784,802]
            # Polygon IDs that need to be updated
            ids = [758, 761, 966, 679, 1005, 1007]
            ids = [0]

            states = NeuroglancerState.objects.exclude(pk__in=ids).order_by('id').filter(active=True).all()
        for state in states:
            layer_ids_to_update = []
            existing_state = state.neuroglancer_state # big JSON
            layers = existing_state['layers'] # list of dictionaries
            for i, layer in enumerate(layers): # layers is a list
                if 'annotations' in layer: # We will be updating this layer in the state
                    layer_ids_to_update.append(i)

            for layer_id in layer_ids_to_update:
                if self.layer_type == "cloud":
                    self.fix_and_update_cloud_annotation_data(state.id, layer_id, self.layer_name, self.debug)
                if self.layer_type == "volume":
                    self.fix_and_update_volume_annotation_data(state.id, layer_id)

    def show_annotations(self):
        if self.id > 0:
            try:
                state = NeuroglancerState.objects.get(pk=self.id)
            except NeuroglancerState.DoesNotExist:
                print(f'ID={self.id} not found, returning ...')
                return
        else:
            print('No ID was provided, returning ...')
            return
        
        print(state.id, state.comments)
        existing_state = state.neuroglancer_state # big JSON
        layers = existing_state['layers'] # list of dictionaries
        for i, layer in enumerate(layers): # layers is a list
            if 'annotations' in layer: # just look at the layers with annotations
                if layer_type == 'cloud':
                    self.show_v1_cloud_annotations(layer)
                    self.show_v2_cloud_annotations(layer)
                elif layer_type == 'volume':
                    self.show_annotation_json(layer)
                else:
                    print('Select either layer_type=cloud or volume')

    @staticmethod
    def show_annotation_json(layer):
        name = layer['name']
        annotations = layer['annotations']
        # type for v1 is either line or polygon
        for annotation in annotations:
            annotation_type = annotation.get('type')
            parent_id = annotation.get('parentAnnotationId', 'XXXXX')
            parent_id = parent_id[0:5] if isinstance(parent_id, str) else parent_id
            child_ids = annotation.get('childAnnotationIds', [])
            number_of_children = len(child_ids)
            if len(child_ids) != 0:
                child_ids = [str(child_id[0:5]) for child_id in child_ids]
            if annotation_type == 'volume':
                print(f'Annotation type={annotation_type}', end=' ')
                print(f'id={annotation.get("id")} description={annotation.get("description")}')
                print(f'# polygons={number_of_children} child IDS={child_ids[:5]}')
            if annotation_type == 'polygon':
                print(f'\tAnnotation type={annotation_type} parentID={parent_id}', end=' ')
                print(f'\tid={annotation.get("id")} description={annotation.get("description")}')
                #print(f'child IDS={annotation.get("childAnnotationIds")}')
                print(f'\t# lines={number_of_children} child IDS={child_ids[:5]}')
            if annotation_type == 'line':
                print(f'\t\tAnnotation type={annotation_type} parentID={parent_id}', end=' ')
                print(f'\t\tid={annotation.get("id")} description={annotation.get("description")}')
                


    @staticmethod
    def show_v1_cloud_annotations(layer):
        name = layer['name']
        annotations = layer['annotations']
        print(f'Layer={name}')
        keys = set()
        for annotation in annotations:
            #print(annotation.keys())
            keys.add(tuple(annotation.keys()))
            points = [ row['point'] for row in annotations if 'point' in row]
            pointsAB = [ row['pointA'] for row in annotations if 'pointA' in row]
        print(keys)
        print(f'with # cloud points={len(points)}')
        print(f'with # annotation points={len(pointsAB)}')


    @staticmethod
    def show_v2_cloud_annotations(layer):
        name = layer['name']
        annotations = layer['annotations']
        print(f'Layer={name}', end="\t")
        total_points = 0
        cloud_ids = list(set(row["parentAnnotationId"] for row in annotations if "parentAnnotationId" in row
                                and 'type' in row
                                and row['type'] == 'point'))

        for parentId in cloud_ids:
            points = [ row['point'] for row in annotations if 'point' in row and "parentAnnotationId" in row and row["parentAnnotationId"] == parentId]
            descriptions = [row["description"] for row in annotations if "description" in row 
                                    and 'type' in row 
                                    and row['type'] == 'cloud'
                                    and 'id' in row
                                    and row['id'] == parentId]
            if len(descriptions) == 0:
                descriptions = 'unlabeled point'
            else:
                descriptions = descriptions[0].replace('\n', ', ')
            print('Cloud description'.ljust(20), str(descriptions).ljust(40), 'points', len(points))
            total_points += len(points)
        print(f'with # cloud points={total_points}')
 
    @staticmethod
    def show_volume_annotations(layer):
        name = layer['name']
        annotations = layer['annotations']
        total_points = 0
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
            number_of_points = 0
            for polygon_id in polygon_ids:
                points = [
                    row
                    for row in annotations
                    if "pointA" in row
                    and "type" in row
                    and row["type"] == "line"
                    and "parentAnnotationId" in row
                    and row["parentAnnotationId"] == polygon_id
                ]
                number_of_points += len(points)
            total_points += number_of_points

            print(f'Layer={name}', end="\t")            
            print(f'\nVolume description={str(descriptions)}')
            print(f'# polygons {len(polygon_ids)}')  
            print(f'# points {number_of_points}')
            for point in points:
                print(point)
        


    @staticmethod
    def fix_and_update_cloud_annotation_data(neuroglancer_state_id, layer_id, layer_name, debug):
        default_props = ["#00ff00", 1, 1, 5, 3, 1]

        state = NeuroglancerState.objects.get(pk=neuroglancer_state_id)
        existing_state = state.neuroglancer_state
        existing_annotations = existing_state["layers"][layer_id]["annotations"]

        existing_name = existing_state["layers"][layer_id]["name"]
        if len(existing_annotations) == 0:
            return
                
        #for a in existing_annotations:
        #    print(a)
        #return
        existing_state["layers"][layer_id]["annotations"] = []
        descriptions = list(set(row["description"] for row in existing_annotations if "description" in row and "type" in row and row["type"] == "cloud"))

        cloud_ids = list(set(row["id"] for row in existing_annotations if "id" in row and "type" in row and row["type"] == "cloud"))
        if len(cloud_ids) == 0:
            return

        if len(descriptions) == 0:
            descriptions = [None]

        for cid, cloud_id in enumerate(cloud_ids):
            other_rows = []  # list of dictionaries
            childAnnotationIds = [row["childAnnotationIds"] for row in existing_annotations if "childAnnotationIds" in row and row["id"] == cloud_id][0]
            points = []
            child_ids = []            
            
            all_points_in_cloud = [row for row in existing_annotations if "type" in row 
                                    and row["type"] == "point"
                                    and row["id"] in childAnnotationIds]
            first_prop = all_points_in_cloud[0]["props"]

            for i, existing_row in enumerate(all_points_in_cloud):
                if "point" in existing_row:
                    point = existing_row["point"]
                else:
                    continue

                if "props" in existing_row:
                    color = existing_row["props"][0]
                    props = [f"{color}", 1, 1, 5, 3, 1]
                else:
                    props = default_props

                new_row = {
                    "point": point,
                    "type": "point",
                    "id": f"{existing_row['id']}",
                    "parentAnnotationId": f"{cloud_id}",
                    "props": props
                }
                child_ids.append(f"{existing_row['id']}")
                other_rows.append(new_row)
                points.append(new_row["point"])

            if len(points) == 0:
                return

            first_row = {}
            first_row["source"] = points[0]
            first_row["centroid"] = np.mean(points, axis=0).tolist()
            first_row["childAnnotationIds"] = child_ids
            first_row["childrenVisible"] = True
            first_row["type"] = "cloud"
            first_row["id"] = f"{cloud_id}"
            first_row["props"] = [ f"{first_prop}", 1, 1, 5, 3, 1]
            first_row["description"] = f"{descriptions[cid]}"

            reformatted_annotations = []
            reformatted_annotations.append(first_row)
            reformatted_annotations.extend(other_rows)

            existing_state["layers"][layer_id]["annotations"] += reformatted_annotations

        state.updated = datetime.datetime.now(datetime.timezone.utc)
        existing_state["layers"][layer_id]["tool"] = "annotateCloud"
        existing_state["layers"][layer_id]["annotationProperties"] = create_json_header()

        if debug:
            task = "debugging"
        else:
            task = "updating"
            state.neuroglancer_state = existing_state
            state.save()

        print(f'Finished {task} URL ID={state.id} comments="{state.comments}", layer_name="{existing_name}" with {len(reformatted_annotations)} reformatted annotations')



    def fix_and_update_volume_annotation_data(self, neuroglancer_state_id, layer_id):
        default_props = ["#ffff00", 1, 1, 5, 3, 1]

        state = NeuroglancerState.objects.get(pk=neuroglancer_state_id)
        existing_state = state.neuroglancer_state
        existing_annotations = existing_state["layers"][layer_id]["annotations"]

        existing_name = existing_state["layers"][layer_id]["name"]
        
        if len(existing_annotations) == 0:
            if self.id > 0:
                print("No annotations found for", state.comments, existing_name, layer_id)
            return
        
        existing_state["layers"][layer_id]["annotations"] = []
        # descriptions are the labels

        #volume_id = f"{Parsedata.random_string()}"
        volume_ids = [row['id'] for row in existing_annotations if "type" in row and row["type"] == "volume"]
        if len(volume_ids) == 0:
            return

        if "props" in existing_annotations and "type" in existing_annotations and existing_annotations["type"] == "polygon":
            color = existing_annotations["props"][0]
            default_props = [f"{color}", 1, 1, 5, 3, 1]
        else:
            props = default_props

        descriptions = list(set(row["description"] for row in existing_annotations if "description" in row))
        if len(descriptions) > 0:
            description = descriptions[0]
        else:
            description = ""

        points = []
        all_volume_lines = []
        reformatted_annotations = []
        errors = []

        for volume_id in volume_ids:
            polygons = []
            polygon_ids = [row['childAnnotationIds'] for row in existing_annotations if "type" in row and row["type"] == "volume"
                         and "childAnnotationIds" in row and row["id"] == volume_id][0]
            for idx, polygon_id in enumerate(polygon_ids):
                try:
                    line_ids = [row['childAnnotationIds'] for row in existing_annotations 
                                if "type" in row 
                                    and row["type"] == "polygon"
                                    and "childAnnotationIds" in row
                                    and row["id"] == polygon_id][0]
                except IndexError as ie:
                    print(f"Error finding line IDs for layer {existing_name} ID={state.id} {ie}")
                    continue
                # Get all the lines that are children of this polygon
                all_lines_in_polygon = [row for row in existing_annotations if "type" in row and row["type"] == 'line'
                                and row['id'] in line_ids]            

                if len(all_lines_in_polygon) != len(line_ids):
                    errors.append(f"Line IDs do not match for layer={existing_name} ID={state.id}")
                    continue
                polygon_lines = []
                for line_source in all_lines_in_polygon:
                    id = line_source.get("id", f"{Parsedata.random_string()}")
                    pointA = line_source["pointA"]
                    pointB = line_source["pointB"]
                    points.append(pointA)
                    
                    if "props" in line_source and "type" in line_source and line_source["type"] == "line":
                        color = line_source["props"][0]
                        props = [f"{color}", 1, 1, 5, 3, 1]
                    else:
                        props = default_props

                    line = {
                        "pointA": pointA,
                        "pointB": pointB, 
                        "type": "line",
                        "id": f"{id}",
                        "parentAnnotationId": f"{polygon_id}",
                        "props": props
                    }
                    polygon_lines.append(line)

                if len(polygon_lines) == 0:
                    errors.append(f"No lines found for {state.id} in polygon={polygon_id}")
                    continue
                polygon = {}
                polygon['source'] = polygon_lines[0]['pointA']
                polygon["centroid"] = np.mean([line['pointA'] for line in polygon_lines], axis=0).tolist()
                polygon['childAnnotationIds'] = line_ids
                polygon['type'] = 'polygon'
                polygon['id'] = f"{polygon_id}"
                polygon["parentAnnotationId"] = f"{volume_id}"
                polygon['props'] = props
                section = int(polygon['centroid'][-1])
                polygon['section'] = section
                all_volume_lines.extend(polygon_lines)
                if self.debug and False:
                        print(f"\n\t{idx=} Polygon ID={polygon_id[0:5]} with {len(line_ids)} lines")
                        print(f"\tcentroid={polygon['centroid']} int section={section}")
    
                polygons.append(polygon)
            key_for_uniqueness = "section"
            seen_ids = set()
            unique_list = []
            if self.debug and self.id > 0:
                print(f"Found {len(polygons)} polygons before removal", end =' ')

            for d in polygons:
                if d[key_for_uniqueness] not in seen_ids:
                    unique_list.append(d)
                    seen_ids.add(d[key_for_uniqueness])                
            polygons = unique_list
            del unique_list
            # now remove the section key from each polygon
            for d in polygons:
                del d['section']

            if self.debug and self.id > 0:
                print(f"and {len(polygons)} polygons after removal")
            polygon_ids = [polygon['id'] for polygon in polygons]


            if len(polygons) == 0:
                continue
            assert len(points) == len(all_volume_lines), f"Points {len(points)} and lines {len(all_volume_lines)} do not match for volume={volume_id}"
            volume = {}
            volume["source"] = points[0]
            volume["centroid"] = np.mean(points, axis=0).tolist()
            volume["childAnnotationIds"] = polygon_ids # random ids length of points
            volume["childrenVisible"] = True
            volume["type"] = "volume"
            volume["id"] = f"{volume_id}"
            volume["props"] = default_props
            volume["description"] = f"{description}"

            reformatted_annotations.append(volume)
            reformatted_annotations.extend(polygons)
            reformatted_annotations.extend(all_volume_lines)

        existing_state["layers"][layer_id]["annotations"] = reformatted_annotations
        if self.debug and self.id > 0:
            pass
            print("Reformatted ")
            json_output = json.dumps(reformatted_annotations, indent=4)
            #print(json_output)
            return


        state.updated = datetime.datetime.now(datetime.timezone.utc)
        existing_state["layers"][layer_id]["tool"] = "annotateVolume"
        existing_state["layers"][layer_id]["annotationProperties"] = create_json_header()
        print(f'Finished ID={state.id} layer={existing_name} volumes={len(volume_ids)} total annotations={len(reformatted_annotations)}')
        errors = set(errors)
        if len(errors) > 0:
            print(f"Errors found for {state.id} {state.comments}:")
            for error in errors:
                print(f"\t{error}")

        if not debug:
            state.neuroglancer_state = existing_state
            state.save()
            print("Updated", state.comments, existing_name)
    
    @staticmethod
    def random_string():
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=40))

    def parse_annotation(self):
        if self.id > 0:
            state = AnnotationSession.objects.get(pk=id)
            states = [state]
        else:
            states = AnnotationSession.objects.filter(active=True).all()
        data = []
        for state in states:
            data.append(state.annotation)

        key = 'type'
        signs = Counter(k[key] for k in data if k.get(key))
        for sign, count in signs.most_common():
            print(sign, count)

        if id is not None:
            print(data)
            print(len(data))


def create_json_header():
    header = [
                {
                    "id": "color",
                    "description": "color",
                    "type": "rgb",
                    "default": "#ffff00",
                },
                {
                    "id": "visibility",
                    "description": "visibility",
                    "type": "float32",
                    "default": 1,
                    "min": 0,
                    "max": 1,
                    "step": 1,
                },
                {
                    "id": "opacity",
                    "description": "opacity",
                    "type": "float32",
                    "default": 1,
                    "min": 0,
                    "max": 1,
                    "step": 0.01,
                },
                {
                    "id": "point_size",
                    "description": "point marker size",
                    "type": "float32",
                    "default": 5,
                    "min": 0,
                    "max": 10,
                    "step": 0.01,
                },
                {
                    "id": "point_border_width",
                    "description": "point marker border width",
                    "type": "float32",
                    "default": 3,
                    "min": 0,
                    "max": 5,
                    "step": 0.01,
                },
                {
                    "id": "line_width",
                    "description": "line width",
                    "type": "float32",
                    "default": 1,
                    "min": 0,
                    "max": 5,
                    "step": 0.01,
                },
            ]
    return header


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Work on Animal')
    parser.add_argument('--id', help='Enter ID', required=False, default=None, type=int)
    parser.add_argument('--task', help='Enter task', required=True, type=str)
    parser.add_argument('--layer_type', help='Enter layer type', required=False, type=str)   
    parser.add_argument('--layer_name', help='Enter layer name', required=False, type=str)   

    parser.add_argument('--debug', required=False, default='false', type=str)

    args = parser.parse_args()

    task = str(args.task).strip().lower()
    layer_type = str(args.layer_type).strip()
    layer_name = str(args.layer_name).strip()
    debug = bool({'true': True, 'false': False}[args.debug.lower()])    
    id = args.id

    pipeline = Parsedata(id=id, layer_type=layer_type, layer_name=layer_name, debug=debug)

    function_mapping = {
            "session": pipeline.parse_annotation,
            "fix": pipeline.fix_neuroglancer_state,
            "show": pipeline.show_annotations,
            "fix_animal": pipeline.update_neuroglancer_state_animal,
        }

    if task in function_mapping:
        function_mapping[task]()
    else:
        print(f"{task} is not a correct task. Choose one of these:")
        for key in function_mapping.keys():
            print(f"\t{key}")
