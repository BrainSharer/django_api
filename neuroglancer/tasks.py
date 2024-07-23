"""
Background tasks must be in a file named: tasks.py
Don't move it to another file!
They also cannot accept objects as arguments. 
**Note: If you modify the tasks.py file, you must restart supervisord on the web server!!!**
``sudo systemctl restart supervisord.service``
"""
from neuroglancer.models import NeuroglancerState
from neuroglancer.contours.annotation_manager import AnnotationManager, DEBUG
from timeit import default_timer as timer

def upsert_annotations(layer, neuroglancer_state_id):
    """Does a delete then insert every time a user clicks 
    the 'Save annotations' button.

    :param layeri: the active layer in Neuroglancer we are working on
    :param neuroglancer_state_id: the primary key of the Neuroglancer state
    """

    neuroglancerState = NeuroglancerState.objects.get(pk=neuroglancer_state_id)
    manager = AnnotationManager(neuroglancerState)
    start_time = timer()
    manager.set_current_layer(layer) # This takes a LONG time for polygons/volumes!
    if DEBUG:
        end_time = timer()
        total_elapsed_time = round((end_time - start_time),2)
        print(f'Setting current layer took {total_elapsed_time} seconds.')

    assert manager.animal is not None
    assert manager.annotator is not None

    start_time = timer()
    manager.insert_annotations()
    if DEBUG:
        end_time = timer()
        total_elapsed_time = round((end_time - start_time),2)
        print(f'Inserting all annotations took {total_elapsed_time} seconds.')

