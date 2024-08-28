
from django.contrib import admin
from django.forms import TextInput, Textarea, DateInput, NumberInput, Select
from django.db import models
import csv
from django.http import HttpResponse
from django.contrib.admin.widgets import AdminDateWidget


class AtlasAdminModel(admin.ModelAdmin):
    """This is used as a base class for most of the other classes. It contains
    all the common variables that all the tables/objects have. It inherits
    from the Django base admin model: admin.ModelAdmin
    """
    class Media:
        """This is a simple class that defines some CSS attributes for the 
        thumbnails
        """
        css = {
            'all': ('admin/css/thumbnail.css',)
        }

    def is_active(self, instance):
        """A method returning a boolean showing if the data row is active

        :param instance: obj class
        :return: A boolean
        """
        return instance.active == 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Simple formatting for foreign keys

        :param db_field: data row field
        :param request: http request
        :param kwargs: extra args
        :return: the HTML of the form field
        """
        kwargs['widget'] = Select(attrs={'style': 'width: 250px;'})
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


    formfield_overrides = {
        models.CharField: {'widget': Select(attrs={'size': '20', 'style': 'width:250px;'})},
        models.CharField: {'widget': TextInput(attrs={'size': '20','style': 'width:100px;'})},
        models.DateTimeField: {'widget': DateInput(attrs={'size': '20'})},
        models.DateField: {'widget': AdminDateWidget(attrs={'size': '20'})},
        models.IntegerField: {'widget': NumberInput(attrs={'size': '40', 'style': 'width:100px;'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 40})},
    }

    is_active.boolean = True
    list_filter = ('created', )
    fields = []
    actions = ["export_as_csv"]


class ExportCsvMixin:
    """A class used by most of the admin categories. It adds formatting 
    to make fields look consistent and also adds the method to export 
    to CSV from each of the 'Action' dropdowns in each category. 
    """

    def export_as_csv(self, request, queryset):
        """Set the callback function to be executed when the device sends a
        notification to the client.

        :param request: The http request
        :param queryset: The query used to fetch the CSV data
        :return: a http response
        """

        meta = self.model._meta
        excludes = ['histogram',  'image_tag']
        field_names = [
            field.name for field in meta.fields if field.name not in excludes]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(
            meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field)
                                  for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"
