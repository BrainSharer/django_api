"""
This page lists the classes and methods used to administer the 'Brain' app in 
our database portal. This is where the end user can create, retrieve, update and delete (CRUD)
metadata associated with the 'Brain' app. It does not list the fields (database columns). Look 
in the models document for the database table model.
"""

from django.contrib import admin
from django.conf import settings
from django.shortcuts import HttpResponseRedirect
from django.utils.safestring import mark_safe
from adminsortable2.admin import SortableAdminMixin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from brain.forms import save_slide_model, TifInlineFormset, scene_reorder, CustomExportForm
from brain.models import (Animal, Histology, Injection, Virus, InjectionVirus,
                          ScanRun, Slide, SlideCziToTif, Section)
from brainsharer.admin_extensions import AtlasAdminModel, ExportCsvMixin


@admin.register(Animal)
class AnimalAdmin(AtlasAdminModel, ExportCsvMixin):
    """This class is used to administer the animal. It includes all the metadata
    entered by the user. The animal class is often used as a key in another table.
    """

    list_display = ('prep_id', 'comments', 'histogram', 'created')
    search_fields = ('prep_id',)
    ordering = ['prep_id']
    exclude = ('created',)



@admin.register(Histology)
class HistologyAdmin(AtlasAdminModel, ExportCsvMixin):
    """A class to administer the histology of each animal

    :Inheritance:
        :AtlasAdminModel: The base admin model
        :ExportCsvMixin: The class with standard features and CSV 
            exporter method.

    """
    list_display = ('prep_id', 'performance_center')
    search_fields = ('prep__prep_id',)
    autocomplete_fields = ['prep_id']
    ordering = ['prep_id']
    exclude = ('created',)

    class Media:
        js = ('admin/js/histology.js',)  # relative path in static folder

@admin.register(Injection)
class InjectionAdmin(AtlasAdminModel, ExportCsvMixin):
    """A class to describe the injections (if any) for each animal. 
    Each animal can have multiple injections.

    :Inheritance:
        :AtlasAdminModel: The base admin model
        :ExportCsvMixin: The class with standard features and CSV 
            exporter method.

    """
    list_display = ('prep_id', 'performance_center', 'anesthesia', 'comments', 'created')
    search_fields = ('prep__prep_id',)
    ordering = ['created']

@admin.register(Virus)
class VirusAdmin(AtlasAdminModel, ExportCsvMixin):
    """A class used to describe a virus. This class can then be a 
    foreign key into the Injection class

    :Inheritance:
        :AtlasAdminModel: The base admin model
        :ExportCsvMixin: The class with standard features and CSV 
            exporter method.

    """
    list_display = ('virus_name', 'virus_type', 'type_details', 'created')
    search_fields = ('virus_name',)
    ordering = ['virus_name']

@admin.register(InjectionVirus)
class InjectionVirusAdmin(AtlasAdminModel):
    """This class describes a many to many relationship between the 
    virus and the injection classes. An animal can multiple 
    injections, with each injection having one or more viruses.

    :Inheritance:
        :AtlasAdminModel: The base admin model

    """
    list_display = ('prep_id', 'virus_name', 'created')
    fields = ['injection', 'virus']
    ordering = ['created']

    def prep_id(self, instance):
        """This returns the animal name (string) used as a
        foreign key in this class.

        :param instance: the obj
        :return: the prep_id (AKA the animal name) as a string
        """
        return instance.injection.prep

    def virus_name(self, instance):
        """Gives the description from the virus foreign key

        :param instance: the obj
        """
        return instance.virus.virus_name

@admin.register(ScanRun)
class ScanRunAdmin(AtlasAdminModel, ExportCsvMixin):
    """This class describes what occurs when the slides are actually 
    scanned. Many of the attributes from this class are used 
    throughout the preprocessing  An animal can have multiple
    scan runs, but usually, there is just one scanning done 
    for each animal.

    :Inheritance:
        :AtlasAdminModel: The base admin model
        :ExportCsvMixin: The class with standard features and CSV 
            exporter method.
    """
    list_display = ('prep_id', 'resolution', 'zresolution', 'number_of_slides', 'machine','comments', 'created')
    search_fields = ('prep__prep_id',)
    ordering = ['prep_id', 'machine','comments', 'created']


class TifInline(admin.TabularInline):
    """This class is solely used for the database QA. It will display the 
    associated TIFF files for each 
    slide on the slide page.

    :Inheritance:
        :admin.TabularInline: The class that describes how the data is 
            laid out on the page.
    """
    model = SlideCziToTif
    fields = ('file_name','scene_number', 'active', 'scene_index', 'section_number', 'channel', 
        'scene_image', 'section_image')
    readonly_fields = ['file_name', 'section_number', 'channel', 
        'scene_index', 'scene_image', 'section_image']
    ordering = ['-active', 'scene_number', 'scene_index']
    extra = 0
    can_delete = False
    formset = TifInlineFormset
    template = 'admin/brain/tabular_tifs.html'
    
    def section_number(self, obj) -> str:
        """
        Returns the section number of a given object as a zero-padded string with a ".tif" extension.
        Args:
            obj: The object for which the section number is to be determined. It is expected to have 
                 a related slide, scan_run, and prep_id attributes.
        Returns:
            str: The section number formatted as a zero-padded string with a ".tif" extension.
        The function performs the following steps:
        1. Retrieves the animal identifier from the object's related slide's scan_run's prep_id.
        2. Fetches the corresponding Histology object using the animal identifier.
        3. Determines the order of sections based on the 'side_sectioned_first' attribute of the Histology object.
        4. Filters and orders the Section objects based on the determined order.
        5. Finds the index of the given object's ID in the ordered list of Section IDs.
        6. Returns the index as a zero-padded string with a ".tif" extension.
        """
        animal = obj.slide.scan_run.prep_id
        histology = Histology.objects.get(prep_id=animal)
        orderby = histology.side_sectioned_first

        if orderby == 'Right':
            sections =  Section.objects.filter(prep_id__exact=animal).filter(channel=1)\
                .order_by('-slide_physical_id', '-scene_number')
        else:
            sections = Section.objects.filter(prep_id__exact=animal).filter(channel=1)\
                .order_by('slide_physical_id', 'scene_number')

        index = list(sections.values_list('id', flat=True)).index(obj.id)
        return str(index).zfill(3) + ".tif"

    section_number.short_description = 'Section' 

    def scene_image(self, obj):
        """This method tests if there is a 
        PNG file for each scene, and if so, shows it on the QA page 
        for each slide. This is very helpful when the user must decide
        if the TIFF file is usable.

        :param obj: the TIFF obj
        :return: HTML that displays a link to the scene PNG file
        """
        animal = obj.slide.scan_run.prep_id
        tif_file = obj.file_name
        png = tif_file.replace('tif', 'png')
        thumbnail = f"https://imageserv.dk.ucsd.edu/data/{animal}/scene/{png}"
        onerror = 'https://brainsharer.org/images/screenshot/placeholder.png'
        return mark_safe(
            '<div class="profile-pic-wrapper"><img src="{}" onerror="this.onerror=null; this.src=\'{}\'" alt="" /></div>'.format(thumbnail, onerror))

    scene_image.short_description = 'Pre Image'

    def section_image(self, obj):
        """This method shows the TIFF image as 
        a PNG later on in the QA process after it has been cleaned and aligned.

        :param obj: the TIFF obj
        :return: HTML that displays a link to the scene PNG file
        """
        animal = obj.slide.scan_run.prep_id
        tif_file = self.section_number(obj)
        png = tif_file.replace('tif', 'png')
        filepath = f"{animal}/section/{png}"
        thumbnail = f"https://imageserv.dk.ucsd.edu/data/{filepath}"
        onerror = 'https://brainsharer.org/images/screenshot/placeholder.png'
        return mark_safe(
            '<div class="profile-pic-wrapper"><img src="{}" onerror="this.onerror=null; this.src=\'{}\'" alt=""/></div>'.format(thumbnail, onerror))

    section_image.short_description = 'Post Image'


    def get_formset(self, request, obj=None, **kwargs):
        """Description of get_formset - sets up the form for the set of 
        TIFF files for each slide

        :param request: http request
        :param obj: the TIFF obj
        :param kwargs: extra args
        :return: the HTML of the formset
        """
        formset = super(TifInline, self).get_formset(request, obj, **kwargs)
        formset.request = request
        return formset

    def get_queryset(self, request):
        """Description of get_queryset - returns just the first channel 
        for each slide. We only need to look
        at the first channel for QA purposes.

        :param obj: the TIFF obj
        :return: a query set
        """
        qs = super(TifInline, self).get_queryset(request)
        results = qs.filter(channel=1)
        return results

    def has_add_permission(self, request, obj=None):
        """TIFF files cannot be added 
        at this stage.

        :param request: http request
        :param obj: the TIFF obj
        :return: False
        """
        return False

    def has_change_permission(self, request, obj=None):
        """TIFF files can be edited at this stage.

        :param request: http request
        :param obj: the TIFF obj
        :return: True
        """
        return True

@admin.register(Slide)
class SlideAdmin(AtlasAdminModel, ExportCsvMixin):
    """This class describes the admin area for a particular slide. This 
    is used in the QA process and includes
    the inline TIFF files in the QA form.

    :Inheritance:
        :AtlasAdminModel: The base admin model
        :ExportCsvMixin: The class with standard features and CSV 
            exporter method.
    """
    change_form_template = 'admin/brain/slide_change_form.html'

    list_display = ('prep_id', 'slide_physical_id', 'slide_status', 'comments', 'scene_count')
    search_fields = ['scan_run__prep__prep_id', 'file_name']
    ordering = ['file_name', 'created']
    readonly_fields = ['file_name', 'slide_physical_id', 'scan_run', 'processed', 'file_size', 
                       'previous_preview_tag', 'current_preview_tag', 'following_preview_tag']

    def get_fields(self, request, obj):
        """This method fetches the correct 
        number of inline TIFF files that are used
        in the QA form.

        :param request: http request
        :param obj: the TIFF obj
        :return: HTML of the fields
        """
        # count = self.scene_count(obj)
        scene_indexes = list(SlideCziToTif.objects\
                            .filter(slide=obj).filter(channel=1).filter(active=True)\
                            .order_by('-active','scene_number','scene_index').values_list('scene_index', flat=True))
        scene_indexes = sorted(set(scene_indexes))

        slide_ids = list(Slide.objects.filter(scan_run=obj.scan_run).filter(active=True).order_by('slide_physical_id').values_list('slide_physical_id', flat=True))
        all_previews = ['previous_preview_tag', 'current_preview_tag', 'following_preview_tag']
        self.previews = []
        current_index = slide_ids.index(obj.slide_physical_id)
        print(f'DEBUG: {current_index}, {slide_ids}')
        if current_index > 0:
            previous_index = slide_ids.index(slide_ids[current_index - 1])
            self.previews.append(all_previews[0])
            self.previous_slide = Slide.objects.filter(scan_run=obj.scan_run).filter(active=True).filter(slide_physical_id=slide_ids[previous_index]).first()

        self.previews.append(all_previews[1])

        try:
            following_index = slide_ids.index(slide_ids[current_index + 1])
            self.previews.append(all_previews[2])
            self.following_slide = Slide.objects.filter(scan_run=obj.scan_run).filter(active=True).filter(slide_physical_id=slide_ids[following_index]).first()
        except IndexError:
            pass

        fields = ['file_name', 'scan_run', 'slide_physical_id', 'slide_status']
        replication_fields = {
            0: ['insert_before_one'],
            1: ['insert_between_one_two'],
            2: ['insert_between_two_three'],
            3: ['insert_between_three_four'],
            4: ['insert_between_four_five'],
            5: ['insert_between_five_six'],
            6: ['insert_between_six_seven'],
            7: ['insert_between_seven_eight']
        }
        for scene_index in scene_indexes:
            if scene_index in replication_fields:
                fields.extend(replication_fields[scene_index])

        fields.extend(['comments'])
        fields.extend(self.previews)

        return fields

    inlines = [TifInline, ]

    def previous_preview_tag(self, obj):
        png = self.previous_slide.file_name.replace('czi', 'png')
        full_res_url = thumbnail = f"https://imageserv.dk.ucsd.edu/data/{self.previous_slide.scan_run.prep}/slides_preview/{png}"
        # full_res_png = png.replace('.png', '_full.png')
        # full_res_url = f"https://imageserv.dk.ucsd.edu/data/{self.previous_slide.scan_run.prep}/slides_preview/{full_res_png}"
        full_checksum = self.previous_slide.checksum
        if full_checksum is None:
            truncated_checksum = 'None'
        else:
            truncated_checksum = full_checksum[-6:]

        toggle_script = f"""
            <script>
            function togglePreviousChecksum(element) {{
                var fullChecksum = "{full_checksum}";
                var truncatedChecksum = "{truncated_checksum}";
                if (element.textContent === truncatedChecksum) {{
                    element.textContent = fullChecksum;
                    element.title = "Click to show truncated checksum";
                }} else {{
                    element.textContent = truncatedChecksum;
                    element.title = "Click to show entire sha256 checksum";
                }}
            }}
            </script>
            """
        checksum_display = f'<span onclick="togglePreviousChecksum(this)" style="cursor: pointer; color: blue; text-decoration: underline;" title="Click to show entire sha256 checksum">{truncated_checksum}</span>'
        return mark_safe(f'''{toggle_script} 
        <a href="{full_res_url}" target="_blank"><img src="{thumbnail}" alt="previous preview" style="cursor: pointer;" title="Click to view full resolution in new window"/></a>
        <caption><h3>{self.previous_slide.file_name} ({checksum_display})</h3></caption>''')
    previous_preview_tag.short_description = 'Previous' 

    def current_preview_tag(self, obj):
        png = obj.file_name.replace('czi', 'png')
        thumbnail = f"https://imageserv.dk.ucsd.edu/data/{obj.scan_run.prep}/slides_preview/{png}"
        full_res_png = png.replace('.png', '_full.png')
        full_res_url = f"https://imageserv.dk.ucsd.edu/data/{obj.scan_run.prep}/slides_preview/{full_res_png}"
        full_checksum = obj.checksum
        if full_checksum is None:
            truncated_checksum = 'None'
        else:
            truncated_checksum = full_checksum[-6:]

        toggle_script = f"""
            <script>
            function toggleChecksum(element) {{
                var fullChecksum = "{full_checksum}";
                var truncatedChecksum = "{truncated_checksum}";
                if (element.textContent === truncatedChecksum) {{
                    element.textContent = fullChecksum;
                    element.title = "Click to show truncated checksum";
                }} else {{
                    element.textContent = truncatedChecksum;
                    element.title = "Click to show entire sha256 checksum";
                }}
            }}
            </script>
            """
        checksum_display = f'<span onclick="toggleChecksum(this)" style="cursor: pointer; color: blue; text-decoration: underline;" title="Click to show entire sha256 checksum">{truncated_checksum}</span>'
        return mark_safe(f'''{toggle_script}
        <a href="{full_res_url}" target="_blank"><img src="{thumbnail}" alt="current preview" style="cursor: pointer;" title="Click to view full resolution in new window"/></a>
        <caption><h3>{obj.file_name} ({checksum_display})</h3></caption>''')
    current_preview_tag.short_description = 'Current'

    def following_preview_tag(self, obj):
        png = self.following_slide.file_name.replace('czi', 'png')
        thumbnail = f"https://imageserv.dk.ucsd.edu/data/{self.following_slide.scan_run.prep}/slides_preview/{png}"
        full_res_png = png.replace('.png', '_full.png')
        full_res_url = f"https://imageserv.dk.ucsd.edu/data/{self.following_slide.scan_run.prep}/slides_preview/{full_res_png}"
        full_checksum = self.following_slide.checksum
        if full_checksum is None:
            truncated_checksum = 'None'
        else:
            truncated_checksum = full_checksum[-6:]

        toggle_script = f"""
            <script>
            function toggleFollowingChecksum(element) {{
                var fullChecksum = "{full_checksum}";
                var truncatedChecksum = "{truncated_checksum}";
                if (element.textContent === truncatedChecksum) {{
                    element.textContent = fullChecksum;
                    element.title = "Click to show truncated checksum";
                }} else {{
                    element.textContent = truncatedChecksum;
                    element.title = "Click to show entire sha256 checksum";
                }}
            }}
            </script>
            """
        checksum_display = f'<span onclick="toggleFollowingChecksum(this)" style="cursor: pointer; color: blue; text-decoration: underline;" title="Click to show entire sha256 checksum">{truncated_checksum}</span>'
        return mark_safe(f'''{toggle_script}
        <a href="{full_res_url}" target="_blank"><img src="{thumbnail}" alt="next slide preview" style="cursor: pointer;" title="Click to view full resolution in new window"/></a>
        <caption><h3>{self.following_slide.file_name} ({checksum_display})</h3></caption>''')
    following_preview_tag.short_description = 'Next'

    
    def scene_count(self, obj):
        """Determines how many scenes are 
        there for a slide

        :param obj: the slide obj
        :return: an integer of the number of scenes
        """

        scenes = SlideCziToTif.objects.filter(slide__id=obj.id).filter(channel=1).filter(active=True).values_list('id').distinct()
        count = len(scenes)
        return count

    scene_count.short_description = "Active Scenes"

    def get_queryset(self, request):
        """Description of get_queryset - returns the active slides 

        :param request: http request
        :return: a query set
        """
        qs = Slide.objects.filter(active=True)
        return qs

    def save_model(self, request, obj, form, change):
        """Description of save_model - overridden method of the save 
        method. When the user changes the scenes via the QA form, 
        the usual save isn't sufficient so we override it.

        :param self: the admin slide obj
        :param request: the http request
        :param obj: the slide obj
        :param form: the form obj
        :param change: if the form has changed or not.
        """
        obj.user = request.user
        save_slide_model(self, request, obj, form, change)
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """Cannot show or use the delete button at this stage.

        :param request: http request
        :param obj: the slide obj
        :return: False
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Cannot show or use the add button at this stage

        :param request: http request
        :param obj: the TIFF obj
        :return: False
        """
        return False

    def prep_id(self, instance):
        """Returns the animal name that the slide belongs to

        :param instance: the TIFF obj
        :return: False
        """
        return instance.scan_run.prep.prep_id

    def response_change(self, request, obj):
        """Reset all tifs belong to this slide to its original state
        """
        if "_reset-slide" in request.POST:
            Slide.objects.filter(id=obj.id)\
                .update(insert_before_one=0,
                insert_between_one_two=0,
                insert_between_two_three=0,
                insert_between_three_four=0,
                insert_between_four_five=0,
                insert_between_five_six=0)
            SlideCziToTif.objects.filter(slide__id=obj.id).update(active=True)
            existing_file_names = []
            for placeholder in SlideCziToTif.objects.filter(slide__id=obj.id).all():
                if placeholder.file_name in existing_file_names:
                    placeholder.delete()
                else:
                    existing_file_names.append(placeholder.file_name)
            scene_reorder(obj.id)
            self.message_user(request, "The slide has been reset to it's original state.")
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)

class SectionResource(resources.ModelResource):
    def __init__(self, **kwargs):
        super().__init__()
        self.animal = kwargs.get("slide__scan_run__prep")

    def filter_export(self, queryset, **kwargs):
        query = queryset.filter(slide__scan_run__prep=self.animal) 
        print(f"DEBUG: Filtering queryset for animal {self.animal}: -> {query.query}")
        return query

    class Meta:
        model = SlideCziToTif 
        fields = ('id', 'czifile', 'file_name', 'scene_order', 'channel', 'active')
        #exclude = ('scene_index', 'file_size', 'width', 'height', 'processing_duration')

    
@admin.register(SlideCziToTif)
class OrderingAdmin(ImportExportModelAdmin):
    resource_classes = [SectionResource]
    export_form_class = CustomExportForm

    search_fields = ['slide__scan_run__prep__prep_id']
    list_display = ('slide__file_name', 'file_name', 'scene_order', 'channel', 'active', 'created')
    ordering = ['slide__scan_run__prep__prep_id', 'scene_order', 'channel', 'file_name']

    def get_export_resource_kwargs(self, request, **kwargs):
        export_form = kwargs.get("export_form")
        if export_form:
            kwargs.update(slide__scan_run__prep=export_form.cleaned_data["animal"])
        return kwargs    

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        return True
    
    
@admin.register(Section)
class SectionAdmin(AtlasAdminModel, ExportCsvMixin):
    """This class describes the Section methods and attributes. 
    Sections come from a view and 
    not a table so it needs to be handled a bit differently.

    :Inheritance:
        :AtlasAdminModel: The base admin model
        :ExportCsvMixin: The class with standard features and CSV
            exporter method.
    """
    indexCounter = -1
    list_display = ('czi_file', 'tif','section_number', 'slide','scene', 'scene_index', 'histogram', 'image_tag')
    ordering = ['prep_id', 'channel']
    list_filter = []
    list_display_links = None
    search_fields = ['prep_id', 'file_name']
    list_per_page = 1000
    class Media:
        css = {'all': ('admin/css/thumbnail.css',)}

    def changelist_view(self, request, extra_context=None):
        title = 'List sections by animal name'
        subtitle = 'Enter a valid animal name in the search field below'
        extra_context = {'title': title, 'subtitle': subtitle}
        return super(SectionAdmin, self).changelist_view(request, extra_context=extra_context)

    def section_number(self, instance):
        """ Description of section_number - this is just an ordered query,
        so to get the section number, we
        just use an incrementor

        :param instance: section obj
        """
        self.indexCounter += 1
        return self.indexCounter

    section_number.short_description = 'Section'


    def get_queryset(self, request, obj=None):
        """Description of get_queryset - the query starts out with an 
        empty qeuryset 'prep_id=XXXX' so the initial page is empty 
        and the user is forced to select one and only one animal. 
        The order is decided upon whether the brain was section 
        from left to right, or right to left. This comes
        from the histology table: side_sectioned_first
        and then slide physical ID and scene number

        :param request: http request
        :param obj: section obj
        :return: the queryset ordered correctly
        """
        self.indexCounter = -1
        sections = Section.objects.filter(prep_id='XXXX')
        if request and request.GET:
            prep_id = request.GET['q']
            histology = None
            try:
                histology = Histology.objects.get(prep_id=prep_id)
            except Histology.DoesNotExist:
                orderby = 'ASC'

            if histology is not None: 
                orderby = histology.side_sectioned_first

            if orderby == 'DESC':
                sections =  Section.objects.filter(prep_id__exact=prep_id).filter(channel=1)\
                    .order_by('-slide_physical_id', '-scene_number')
            else:
                sections = Section.objects.filter(prep_id__exact=prep_id).filter(channel=1)\
                    .order_by('slide_physical_id', 'scene_number')

        return sections

    def has_change_permission(self, request, obj=None):
        """The edit button is not shown as sections are a view and they can't be changed.

        :param request: http request
        :param obj: the section obj
        :return: False
        """
        return False

    def has_add_permission(self, request, obj=None):
        """The add button is not shown as sections are a view and they can't be added to.

        :param request: http request
        :param obj: the section obj
        :return: False
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """The add button is not shown as sections are a view and they can't be added to.
        
        :param request: http request
        :param obj: the section obj
        :return: False
        """
        return False


@admin.register(admin.models.LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """This class describes the log objects used during the 
    preprocessing pipeline

    :Inheritance:
        :admin.ModelAdmin: the base Django admin obj
    """
    # to have a date-based drilldown navigation in the admin page
    date_hierarchy = 'action_time'

    # to filter the resultes by users, content types and action flags
    list_filter = ['action_time', 'action_flag']
    search_fields = ['object_repr', 'change_message']
    list_display = ['action_time', 'user', 'content_type', 'action_flag']

    def has_add_permission(self, request):
        """This data is added by the 
        preprocessing pipeline so can't be changed here

        :param request: http request
        :return: False
        """
        return False

    def has_change_permission(self, request, obj=None):
        """This data is added by the preprocessing pipeline so can't be changed here
        
        :param request: http request
        :param obj: the LogEntry obj
        :return: False
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """This data is added by 
        the preprocessing pipeline so can't be deleted here
        
        :param request: http request
        :param obj: the LogEntry obj
        :return: False
        """
        return False

    def has_view_permission(self, request, obj=None):
        """This data can only be viewed by a superuser
        
        :param request: http request
        :param obj: the LogEntry obj
        :return: boolean depending on if the user is a super user or not

        """
        return request.user.is_superuser


admin.site.site_header = 'Brainsharer Admin'
admin.site.site_title = "Brainsharer"
admin.site.index_title = "Welcome to Brainsharer Portal"
admin.site.site_url = settings.BASE_FRONTEND_URL
