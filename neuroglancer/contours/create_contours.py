import os 
import numpy as np
from cloudvolume import CloudVolume

from brain.models import ScanRun
from neuroglancer.contours.volume_maker import VolumeMaker
from neuroglancer.contours.ng_segment_maker import NgConverter
from neuroglancer.models import DEBUG
from timeit import default_timer as timer

def downsample_contours(contours, downsample_factor):
    values = [i/downsample_factor for i in contours.values()]
    return dict(zip(contours.keys(), values))

def get_scales(animal, downsample_factor):
    try:
        scan_run = ScanRun.objects.get(prep=animal)
        res = scan_run.resolution
        zresolution = scan_run.zresolution
    except ScanRun.DoesNotExist:
        res = 0.325
        zresolution = 20

    return [int(downsample_factor*res*1000), int(downsample_factor*res*1000), int(zresolution*1000)]


def make_volumesDEPRECATED(volume, animal, downsample_factor):
    vmaker = VolumeMaker()
    structure, contours = volume.get_volume_name_and_contours()
    downsampled_contours = downsample_contours(contours, downsample_factor)
    vmaker.set_aligned_contours({structure: downsampled_contours})
    vmaker.compute_origins_and_volumes_for_all_segments(interpolate=100)
    volume = (vmaker.volumes[structure]).astype(np.uint8)
    offset = list(vmaker.origins[structure])
    print(f'offset={offset}')
    folder_name = f'{animal}_{structure}'
    path = '/var/www/brainsharer/structures'
    output_dir = os.path.join(path, folder_name)
    scales = get_scales(animal, downsample_factor)
    maker = NgConverter(volume=volume, scales=scales, offset=offset)
    segment_properties = {1:structure}
    maker.reset_output_path(output_dir)
    maker.init_precomputed(output_dir)
    
    cloudpath = f'file://{output_dir}'
    cloud_volume = CloudVolume(cloudpath, 0)
    maker.add_segment_properties(cloud_volume=cloud_volume, segment_properties=segment_properties)
    maker.add_segmentation_mesh(cloud_volume.layer_cloudpath, mip=0)
    return folder_name
    
