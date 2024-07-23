"""This module is responsible for the saving and restoring of the three different annotations.

A. Saving annotations - when the user clicks 'Save annotations' in Neuroglancer:


1. All data from the active layer gets sent to one of the three tables:
   
   * Marked cells
   * Polygon sequences
   * Structure COM

2. Data also gets sent to the annotations_point_archive table. This table has a unique
constraint. When the same data gets sent to the database, it updates it instead
of creating new useless inserts. This is done by Django's built-in bulk_create
method with the 'ignore_conficts' flag set to true. It also finds an existing
archive, or creates a new archive and uses that key for the FK_archive_set_ID. 
The constraint is on these columns:

   * Session ID (FK_session_id)
   * x Decimal(8,2) - formerly a float
   * y Decimal(8,2) - formerly a float
   * z Decimal(8,2) - formerly a float

B. Restoring annotations

1. This occurs when the user checks one and only one checkbox on the archive page. After
selecting a checkbox, the user chooses the 'Restore the selected archive' option from
the dropdown menu. Once the user clicks 'Go', these events take place:

    #. Get requested archive (set of points in the annotations_points_archive table)
    #. Mark session inactive that is in the archive
    #. Create a new active session and add it to either marked_cell, polygon_sequence or structureCOM
"""

#from django.http import Http404
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from django.db.models import ProtectedError
import numpy as np
from statistics import mode
from neuroglancer.models import AnnotationSession, BrainRegion, DEBUG, \
    PolygonSequence, StructureCom, PolygonSequence, MarkedCell, get_region_from_abbreviation
from neuroglancer.atlas import get_scales
from neuroglancer.models import CellType, UNMARKED
from neuroglancer.contours.annotation_layer import AnnotationLayer, Annotation, random_string
from neuroglancer.contours.annotation_base import AnnotationBase
from timeit import default_timer as timer

class AnnotationManager(AnnotationBase):
    """This class handles the management of annotations into the three tables: 

    #. MarkedCells
    #. StructureCOM
    #. PolygonSequence
    """

    def __init__(self, neuroglancerModel):
        """iniatiate the class starting from a perticular url

        :param neuroglancerModel (NeuroglancerState): query result from the 
        django ORM of the neuroglancer_state table
        """

        self.neuroglancer_model = neuroglancerModel
        self.owner_id = neuroglancerModel.owner.id
        self.MODELS = ['MarkedCell', 'PolygonSequence', 'StructureCom']
        self.set_annotator_from_id(neuroglancerModel.owner.id)
        self.set_animal_from_id(neuroglancerModel.animal)
        self.scale_xy, self.z_scale = get_scales(self.animal.prep_id)
        self.scales = np.array([self.scale_xy, self.scale_xy, self.z_scale])
        self.batch_size = 50

    def set_current_layer(self, state_layer):
        """set the current layer attribute from a layer component of neuroglancer json state.
           The incoming neuroglancer json state is parsed by a custom class named AnnotationLayer that 
           groups points according to it's membership to a polygon seqence or volume

        :param state_layer (dict): neuroglancer json state component of an annotation layer in dictionary form
        """

        assert 'name' in state_layer
        self.label = str(state_layer['name']).strip()
        self.current_layer = AnnotationLayer(state_layer) # This takes a long time


    def insert_annotations(self):
        """The main function that updates the database with annotations in the current_layer 
        attribute. This function loops each annotation in the current layer and 
        inserts data into the bulk manager. At the end of the loop, all data is in the bulk
        manager and it gets inserted. We also save the session to update the updated column.
        """

        session = None

        if self.animal is None or self.annotator is None:
            raise ValidationError("Error, missing animal or user.")
        
        marked_cells = []
        for annotation in self.current_layer.annotations:
            # marked cells are treated differently than com, polygon and volume
            if annotation.is_cell():
                marked_cells.append(annotation)
            if annotation.is_com():
                brain_region = get_region_from_abbreviation(annotation.get_description())
                session = self.get_session(brain_region=brain_region, annotation_type='STRUCTURE_COM')
                self.delete_com(session)
                self.add_com(annotation, session)
            if annotation.is_volume():
                brain_region = get_region_from_abbreviation(annotation.get_description())
                session = self.get_session(brain_region=brain_region, annotation_type='POLYGON_SEQUENCE')
                self.delete_polygons(session)
                self.add_polygons(annotation, session)


        if len(marked_cells) > 0:
            batch = []
            marked_cells = np.array(marked_cells)
            description_and_cell_types = np.array([f'{i.description}@{i.category}' for i in marked_cells])
            unique_description_and_cell_types = np.unique(description_and_cell_types)
            brain_region = get_region_from_abbreviation('point')
            session = self.get_session(brain_region=brain_region, annotation_type='MARKED_CELL')
            self.delete_marked_cells(session)
            for description_cell_type in unique_description_and_cell_types:
                in_category = description_and_cell_types == description_cell_type
                cells = marked_cells[in_category]
                _, cell_type = description_cell_type.split('@')
                if cells[0].description == 'positive':
                    source = 'HUMAN_POSITIVE'
                elif cells[0].description == 'negative':
                    source = 'HUMAN_NEGATIVE'
                else:
                    source = UNMARKED
                
                for cell in cells:
                    cell_type_object = CellType.objects.filter(cell_type=cell_type).first()
                    marked_cell = self.create_marked_cell(cell, session, cell_type_object, source)
                    batch.append(marked_cell)
                    
            MarkedCell.objects.bulk_create(batch, self.batch_size, ignore_conflicts=True)
            if DEBUG:
                print(f'Adding {len(batch)} rows to marked cells with session ID={session.id}')

        if session is not None:
            session.neuroglancer_model = self.neuroglancer_model
            session.save()

    def delete_com(self, session: Annotation):
        try:
            StructureCom.objects.filter(annotation_session=session).delete()
        except ProtectedError:
            error_message = "Error trying to delete the COMs."
            return JsonResponse(error_message)
        
    def delete_marked_cells(self, session: Annotation):
        try:
            MarkedCell.objects.filter(annotation_session=session).delete()
        except ProtectedError:
            error_message = "Error trying to delete the marked cells."
            return JsonResponse(error_message)
        
    def delete_polygons(self, session: Annotation):
        try:
            PolygonSequence.objects.filter(annotation_session=session).delete()
        except ProtectedError:
            error_message = "Error trying to delete the polygons."
            return JsonResponse(error_message)


    def is_structure_com(self, annotation: Annotation):
        """Determines if a point annotation is a structure COM.
        A point annotation is a COM if the description corresponds to a structure 
        existing in the database.
        
        :param annotationi (Annotation): the annotation object 
        :return boolean: True or False
        """

        assert annotation.is_point()
        description = annotation.get_description()
        if description is not None:
            description = str(description).replace('\n', '').strip()
            return bool(BrainRegion.objects.filter(abbreviation=description).first())
        else:
            return False

    def add_com(self, annotation: Annotation, annotation_session: AnnotationSession):
        """Helper method to add a COM to the bulk manager.

        :param annotationi: A COM annotation
        :param annotation_session: session object
        """

        x, y, z = np.floor(annotation.coord) * (self.scales).astype(np.float64)
        com = StructureCom(annotation_session=annotation_session, source='MANUAL', x=x, y=y, z=z)
        com.save()

    def create_marked_cell(self, annotation: Annotation, annotation_session: AnnotationSession, 
        cell_type, source) -> MarkedCell:
        """Helper method to create a MarkedCell object.

        :param annotationi: A COM annotation
        :param annotation_session: session object
        :param cell_type: the cell type object of the marked cell
        :param source: the MARKED/UNMARKED source
        :return: MarkedCell object
        """

        x, y, z = np.floor(annotation.coord) * (self.scales).astype(np.float64)
        return MarkedCell(annotation_session=annotation_session,
                          source=source, x=x, y=y, z=z, cell_type=cell_type)

    def add_polygons(self, annotation: Annotation, annotation_session: AnnotationSession):
        """Helper method to add a polygon to the bulk manager.

        :param annotationi: A polygon annotation
        :param annotation_session: session object
        """

        start_time = timer()

        batch = []
        for polygon in annotation.childs:
            point_order = 1
            polygon_index = random_string()
            z = mode([int(np.floor(coord.coord_start[2]) * float(self.z_scale)) for coord in polygon.childs])
            for child in polygon.childs:
                xa, ya, _ = child.coord_start * (self.scales).astype(np.float64)
                polygon_sequence = PolygonSequence(annotation_session=annotation_session, x=xa, y=ya, z=z, point_order=point_order, polygon_index=str(polygon_index))
                point_order += 1
                batch.append(polygon_sequence)
                
        PolygonSequence.objects.bulk_create(batch, self.batch_size, ignore_conflicts=True)
        
        if DEBUG:
            end_time = timer()
            total_elapsed_time = round((end_time - start_time),2)
            print(f'Inserting polygon {len(batch)} points to {annotation.get_description()} took {total_elapsed_time} seconds.')

    def get_session(self, brain_region, annotation_type):
        """Gets either the existing session or creates a new one.
        We first try by trying to get the exact NeuroglancerState (AKA, neuroglancer state). 
        If that doesn't succeed, we try without the state ID

        :param brain_region: brain region object AKA structure
        :param annotation_type: either marked cell or polygon or COM
        """
        
        annotation_session = AnnotationSession.objects.filter(active=True)\
            .filter(annotation_type=annotation_type)\
            .filter(animal=self.animal)\
            .filter(neuroglancer_model=self.neuroglancer_model)\
            .filter(brain_region=brain_region)\
            .filter(annotator=self.annotator)\
            .order_by('-created').first()
            
        if annotation_session is None:
            annotation_session = AnnotationSession.objects.filter(active=True)\
                .filter(annotation_type=annotation_type)\
                .filter(animal=self.animal)\
                .filter(brain_region=brain_region)\
                .filter(annotator=self.annotator)\
                .order_by('-created').first()

        if annotation_session is None:
            annotation_session = self.create_new_session(brain_region, annotation_type)
            
        return annotation_session

    def create_new_session(self, brain_region: BrainRegion, annotation_type: str):
        """Helper method to create a new annotation_session
        
        :param brain_region: brain region object AKA structure
        :param annotation_type: either marked cell or polygon or COM
        """

        annotation_session = AnnotationSession.objects.create(
            animal=self.animal,
            neuroglancer_model=self.neuroglancer_model,
            brain_region=brain_region,
            annotator=self.annotator,
            annotation_type=annotation_type, 
            active=True)
        return annotation_session

