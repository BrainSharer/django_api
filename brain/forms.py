"""This module defines the forms necessary to perform the QC on the slides/scenes.
The user can rearrange, edit, and hide scenes with these forms.
"""
from django import forms
from django.forms import ModelChoiceField
from brain.models import Animal, SlideCziToTif
from import_export.forms import ExportForm

from django.forms.models import BaseInlineFormSet
from django.db import transaction
from django.db.models import Q
import copy


class AnimalForm(forms.Form):
    """Sets up fields for the select dropdown menu in forms.
    Animals are sorted by name.
    """
    prep_id = ModelChoiceField(label='Animal',
                               queryset=Animal.objects.all().order_by('prep_id'),
                               required=False,
                               widget=forms.Select(attrs={'onchange': 'id_list.submit();', 'class': 'form-control'}))

    class Meta:
        fields = ('prep_id',)

class AnimalChoiceField(forms.ModelChoiceField):
    """A simple class that returns the animal name.
    """
    def label_from_instance(self, obj):
        return obj.prep_id


def get_slide_channels(slide):
    channels = SlideCziToTif.objects.filter(slide=slide).filter(active=True).values('channel').distinct().count()
    return channels


def scene_reorder(slide):
    """ Helper method to reorder a set of scenes.

    :param slide: An integer for the primary key of the slide.
    """
    scenes_tifs = SlideCziToTif.objects.filter(slide=slide).filter(active=True).order_by('scene_number')
    channels = get_slide_channels(slide)
    len_tifs = len(scenes_tifs) + 1
    flattened = [item for sublist in [[i] * channels for i in range(1, len_tifs)] for item in sublist]
    for new_scene, tif in zip(flattened, scenes_tifs):  # iterate over the scenes
        tif.scene_number = new_scene
        tif.save()


class TifInlineFormset(BaseInlineFormSet):
    """
    A custom inline formset that:
    1. Detects and updates only changed fields.
    2. Updates similar rows (e.g., same group_field).
    3. Duplicates rows based on an integer field (duplicate_count).
    4. Uses a single atomic transaction for performance and consistency.
    """

    # configure which field defines “similar rows”
    group_field = 'channel'          # example: all rows with same category are similar
    duplicate_field = 'copy_count'  # integer field for how many times to copy
    fields_we_are_changing = ['active', 'scene_number']

    def create_id_dictionary(self, instance):
        queryset = SlideCziToTif.objects.filter(slide=instance.slide).filter(active=True)
        channel_ids = {obj.id: obj.channel for obj in queryset}
        return channel_ids

    def save(self, commit=True):
        """
        Override the default save to handle:
        - selective updates
        - propagating changes to similar rows
        - duplication logic
        """
        # track instances for later
        updated_instances = super().save(commit=False)

        # Defer all DB operations to a single atomic commit
        with transaction.atomic():
            for form in self.forms:
                if not form.has_changed():
                    continue  # skip unchanged forms

                instance = form.save(commit=False)
                changed_fields = form.changed_data
                if instance.pk:
                    # update the instance only on changed fields
                    instance.save(update_fields=changed_fields)
                    updated_instances.append(instance)

                    # propagate changes to similar rows
                    self._update_other_channels(instance, changed_fields, form)

                # handle duplication
                self._handle_duplication(instance)

        return updated_instances

    def _update_other_channels(self, instance, changed_fields, form):
        update_changed_fields = copy.deepcopy(changed_fields)
        if set(update_changed_fields).intersection(set(self.fields_we_are_changing)) == set():
            return  # no relevant fields changed

        rows = self.get_other_channels(instance)
        # Apply same changes to similar rows
        update_data = {field: getattr(instance, field) for field in update_changed_fields}
        if update_data:
            for row in rows:
                for field in update_changed_fields:
                        setattr(row, field, form.cleaned_data[field])
                row.save()            

    def _handle_duplication(self, instance):
        """
        Duplicate the instance N times (based on `duplicate_field`),
        and optionally create dependent duplicates based on the group field.
        """
        n = getattr(instance, self.duplicate_field, 0)
        if not n or n < 1:
            return

        #model = instance.__class__
        #related_manager = getattr(instance, self.fk.name)

        duplicates = []
        other_channels = self.get_other_channels(instance)

        for _ in range(n):
            # clone channel 1
            clone = self._clone_instance(instance)
            clone.save()
            duplicates.append(clone)

            # also duplicate channels 2,3 n number of times
            for sim in other_channels:
                sim_clone = self._clone_instance(sim)
                sim_clone.save()
                duplicates.append(sim_clone)

        # reset copy_count on original instance to 0
        instance.copy_count = 0
        instance.save()
        return duplicates

    def _clone_instance(self, instance):
        """
        Returns a shallow copy of the model instance suitable for saving as a new row.
        """
        clone = instance.__class__.objects.get(pk=instance.pk)
        clone.pk = None  # reset primary key
        clone.copy_count = 0  # reset copy count on clone
        #clone.save()
        return clone


    def get_other_channels(self, instance):
        other_rows = []
        channel_count = get_slide_channels(instance.slide) + 1
        other_channels = [i for i in range(2, channel_count)]
        channel_names = []

        for channel in other_channels:
            channel_filename = instance.file_name.replace('_C1.tif', f'_C{channel}.tif')
            channel_names.append(channel_filename)
            other_channel = self.model.objects.filter(slide=instance.slide).filter(file_name=channel_filename).filter(active=True).first()
            other_rows.append(other_channel)

        return other_rows

    """

    def duplicate_row(self, instance, count):
        for i in range(count):
            clone = self.model.objects.get(pk=instance.pk)
            clone.pk = None
            clone.copy_count = 0  # reset copy count on clone
            clone.save()

            # Also duplicate similar rows
            for sim in self.get_other_channels(instance):
                sim_copy = self.model.objects.get(pk=sim.pk)
                sim_copy.pk = None
                sim.copy_count = 0  # reset copy count on clone
                sim_copy.save()

    def update_changed_fields(self, instance, form):
        changed_fields = form.changed_data
        if 'copy_count' in changed_fields:
            changed_fields.remove('copy_count')  # exclude copy_count from update fields
        if not changed_fields:
            return

        for field in changed_fields:
            setattr(instance, field, form.cleaned_data[field])
        instance.save(update_fields=changed_fields)

    @transaction.atomic
    def save(self, commit=True):
        instances = super().save(commit=False)

        for form in self.forms:
            slide_tif = form.instance
            # checks for changed form, changed data and existing pk
            if form.has_changed():
                # Update channel 1
                self.update_changed_fields(slide_tif, form)

                # Determine changed fields excluding copy_count
                changed_fields = form.changed_data
                if 'copy_count' in changed_fields:
                    changed_fields.remove('copy_count')  # exclude copy_count from update fields
                if len(changed_fields) > 0:
                    for field in changed_fields:
                        setattr(slide_tif, field, form.cleaned_data[field])
                    slide_tif.copy_count = 0  # reset copy count on save
                    slide_tif.save(update_fields=changed_fields)

                    # Update channels 2 and up if they exist
                    for similar in self.get_other_channels(slide_tif):
                        for field_name in changed_fields:
                            setattr(similar, field_name, form.cleaned_data[field_name])
                            print(f'Setting {field_name} from {getattr(similar, field_name)} to {form.cleaned_data[field_name]}')
                        similar.copy_count = 0  # reset copy count on similar
                        similar.save(update_fields=changed_fields)

                # Handle duplication
                count = form.cleaned_data.get("copy_count", 0)
                if count > 0:
                    self.duplicate_row(slide_tif, count)
                    scene_reorder(slide_tif.slide)

            else:
                print(f'No changes for slide_tif id {slide_tif.id}, skipping update and duplications')

        
        return instances


    @transaction.atomic
    def saveXXXXXXXXX(self, commit=True):
        instances = super().save(commit=False)
        saved_instances = []
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE', False):
                continue

            if form.has_changed():
                # The instance linked to this form
                slide_tif = form.instance

                if slide_tif.pk and form.changed_data:
                    channel_count = get_slide_channels(slide_tif.slide) + 1
                    other_channels = [i for i in range(2, channel_count)]
                    # Existing instance: update only changed fields
                    changed_fields = form.changed_data
                    update_dict = {}
                    for field_name in changed_fields:
                        update_dict[field_name] = form.cleaned_data[field_name]
                        setattr(slide_tif, field_name, form.cleaned_data[field_name])

                    # Update channel 1
                    slide_tif.save(update_fields=changed_fields)
                    saved_instances.append(slide_tif)
                    # update other channels
                    for channel in other_channels:
                        channel_filename = slide_tif.file_name.replace('_C1.tif', f'_C{channel}.tif')
                        SlideCziToTif.objects.filter(slide=slide_tif.slide).filter(channel=channel).filter(file_name=channel_filename)\
                            .update(**update_dict)
                        
                    # Duplicate logic
                    copy_count = form.cleaned_data.get("copy_count", 1)
                    if copy_count > 1:
                        print(f'Duplicating slide {slide_tif.id} for {copy_count} copies')
                        for _ in range(copy_count - 1):
                            print(f'Duplicating slide {slide_tif.id} for other channels {other_channels}')
                            clones = self._duplicate_instance(slide_tif, other_channels)
                            for clone in clones:
                                clone.save()
                                saved_instances.append(clone)

                saved_instances.append(slide_tif)

        return saved_instances        
    
    """

class AnimalFormMixin(forms.Form):
    animal = forms.ModelChoiceField(queryset=Animal.objects.all(), required=True)

class CustomExportForm(AnimalFormMixin, ExportForm):
    """Customized ExportForm, with author field required."""
    animal = forms.ModelChoiceField(
        queryset=Animal.objects.all(),
        required=True)