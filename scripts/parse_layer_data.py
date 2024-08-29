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



def parse_neuroglancer_state(id=None):
  if id is not None:
    state = NeuroglancerState.objects.get(pk=id)
    states = [state]
  else:
     states = NeuroglancerState.objects.all()
  for state in states:
    json_txt = state.neuroglancer_state
    layers = json_txt['layers']
    for layer in layers:
        if 'annotations' in layer:
            annotations = layer['annotations']
            d = [row['pointA'] for row in annotations if 'pointA' in row and 'point' not in row]
            print(d)


def parse_annotation(id=None):
  if id is not None:
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
    parser.add_argument('--id', help='Enter ID', required=False, type=int)

    args = parser.parse_args()
    id = args.id
    parse_annotation(id)

