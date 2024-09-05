import os, sys
import argparse
from collections import Counter
from pathlib import Path
import django

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
      ids = [586,593,651,658,669,682,688,704,804,623,610,727,774,785,800,755,772,784,802]
      states = NeuroglancerState.objects.filter(pk__in=ids).all()
    for state in states:
      print(state.id, state.comments)
      json_txt = state.neuroglancer_state
      layers = json_txt['layers']
      for layer in layers:
        if 'annotations' in layer:
          update_dict = [] # list of dictionaries to update
          rows = layer['annotations'] # list of dictionaries
          if self.layer_name is not None:
            if layer['name'] != self.layer_name:
              continue
          data = [(row['point'],row['category'], row['description']) for row in rows if 'point' in row and 'category' in row]
          for (point, category, description) in data:
              x = point[0]
              y = point[1]
              z = point[2]
              update_dict.append([x, y, z])
              # update the code below for the new JSON format
          annotation['childJsons'] = point_list        
          update_dict = {'annotation': annotation }
        

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