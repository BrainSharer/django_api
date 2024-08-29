import os 
import numpy as np
import sys
import argparse
import json
from cloudvolume import CloudVolume
import urllib

PIPELINE_ROOT = '/opt/brainsharer'
sys.path.append(PIPELINE_ROOT)

from abakit.controller.neuroglancer_state_controller import NeuroglancerStateController
from abakit.controller.scan_run_controller import ScanRunController
from abakit.annotation.annotation_layer import AnnotationLayer
from abakit.atlas.volume_maker import VolumeMaker
from abakit.atlas.ng_segment_maker import NgConverter
try:
    from brainsharer.settings import DATABASES
except ImportError:
    print('Could not import settings')
    try:
        from brainsharer.local_settings import DATABASES
    except ImportError:
        print('Could not import local settings')
        sys.exit

host = DATABASES['default']['HOST']
password = DATABASES['default']['PASSWORD']
password = urllib.parse.quote_plus(password) # escape special characters
schema = DATABASES['default']['NAME']
user = DATABASES['default']['USER']



def contours_to_volume(url_id, volume_id):
    controller = NeuroglancerStateController(host=host, password=password, schema=schema, user=user)
    urlModel = controller.get_neuroglancer_state_model(url_id)
    state_json = json.loads(urlModel.neuroglancer_state)
    layers = state_json['layers']
    for layeri in layers:
        if layeri['type'] == 'annotation':
            layer = AnnotationLayer(layeri)
            volume = layer.get_annotation_with_id(volume_id)
            if volume is not None:
                break
    if volume is None:
        raise Exception(f'No volume was found with id={volume_id}' )
    
    animal = urlModel.get_animal()
    folder_name = make_volumes(volume, animal)
    segmentation_save_folder = f"precomputed://https://www.brainsharer.org/structures/{folder_name}"
    return segmentation_save_folder

def downsample_contours(contours, downsample_factor):
    values = [i/downsample_factor for i in contours.values()]
    return dict(zip(contours.keys(), values))

def get_scale(animal, downsample_factor):
    controller = ScanRunController(host=host, password=password, schema=schema, user=user)
    scan_run = controller.get_scan_run(animal)
    res = scan_run.resolution
    return [downsample_factor*res*1000, downsample_factor*res*1000, scan_run.zresolution*1000]


def make_volumes(volume, animal='DK55', downsample_factor=20):
    vmaker = VolumeMaker()
    structure, contours = volume.get_volume_name_and_contours()
    downsampled_contours = downsample_contours(contours, downsample_factor)
    vmaker.set_aligned_contours({structure: downsampled_contours})
    vmaker.compute_origins_and_volumes_for_all_segments(interpolate=1)
    volume = (vmaker.volumes[structure]).astype(np.uint8)
    offset = list(vmaker.origins[structure])
    folder_name = f'{animal}_{structure}'
    path = '/var/www/brainsharer/structures'
    output_dir = os.path.join(path, folder_name)
    scale = get_scale(animal, downsample_factor)
    maker = NgConverter(volume=volume, scales=scale, offset=offset)
    segment_properties = {1:structure}
    maker.reset_output_path(output_dir)
    maker.init_precomputed(output_dir)
    
    cloudpath = f'file://{output_dir}'
    cloud_volume = CloudVolume(cloudpath, 0)
    maker.add_segment_properties(cloud_volume=cloud_volume, segment_properties=segment_properties)
    maker.add_segmentation_mesh(cloud_volume.layer_cloudpath, mip=0)
    return folder_name

if __name__=='__main__':
    parser = argparse.ArgumentParser(description="url and volume id")
    parser.add_argument("--url", help="url id", required=True, type=int)
    parser.add_argument("--volume", help="volume id", required=False, default=1, type=str)
    args = parser.parse_args()
    url = contours_to_volume(args.url, args.volume)
    sys.stdout.write(url)
    sys.stdout.flush()
    
    
