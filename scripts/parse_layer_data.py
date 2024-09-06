import random
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


from neuroglancer.models import NeuroglancerState, AnnotationSession

class Parsedata:
    def __init__(self, id=0, layer_name=None):
        self.id = id
        self.layer_name = layer_name

    def parse_neuroglancer_state(self):
        if self.id > 0:
            state = NeuroglancerState.objects.get(pk=self.id)
            states = [state]
        else:
            # These IDs are from Marissa
            ids = [586,593,651,658,669,682,688,704,804,623,610,727,774,785,800,755,772,784,802]
            states = NeuroglancerState.objects.filter(pk__in=ids).all()
        for state in states:
            layer_ids_to_update = []
            print(state.id, state.comments)
            existing_state = state.neuroglancer_state # big JSON
            layers = existing_state['layers'] # list of dictionaries
            for i, layer in enumerate(layers): # layers is a list
                if 'annotations' in layer: # We will be updating this layer in the state
                    existing_layer = layer # dictionary
                    layer_ids_to_update.append(i)
            for layer_id in layer_ids_to_update:
                self.create_new_annotation_data(state.id, layer_id)

    @staticmethod
    def create_new_annotation_data(neuroglancer_state_id, layer_id):
        default_props = ["#ffff00", 1, 1, 5, 3, 1]

        state = NeuroglancerState.objects.get(pk=neuroglancer_state_id)
        existing_state = state.neuroglancer_state
        existing_annotations = existing_state['layers'][layer_id]['annotations']

        existing_name = existing_state['layers'][layer_id]['name']
        parent_id = f"{Parsedata.random_string()}"
        other_rows = []  # list of dictionaries
        childAnnotationIds = []
        points = []
        if len(existing_annotations) == 0:
            return
        for i, row in enumerate(existing_annotations):
            if 'point' in row:
                point = row['point']
            else:
                continue
            
            if 'category' in row:
                category = row['category']
            else:
                category = ''

            if 'description' in row:
                description = row['description']
            else:
                description = ''
            
            if 'props' in row:
                color = row['props'][0]
                props = [color]
            else:
                props = default_props

            row = {
                "point": point,
                "type": "point",
                "id": f"{Parsedata.random_string()}",
                "parentAnnotationId": f"{parent_id}",
                "props": default_props,
            }
            other_rows.append(row)
            childAnnotationIds.append(row['id'])
            points.append(row['point'])

        first_row = {}
        first_row["source"] = points[0]
        first_row["centroid"] = np.mean(points, axis=0).tolist()
        first_row["childAnnotationIds"] = childAnnotationIds # random ids length of points
        first_row["childrenVisible"] = True
        first_row["type"] = "cloud"
        first_row["id"] = f"{parent_id}"
        first_row["props"] = default_props

        reformatted_annotations = []
        reformatted_annotations.append(first_row)
        reformatted_annotations.extend(other_rows)

        print('Updating', state.comments, existing_name, len(reformatted_annotations))
        debug = False
        if debug:
          for i, row in enumerate(existing_annotations):
              print(row)
              if i > 2:
                  break
        else:

          existing_state['layers'][layer_id]['annotations'] = reformatted_annotations
          state.updated = datetime.datetime.now(datetime.timezone.utc)
          existing_state['layers'][layer_id]['tool'] =  "annotateCloud"
          state.neuroglancer_state = existing_state
          state.save()  

    @staticmethod
    def random_string():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=40))

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Work on Animal')
    parser.add_argument('--id', help='Enter ID', required=False, default=0, type=int)
    parser.add_argument('--task', help='Enter task', required=True, type=str)
    parser.add_argument('--layer_name', help='Enter layer name', required=False, type=str)
    args = parser.parse_args()

    task = str(args.task).strip().lower()
    layer_name = str(args.layer_name).strip()
    id = args.id

    pipeline = Parsedata(id=id, layer_name=layer_name)

    function_mapping = {
            "session": pipeline.parse_annotation,
            "state": pipeline.parse_neuroglancer_state
        }

    if task in function_mapping:
        function_mapping[task]()
    else:
        print(f"{task} is not a correct task. Choose one of these:")
        for key in function_mapping.keys():
            print(f"\t{key}")
