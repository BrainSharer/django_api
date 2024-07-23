"""
William, this is the last script for creating the atlas

This will create a precomputed volume of the Active Brain Atlas which
you can import into neuroglancer
"""
import os
import numpy as np
import shutil
from cloudvolume import CloudVolume

from neuroglancer.contours.neuroglancer_manager import NumpyToNeuroglancer


class NgConverter(NumpyToNeuroglancer):
    def __init__(self, volume=None, scales=None, offset=[0, 0, 0], layer_type='segmentation'):
        if volume is not None:
            self.volume = volume
        self.scales = scales
        self.offset = offset
        self.layer_type = layer_type
        self.precomputed_vol = None

    def init_precomputed(self, path):
        info = CloudVolume.create_new_info(
            num_channels=self.volume.shape[3] if len(
                self.volume.shape) > 3 else 1,
            layer_type=self.layer_type,
            # Channel images might be 'uint8'
            data_type=np.uint16,
            # raw, jpeg, compressed_segmentation, fpzip, kempressed
            encoding='raw',
            resolution=self.scales,            # Voxel scaling, units are in nanometers
            # x,y,z offset in voxels from the origin
            voxel_offset=self.offset,
            chunk_size=[64, 64, 64],           # units are voxels
            volume_size=self.volume.shape[:3],
        )
        self.precomputed_vol = CloudVolume(
            f'file://{path}', mip=0, info=info, compress=True, progress=True)
        self.precomputed_vol.commit_info()
        self.precomputed_vol[:, :, :] = self.volume

    def create_neuroglancer_files(self, output_dir, segment_properties):
        self.reset_output_path(output_dir)
        self.init_precomputed(output_dir)
        self.add_segment_properties(segment_properties)
        self.add_downsampled_volumes()
        self.add_segmentation_mesh()

    def reset_output_path(self, output_dir):
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

