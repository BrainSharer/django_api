from itertools import chain
import json
import math
import random
import re
import string
import os, sys
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import cv2
import django
import datetime
import numpy as np
from matplotlib import pyplot as plt
from tifffile import tifffile

PATH = Path('.').absolute().as_posix()
sys.path.append(PATH)
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brainsharer.settings')
django.setup()


from brain.models import Animal
from neuroglancer.models import AnnotationLabel, NeuroglancerState, AnnotationSession, polygon_area, MICRON
from authentication.models import User

M_UM_SCALE = 1000000

class Parsedata:
    def __init__(self, id=None, layer_type=None, layer_name=None, downsample=True, debug=False):
        self.id = id
        self.layer_type = layer_type
        self.layer_name = layer_name
        self.debug = debug
        self.animal = None
        self.downsample = downsample
        self.prep_path = "/net/birdstore/Active_Atlas_Data/data_root/pipeline_data"

    def find_clouds(self):
        datafile = "./scripts/hannah.DK55.json"
        if not os.path.exists(datafile):
            print(f"File {datafile} does not exist, returning ...")
            return
        with open(datafile, 'r') as file:
            # Load the file content into a Python list
            data = json.load(file)

        # Loop through the list
        layers = data['layers']
        default_props = ["#00ff00", 1, 1, 5, 3, 1]
        animal = Animal.objects.get(pk="DK55")
        annotator = User.objects.get(pk=3)

        for layer in layers:
            if 'annotations' in layer:
                annotations = layer['annotations']
                labels = AnnotationLabel.objects.filter(id=92).first()
                print(f"Layer {layer['name']} has {len(annotations)} annotations")
                cloud_id = f"{Parsedata.random_string()}"
                child_ids = []
                points = []
                other_rows = []
                for annotation in annotations:
                    if 'point' in annotation and 'id' in annotation:
                        # print(f"\t{annotation['point']}")
                        x,y,z = annotation["point"]
                        x = x * 0.325 / M_UM_SCALE
                        y = y * 0.325 / M_UM_SCALE
                        z = z * 20 / M_UM_SCALE
                        point = [x, y, z]
                        id = annotation.get("id")

                        new_row = {
                            "point": point,
                            "type": "point",
                            "id": f"{id}",
                            "parentAnnotationId": f"{cloud_id}",
                            "props": default_props
                        }
                        child_ids.append(f"{id}")
                        other_rows.append(new_row)
                        points.append(new_row["point"])

                if len(points) == 0:
                    return

                annotation_json = {}
                annotation_json["source"] = points[0]
                annotation_json["centroid"] = np.mean(points, axis=0).tolist()
                annotation_json["childAnnotationIds"] = child_ids
                annotation_json["childrenVisible"] = True
                annotation_json["type"] = "cloud"
                annotation_json["id"] = f"{cloud_id}"
                annotation_json["props"] = default_props
                annotation_json["description"] = f"{layer['name']}"
                annotation_json["childJsons"] = other_rows

                if debug:
                    pretty_json = json.dumps(annotation_json, indent=4)
                    print(pretty_json)

                else:
                    as1 = AnnotationSession.objects.create(animal=animal, active=True, updated=datetime.datetime.now(datetime.timezone.utc), annotator=annotator)
                    as1.labels.set([labels])
                    annotation_json["sessionID"] = as1.id
                    as1.annotation = annotation_json
                    as1.save()
                    print(f"Saved cloud annotation session with ID={as1.id} for animal {animal}")

    def create_channel(self):

        state = NeuroglancerState.objects.get(pk=self.id)
        neuroglancer_state = state.neuroglancer_state

        # Index all annotations in one pass.
        volume_layers = []
        polygons_by_id = {}
        polygon_ids_by_volume = defaultdict(list)
        lines_by_polygon = defaultdict(list)
        polygons_by_section = {}
        for layer in neuroglancer_state.get("layers", []):
            if layer.get("type") != "annotation":
                continue
            if self.layer_name and layer.get("name") != self.layer_name:
                print(f'Skipping layer {layer.get("name")} because it does not match the specified layer_name {self.layer_name}')
                continue

            layer_name = layer.get("name", "")
            annotations = layer.get("annotations") or []
            description = "NA"
            for annotation in annotations:
                annotation_type = annotation.get("type")

                if annotation_type == "volume" and annotation.get("id") is not None:
                    volume_id = annotation["id"]
                    description = annotation.get("description", "NA")
                    volume_layers.append((layer_name, volume_id, description))

                elif annotation_type == "polygon":
                    polygon_id = annotation.get("id")
                    parent_id = annotation.get("parentAnnotationId")

                    if polygon_id is not None:
                        polygons_by_id[polygon_id] = annotation

                        if parent_id is not None:
                            polygon_ids_by_volume[parent_id].append(polygon_id)

                elif annotation_type == "line":
                    parent_id = annotation.get("parentAnnotationId")
                    point = annotation.get("pointA")

                    if (
                        parent_id is not None
                        and point is not None
                        and len(point) >= 3
                    ):
                        lines_by_polygon[parent_id].append(point)

                else:
                    print(f"Skipping annotation type '{annotation_type}' in layer '{layer_name}'")
                    continue

        # Process only polygons belonging to each volume.
        for layer_name, volume_id, description in volume_layers:
            for polygon_id in polygon_ids_by_volume.get(volume_id, []):
                lines = lines_by_polygon.get(polygon_id, [])

                if not lines:
                    continue

                line_array = np.asarray(lines, dtype=np.float64)
                if self.downsample == "thumbnail":
                    divisor = 32
                else:
                    divisor = 1

                polygon_xy = line_array[:, :2] / divisor
                section_value = line_array[0, 2]
                section_number = int(section_value - 0.5)
                polygons_by_section[section_number] = polygon_xy
                # print(f"Layer: {layer_name}, Volume ID: {volume_id[0:5]}, Description: {description}, Polygon ID: {polygon_id[0:5]}, Section: {section_number}, Points: {type(polygon_xy)}, Mean: {polygon_mean}")
        self.animal = state.animal
        print(f"Animal: {self.animal}, State ID: {state.id}")
        input_path = os.path.join(self.prep_path, f"{self.animal}/preps/C2/{self.downsample}_aligned")
        if not os.path.exists(input_path):
            print(f'Input path missing: {input_path}')
            exit(1)
        output_path = os.path.join(self.prep_path, f"{self.animal}/preps/C2/polygons")
        os.makedirs(output_path, exist_ok=True)
        infiles = sorted(os.listdir(input_path))
        sorted_dict = dict(sorted(polygons_by_section.items()))
        for section_number, polygon in sorted_dict.items():
            tifname = f"{section_number:03d}.tif"
            filename = os.path.join(input_path, tifname)
            if os.path.exists(filename):
                image_outpath = os.path.join(output_path, tifname)
                if os.path.exists(image_outpath):
                    print(f"Output file {image_outpath} already exists, skipping ...")
                    continue
                polygon = polygon.astype(np.int32)
                image_inpath = os.path.join(input_path, tifname)
                with tifffile.TiffFile(image_inpath) as tif:
                    image = tif.asarray()

                mask = np.zeros(image.shape, dtype=np.uint16)
                cv2.fillPoly(mask, [polygon], 65535)
                # Apply the mask using a bitwise AND operation
                # Everything outside the ROI becomes 0
                masked_image = cv2.bitwise_and(image, mask)
                x, y, w, h = cv2.boundingRect(polygon)
                cropped_image = masked_image[y:y+h, x:x+w]

                tifffile.imwrite(
                    image_outpath,
                    cropped_image,
                    photometric="minisblack",
                    compression="LZW",
                )
                print(f"Section: {section_number} Polygon Points: {polygon.shape[0]} points, Mean: {np.round(np.mean(polygon, axis=0),2)}", end=" ")
                print(f'Wrote: {image_outpath}')
        return
        for infile in infiles:
            test_file = os.path.join(os.path.join(output_path, infile))
            if not os.path.exists(test_file):
                with tifffile.TiffFile(image_inpath) as tif:
                    # Using as_array reads it into a NumPy array efficiently
                    image = tif.asarray()
                mask = np.zeros(image.shape, dtype=np.uint16)
                tifffile.imwrite(test_file, mask)
                print(f"Creating empty image at: {test_file}")

        # self.histogram_maker()
        # self.find_contours()

    def create_roi(self):
        infile = "014.tif"
        image_path = f"/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/DK283/preps/C2"
        image_inpath = os.path.join(image_path, 'polygons', infile)
        with tifffile.TiffFile(image_inpath) as tif:
            img = tif.asarray()

        min_val = int(np.min(img))
        max_val = int(np.max(img))
        print(f'min value {min_val} max: {max_val}')
        return
        step = 100
        thresholds = np.arange(min_val, max_val + step, step)
        pixel_sums = [np.sum(img[img > t].astype(np.int64)) for t in thresholds]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(thresholds, pixel_sums, color='darkviolet', linewidth=2)
        ax.set_title(f'Sum of Brightness Values vs. Threshold (Active Range: {min_val}:{max_val})', fontsize=12, fontweight='bold')
        ax.set_xlabel('Threshold Value (Filtered to Active Range)', fontsize=12)
        ax.set_ylabel('Sum of Brightness Intensities', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_yscale('log')
        ax.set_xlim(min_val, max_val)
        pngfile = "014.cumulative_intensities_active_range.png"
        outfile_path = os.path.join(image_path, 'testing', pngfile)
        fig.savefig(outfile_path, bbox_inches="tight")
        plt.close(fig)
        print(f'Wrote active range to: {outfile_path}')
        
        # Create and save histogram
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(img.ravel(), bins=2000, range=(min_val, max_val), color="r")
        ax.set_yscale('log')
        ax.grid(axis="y", alpha=0.75)
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        ax.set_title(f"Histogram ROI", fontsize=8)
        plt.style.use("ggplot")
        pngfile = "014.histogram.log.png"
        outfile_path = os.path.join(image_path, 'testing', pngfile)
        fig.savefig(outfile_path, bbox_inches="tight")
        plt.close(fig)
        print(f'Wrote histogram to: {outfile_path}')
        ##### Start thresholded images
        range1 = range(0,1000, 20)
        range2 = range(1200, int(img.max()), 200)
        combined = chain(range1, range2)

        for threshold in combined:

            binary_mask = img > threshold
            pixel_count = np.count_nonzero(binary_mask)
            int8_arr = (binary_mask * 255).astype(np.int8)
            print(f'Threshold: {threshold} | Pixels above threshold: {pixel_count}', end=" ")

            #clipped = np.clip(image, threshold, 65535)
            #modified_values = clipped.astype(np.uint32) * gain
            #adjusted = np.clip(modified_values, 0, 65535).astype(np.uint16)
            str_threshold = str(threshold).zfill(5)
            clipname = f"{str_threshold}.tif"
            output_path = os.path.join(image_path, "thresholds", clipname)
            cv2.imwrite(output_path, int8_arr)
            print(f' to {output_path}')


    def create_roiFULL(self):
        infile = "014.cropped.roi.unchanged.tif"
        image_path = f"/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/DK283/preps/C2/testing"
        image_inpath = os.path.join(image_path, infile)
        with tifffile.TiffFile(image_inpath) as tif:
            image = tif.asarray()
        """
        empty = np.zeros_like(image)
        image = image[image > 0]
        min_val = int(np.min(image))
        max_val = int(np.max(image))
        print(f'min value {min_val} max: {max_val}')
        step = 100
        thresholds = np.arange(min_val, max_val + step, step)
        # 4. Calculate the sum of the actual brightness values above each threshold
        pixel_sums = [np.sum(image[image > t].astype(np.int64)) for t in thresholds]
        # setup figure
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(thresholds, pixel_sums, color='darkviolet', linewidth=2)

        # Formatting the plot
        ax.set_title(f'Sum of Brightness Values vs. Threshold (Active Range: {min_val}:{max_val})', fontsize=12, fontweight='bold')
        ax.set_xlabel('Threshold Value (Filtered to Active Range)', fontsize=12)
        ax.set_ylabel('Sum of Brightness Intensities', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_yscale('log')
        ax.set_xlim(min_val, max_val)
        pngfile = "014.cumulative_intensities_active_range.png"
        outfile_path = os.path.join(image_path, pngfile)
        fig.savefig(outfile_path, bbox_inches="tight")
        plt.close(fig)
        print(f'Wrote active range to: {outfile_path}')
        
        # Create and save histogram
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(image, bins=2000, range=(min_val, max_val), color="r")
        ax.set_yscale('log')
        ax.grid(axis="y", alpha=0.75)
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        ax.set_title(f"Histogram ROI", fontsize=8)
        plt.style.use("ggplot")
        pngfile = "014.histogram.log.png"
        outfile_path = os.path.join(image_path, pngfile)
        fig.savefig(outfile_path, bbox_inches="tight")
        plt.close(fig)
        print(f'Wrote histogram to: {outfile_path}')

        #ids, counts = np.unique(image, return_counts=True)
        #masked_counts = counts > 100
        #lower_bound = int(ids[masked_counts][0])
        from skimage.filters import frangi
        filtered_image = frangi(image)
        filename = f"display.frangi.tif"
        output_path = os.path.join(image_path, filename)
        cv2.imwrite(output_path, filtered_image)
        print(f'Wrote frangi to {output_path}')
        return
        display = np.clip(
            (image.astype(np.float32) - 500) / (10000 - 500) * 255,
            0,
            255
        ).astype(np.uint8)
        """
        p_low, p_high = np.percentile(image, [99, 99.99])

        print("99%:", p_low)
        print("99.99%:", p_high)
        img32 = image.astype(np.float32)     
        display = np.clip(
            (img32 - p_low) /
            (p_high - p_low) * 255,
            0,
            255
        ).astype(np.uint8)

        # Estimate slowly varying background
        background = cv2.GaussianBlur(
            img32,
            (0, 0),
            sigmaX=15
        )

        # Bright structures above background
        response = img32 - background
        response[response < 0] = 0

        responses = []

        for sigma in [2, 4, 8, 12, 20]:
            background = cv2.GaussianBlur(
                img32,
                (0, 0),
                sigmaX=sigma
            )

            response = img32 - background
            response[response < 0] = 0

            responses.append(response)

        axon_response = np.max(
            np.stack(responses),
            axis=0
        )
        lo, hi = np.percentile(
            axon_response,
            [90, 99.9]
        )
        kernel_lengths = [5, 9, 15]
        for p in [99.0, 99.5, 99.7, 99.9]:
            threshold = np.percentile(axon_response, p)
            mask = (axon_response > threshold).astype(np.uint8) * 255
            filename = f"axon_mask_{p}.tif"
            output_path = os.path.join(image_path, filename)
            cv2.imwrite(output_path, mask)
            print(f'Wrote {p=} axon_mask to {output_path}')

            responses = []

            for length in kernel_lengths:

                for angle in range(0, 180, 15):

                    kernel = np.zeros((length, length), dtype=np.uint8)
                    center = length // 2
                    theta = np.deg2rad(angle)
                    dx = int(np.cos(theta) * center)
                    dy = int(np.sin(theta) * center)

                    cv2.line(
                        kernel,
                        (center - dx, center - dy),
                        (center + dx, center + dy),
                        1,1)

                    # Morphological opening estimates structures
                    # that follow this orientation.
                    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN,kernel)
                    responses.append(opened)

            line_response = np.max(
                np.stack(responses),
                axis=0
            )

            linename = f"axon_line_response_{p}.tif"
            output_path = os.path.join(image_path, linename)
            cv2.imwrite(output_path, line_response)
            print(f'Wrote line response to {output_path}')

        return

        lower_bound = 10000
        upper_bound = int(max_val)
        mask = cv2.inRange(image, lower_bound, upper_bound)
        print(f'{lower_bound=} -> {upper_bound=}')
        # Find and sort contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

        print(f"Found {len(contours)} contours in {infile} with values ranging from {lower_bound} -> {upper_bound}.")
        sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for i, contour in enumerate(sorted_contours):
            area = cv2.contourArea(contour)
            area *= 1*0.325
            if area > 0:
                # print(f"\rRank {i+1}: Area = {area:.2f} {MICRON}m", end="", flush=True)
                print(f"Rank {i+1}: Area = {area:.2f} {MICRON}m")
                cv2.drawContours(empty, contour, -1, 65535, 2)
                cv2.fillPoly(empty, [contour], 65535)
        print()
        output_path = os.path.join(image_path, "014.drawn.tif")
        cv2.imwrite(output_path, empty)
        print(f'Wrote drawn image to {output_path}')


    @staticmethod
    def ridge_response(image, sigma, beta, analysis_mask):
        # ============================================================
        # 6. Multi-scale Hessian ridge detector
        # ============================================================

        # Smooth at the scale we're detecting.
        smoothed = cv2.GaussianBlur(
            image,
            (0, 0),
            sigma
        )

        # Second derivatives.
        Ixx = cv2.Sobel(
            smoothed,
            cv2.CV_32F,
            2, 0,
            ksize=3
        )

        Iyy = cv2.Sobel(
            smoothed,
            cv2.CV_32F,
            0, 2,
            ksize=3
        )

        Ixy = cv2.Sobel(
            smoothed,
            cv2.CV_32F,
            1, 1,
            ksize=3
        )

        # Scale normalization.
        scale2 = sigma * sigma

        Ixx *= scale2
        Iyy *= scale2
        Ixy *= scale2

        # Eigenvalues of 2x2 Hessian.
        trace = Ixx + Iyy
        determinant = Ixx * Iyy - Ixy * Ixy

        discriminant = np.sqrt(
            np.maximum(
                trace * trace - 4 * determinant,
                0
            )
        )

        lambda1 = (trace - discriminant) / 2
        lambda2 = (trace + discriminant) / 2

        # Sort by absolute magnitude.
        swap = (
            np.abs(lambda1) >
            np.abs(lambda2)
        )

        temp = lambda1.copy()

        lambda1[swap] = lambda2[swap]
        lambda2[swap] = temp[swap]

        # Ratio describing how line-like the structure is.
        R = (
            np.abs(lambda1) /
            (np.abs(lambda2) + 1e-6)
        )

        # Overall second-derivative strength.
        S = np.sqrt(
            lambda1 * lambda1 +
            lambda2 * lambda2
        )

        # Adaptive normalization of S.
        c = np.percentile(
            S[analysis_mask > 0],
            90
        )

        # Line-likeness.
        line_term = np.exp(
            -(R * R) /
            (2 * beta * beta)
        )

        # Reject weak ridges.
        strength_term = 1 - np.exp(
            -(S * S) /
            (2 * c * c + 1e-12)
        )

        response = (
            line_term *
            strength_term
        )

        # Bright ridges have negative curvature
        # across the ridge.
        response[lambda2 >= 0] = 0

        return response


    def axon_detector(self):
        infile = "014.cropped.roi.unchanged.tif"
        image_path = f"/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/DK283/preps/C2/testing"
        image_inpath = os.path.join(image_path, infile)
        with tifffile.TiffFile(image_inpath) as tif:
            img = tif.asarray()

        # ============================================================
        # Configuration
        # ============================================================
        # Background scale.
        # Increase this if very broad structures are being removed.
        BACKGROUND_SIGMA = 15.0
        # Axon/ridge scales in pixels.
        # These are the scales I would start with for this image.
        RIDGE_SCALES = [2.5, 5.0, 7.0]
        # Controls how strongly blob-like structures are rejected.
        # Smaller = stronger preference for elongated ridges.
        BETA = 0.30
        # Local contrast threshold.
        CONTRAST_PERCENTILE = 98.0
        # Don't analyze pixels close to the FOV boundary.
        BOUNDARY_DISTANCE = 12
        # Minimum candidate connected-component size.
        MIN_AREA = 50

        # ============================================================
        # 1. Read original 16-bit image
        # ============================================================
        if img.dtype != np.uint16:
            raise RuntimeError(
                f"Expected uint16 image, got {img.dtype}"
            )

        print("Image:", img.shape)
        print("dtype:", img.dtype)
        print("min:", img.min())
        print("max:", img.max())
        # ============================================================
        # 2. Find the field of view
        # ============================================================

        # Pixels outside the specimen/FOV are exactly or almost exactly zero.
        fov = (img > 0).astype(np.uint8)

        # Keep largest connected region.
        num_labels, labels, stats, centroids = \
            cv2.connectedComponentsWithStats(fov, 8)

        print('num labels', num_labels)
        print('labels', labels)
        print('stats', stats)
        print('centroids', centroids)

        largest = 1 + np.argmax(
            stats[1:, cv2.CC_STAT_AREA]
        )

        fov = (labels == largest).astype(np.uint8)


        # ============================================================
        # 3. Remove the bright FOV perimeter
        # ============================================================

        distance = cv2.distanceTransform(fov,  cv2.DIST_L2,5)
        analysis_mask = (distance >= BOUNDARY_DISTANCE).astype(np.uint8)

        # ============================================================
        # 4. Estimate slowly varying background
        # ============================================================
        image32 = img.astype(np.float32)
        background = cv2.GaussianBlur(image32, (0, 0), BACKGROUND_SIGMA)
        # Bright structures relative to local background.
        contrast = image32 - background
        contrast[contrast < 0] = 0

        # ============================================================
        # 5. Robust normalization
        # ============================================================
        valid = contrast[analysis_mask > 0]
        lo = np.percentile(valid, 50)
        hi = np.percentile(valid, 99.8)

        contrast_norm = np.clip((contrast - lo) / (hi - lo),0,1).astype(np.float32)

        ridge_responses = []

        for sigma in RIDGE_SCALES:

            for beta in [0.20, 0.25, 0.30, 0.40, 0.50]:            

                response = self.ridge_response(
                    contrast_norm,
                    sigma,
                    beta,
                    analysis_mask
                )

                ridge_responses.append(response)


        # Keep strongest scale at every pixel.
        ridge = np.max(np.stack(ridge_responses),axis=0)

        # ============================================================
        # 7. Combine ridge response with local contrast
        # ============================================================
        contrast_threshold = np.percentile(valid, CONTRAST_PERCENTILE)

        candidate = (
            (ridge > 0.55) &
            (contrast > contrast_threshold) &
            (analysis_mask > 0)
            )


        # ============================================================
        # 8. Morphological cleanup
        # ============================================================
        candidate = (candidate.astype(np.uint8) *255)

        # Close small gaps in axons.
        candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

        # Remove isolated pixels.
        candidate = cv2.morphologyEx(candidate,  cv2.MORPH_OPEN,  np.ones((2, 2), np.uint8))

        # ============================================================
        # 9. Remove tiny connected components
        # ============================================================
        num_labels, labels, stats, centroids = \
            cv2.connectedComponentsWithStats(
                candidate,
                connectivity=8
            )

        axon_mask = np.zeros_like(candidate)

        for i in range(1, num_labels):

            area = stats[i,  cv2.CC_STAT_AREA]
            if area >= MIN_AREA:
                axon_mask[labels == i] = 255


        # ============================================================
        # 10. Save results
        # ============================================================
        image_path = f"/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/DK283/preps/C2/testing"

        output_path = os.path.join(image_path, "axon_mask.png")
        cv2.imwrite(output_path, axon_mask)
        print(f'Wrote axon mask to {output_path}')


        # Ridge response for diagnostics.
        ridge8 = np.clip(
            ridge * 255,
            0,
            255
        ).astype(np.uint8)

        output_path = os.path.join(image_path, "axon_ridge_response.png")
        cv2.imwrite(output_path, ridge8)
        print(f'Wrote ridge 8 to {output_path}')


    def combined_histogram_maker(self):
        image_path = f"/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/DK283/preps/C2"
        input_path = os.path.join(image_path, 'polygons')
        outpath = os.path.join(image_path, 'testing', 'combined_histogram.png')
        files = sorted(os.listdir(input_path))
        lfiles = len(files)
        hist_dict = Counter({})
        file_data = []
        for file in files:
            image_inpath = os.path.join(input_path, file)
            with tifffile.TiffFile(image_inpath) as tif:
                img = tif.asarray()

            file_data.append(img)

            try:
                flat = img.flatten()
                del img
            except:
                print(f"Could not flatten file {image_inpath}")
                lfiles -= 1
                continue
            try:
                img_counts = np.bincount(flat)
            except:
                print(f"Could not create counts {image_inpath}")
                lfiles -= 1
                continue
            try:
                img_dict = Counter(dict(zip(np.unique(flat), img_counts[img_counts.nonzero()])))
            except:
                print(f"Could not create counter {image_inpath}")
                lfiles -= 1
                continue
            try:
                hist_dict = hist_dict + img_dict
            except:
                print(f"Could not add files {image_inpath}")
                lfiles -= 1
                continue
        hist_dict = dict(hist_dict)
        hist_values = [i / lfiles for i in hist_dict.values()]
        fig = plt.figure()
        plt.rcParams["figure.figsize"] = [10, 6]
        plt.bar(list(hist_dict.keys()), hist_values, color='b')
        plt.yscale("log")
        plt.grid(axis="y", alpha=0.75)
        plt.xlabel("Value")
        plt.xlim(0, max(list(hist_dict.keys())))
        plt.ylabel("Frequency")
        log_max = math.log10(max(hist_dict.values()))
        #plt.ylim(bottom=1, top=100)
        plt.title(f"Combined histogram of ROI 16bit with {len(files)} TIF files", fontsize=14)
        plt.style.use("ggplot")
        fig.savefig(outpath, bbox_inches="tight")
        print(f'Wrote combined histogram to {outpath}')

        stack = np.stack(file_data, axis=0)
        combined_image = np.sum(stack, axis=0)
        
        # 3. Determine the dynamic range of the combined image
        min_val = int(np.min(combined_image))
        max_val = int(np.max(combined_image))
        print(f"Combined image range: Min={min_val}, Max={max_val}")
        
        # Define thresholds to test
        thresholds = np.arange(min_val, max_val + 1, 10)
        brightness_sums = []
    
        # 4. Calculate total brightness for each threshold
        print("Calculating brightness sums for each threshold...")
        for t in thresholds:
            # Get pixels above the current threshold
            above_threshold = combined_image[combined_image > t]
            # Sum their intensities
            brightness_sums.append(np.sum(above_threshold))

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(thresholds, brightness_sums, color='darkviolet', linewidth=2)
        ax.set_title(f'Sum of Brightness Values vs. Threshold (Active Range: {min_val}:{max_val})', fontsize=12, fontweight='bold')
        ax.set_xlabel('Threshold Value (Filtered to Active Range)', fontsize=12)
        ax.set_ylabel('Sum of Brightness Intensities', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_yscale('log')
        ax.set_xlim(min_val, max_val)
        pngfile = "combined_cumulative_intensities.png"
        outfile_path = os.path.join(image_path, 'testing', pngfile)
        fig.savefig(outfile_path, bbox_inches="tight")
        plt.close(fig)
        print(f'Wrote active range to: {outfile_path}')




    def histogram_maker(self):
        input_path = os.path.join(self.prep_path, f"{self.animal}/preps/C2/polygons")
        if not os.path.exists(input_path):
            print(f'Input path missing: {input_path}')
            exit(1)
        output_path = os.path.join(self.prep_path, f"{self.animal}/www/histogram/roi")
        os.makedirs(output_path, exist_ok=True)
        infiles = sorted(os.listdir(input_path))
        for infile in infiles:
            pngfile = infile.replace("tif", "png")
            outfile_path = os.path.join(output_path, pngfile)
            if os.path.exists(outfile_path):
                print(f'Histogram already exists: {outfile_path}')
                continue
            image_inpath = os.path.join(input_path, infile)
            with tifffile.TiffFile(image_inpath) as tif:
                image = tif.asarray()

            # Filter out zero values and flatten
            flat = image[image > 0].ravel()

            # Create and save histogram
            fig, ax = plt.subplots(figsize=(10, 6))
            try:
                ax.hist(flat, bins=200, range=(0, 2000), color="r")
            except:
                plt.close(fig)
                continue
            # ax.set_yscale('log')
            ax.grid(axis="y", alpha=0.75)
            ax.set_xlabel("Value")
            ax.set_ylabel("Frequency")
            ax.set_title(f"ROI in {infile}", fontsize=8)
            plt.style.use("ggplot")
            fig.savefig(outfile_path, bbox_inches="tight")
            plt.close(fig)
            print(f'Wrote histogram to: {outfile_path}')

    def find_contours(self):

        input_path = os.path.join(self.prep_path, f"{self.animal}/preps/C2/polygons")
        if not os.path.exists(input_path):
            print(f'Input path missing: {input_path}')
            exit(1)
        output_path = os.path.join(self.prep_path, f"{self.animal}/www/histogram/roi_contours")
        os.makedirs(output_path, exist_ok=True)
        infiles = sorted(os.listdir(input_path))
        for infile in infiles:
            if infile != "014.tif":
                continue

            image_inpath = os.path.join(input_path, infile)
            with tifffile.TiffFile(image_inpath) as tif:
                image = tif.asarray()

            image[image < 450] = 0
            flat = image[image > 0]
            ids, counts = np.unique(flat, return_counts=True)
            valid_mask = counts > 10
            filtered_ids = ids[valid_mask]

            if len(filtered_ids) > 0:
                lowest_id = filtered_ids[-1]
            else:
                continue

            lower_bound = int(lowest_id)
            upper_bound = int(flat.max())
            mask = cv2.inRange(image, lower_bound, upper_bound)
            ids, counts = np.unique(mask, return_counts=True)

            # 4. Find and sort contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

            empty = np.zeros_like(image)
            print('mask ids', ids)
            print('mask counts', counts)
            print(f"Found {len(contours)} contours in {infile} with values ranging from {lower_bound} -> {upper_bound}.")
            sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
            for i, contour in enumerate(sorted_contours):
                area = cv2.contourArea(contour)
                if area > 0:
                    # print(f"Rank {i+1}: Area = {32*0.325*area:.2f} um image area {32*0.325*image_size:.2f} % {100*(area/image_size):.4f}")
                    print(f"Rank {i+1}: Area = {1*0.325*area:.2f} {MICRON}m")
                    cv2.drawContours(empty, contour, -1, 65535, 2)
                    cv2.fillPoly(empty, [contour], 65535)
            output_path = os.path.join(self.prep_path, f"{self.animal}/preps/C2/testing/014.drawn.tif")
            cv2.imwrite(output_path, empty)

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
            pattern = r'data/(\w*)/neuroglancer_data'
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

            states = NeuroglancerState.objects.exclude(pk__in=ids).order_by('id').filter(active=False).all()
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
                elif layer_type == "cell":
                    print(f'layer type is cell, nothing to do')
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
                # print(f'child IDS={annotation.get("childAnnotationIds")}')
                print(f'\t# lines={number_of_children} child IDS={child_ids[:5]}')
            if annotation_type == 'line':
                print(f'\t\tAnnotation type={annotation_type} parentID={parent_id}', end=' ')
                print(f'\t\tid={annotation.get("id")} description={annotation.get("description")}')

    @staticmethod
    def show_v1_cloud_annotations(layer):
        name = layer['name']
        annotations = layer['annotations']
        print(f'Layer={name} has {len(annotations)} annotations')
        keys = set()
        return
        for annotation in annotations:
            # print(annotation.keys())
            keys.add(tuple(annotation.keys()))
            points = [ row['point'] for row in annotations if 'point' in row]
            pointsAB = [ row['pointA'] for row in annotations if 'pointA' in row]
            print(f'with # cloud points={len(points)}')
            print(f'with # annotation points={len(pointsAB)}')
        print(keys)

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

        # for a in existing_annotations:
        #    print(a)
        # return
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

        # volume_id = f"{Parsedata.random_string()}"
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
            # print(json_output)
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
    parser.add_argument("--downsample", help="Enter 'full' or 'thumbnail'", required=False, default="true", type=str, choices=("full", "thumbnail"))
    parser.add_argument('--debug', required=False, default='false', type=str)

    args = parser.parse_args()

    task = str(args.task).strip().lower()
    layer_type = str(args.layer_type).strip()
    layer_name = str(args.layer_name).strip()
    downsample = args.downsample.lower().strip()
    debug = bool({'true': True, 'false': False}[args.debug.lower()])    
    id = args.id

    pipeline = Parsedata(id=id, layer_type=layer_type, layer_name=layer_name, downsample=downsample, debug=debug)

    function_mapping = {
            "session": pipeline.parse_annotation,
            "fix": pipeline.fix_neuroglancer_state,
            "show": pipeline.show_annotations,
            "fix_animal": pipeline.update_neuroglancer_state_animal,
            "find_clouds": pipeline.find_clouds,
            "create_channel": pipeline.create_channel,
            "create_roi": pipeline.create_roi,
            "axon_detector": pipeline.axon_detector,
            "combined_histogram_maker": pipeline.combined_histogram_maker
        }

    if task in function_mapping:
        function_mapping[task]()
    else:
        print(f"{task} is not a correct task. Choose one of these:")
        for key in function_mapping.keys():
            print(f"\t{key}")
