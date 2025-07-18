import os, sys
from pathlib import Path
import django

PATH = Path('.').absolute().as_posix()
sys.path.append(PATH)
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brainsharer.settings')
django.setup()


from brain.models import Animal, SlideCziToTif


#animals = Animal.objects.filter(active=True).filter(prep_id='DK79').order_by('prep_id')
animals = Animal.objects.filter(active=True).order_by('prep_id')

for animal in animals:
    channel1_tifs = SlideCziToTif.objects.filter(slide__scan_run__prep=animal).filter(active=True).filter(channel=1).order_by('slide__slide_physical_id', 'scene_number')
    channel2_tifs = SlideCziToTif.objects.filter(slide__scan_run__prep=animal).filter(active=True).filter(channel=2).order_by('slide__slide_physical_id', 'scene_number')
    channel3_tifs = SlideCziToTif.objects.filter(slide__scan_run__prep=animal).filter(active=True).filter(channel=3).order_by('slide__slide_physical_id', 'scene_number')
    for i, tif in enumerate(channel1_tifs):       
        tif.scene_order = i
        tif.save()
    print(f"Processed {len(channel1_tifs)} tifs for animal {animal.prep_id} channel 1")

    if len(channel2_tifs) == len(channel1_tifs):
        for i, tif in enumerate(channel2_tifs):       
            tif.scene_order = i
            tif.save()
    print(f"Processed {len(channel2_tifs)} tifs for animal {animal.prep_id} channel 2")


    if len(channel3_tifs) == len(channel1_tifs):
        for i, tif in enumerate(channel3_tifs):       
            tif.scene_order = i
            tif.save()
    print(f"Processed {len(channel3_tifs)} tifs for animal {animal.prep_id} channel 3")
