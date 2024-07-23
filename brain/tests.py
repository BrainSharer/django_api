import datetime, random
from django import forms
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from authentication.models import User

from django.test import SimpleTestCase, TestCase, TransactionTestCase
from brain.models import Animal, ScanRun, Slide, SlideCziToTif
from brain.forms import save_slide_model
from brain.admin import SlideAdmin
from unittest import mock


class TestSlideForms(TransactionTestCase):

    def setUp(self):
        animal = 'DK' + str(random.randint(100,999))
        self.prep = Animal.objects.create(prep_id=animal)

        self.scan_run = ScanRun.objects.create(prep=self.prep, resolution=0.325, number_of_slides=1, zresolution=20)

        self.slide = Slide.objects.create(
            scan_run=self.scan_run,
            slide_physical_id=1,
            slide_status='Good',
            scenes=4,
            insert_before_one=0,
            insert_between_one_two=0,
            insert_between_two_three=0,
            insert_between_three_four=0,
            insert_between_four_five=0,
            insert_between_five_six=0,
            file_name='XXX.tif',
            file_size=0,
            processed=True
        )
        self.site = AdminSite()

        self.tif1 = SlideCziToTif.objects.create(slide=self.slide,
                                                 file_name='S1C1.tif',
                                                 scene_number=1,
                                                 scene_index=0,
                                                 channel=1,
                                                 width=0,
                                                 height=0,
                                                 file_size=0,
                                                 processing_duration=0)
        self.tif2 = SlideCziToTif.objects.create(slide=self.slide,
                                                 file_name='S2C1.tif',
                                                 scene_number=2,
                                                 scene_index=0,
                                                 channel=1,
                                                 width=0,
                                                 height=0,
                                                 file_size=0,
                                                 processing_duration=0)
        self.tif3 = SlideCziToTif.objects.create(slide=self.slide,
                                                 file_name='S3C1.tif',
                                                 scene_number=3,
                                                 scene_index=0,
                                                 channel=1,
                                                 width=0,
                                                 height=0,
                                                 file_size=0,
                                                 processing_duration=0)

    def test_modeladmin_str(self):
        ma = ModelAdmin(Slide, self.site)
        self.assertEqual(str(ma), 'brain.ModelAdmin')

    def test_default_fields(self):
        ma = ModelAdmin(Slide, self.site)
        '''
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'bio', 'sign_date'])
        self.assertEqual(list(ma.get_fields(request)), ['name', 'bio', 'sign_date'])
        self.assertEqual(list(ma.get_fields(request, self.slide)),
                         ['active', 'scan_run', 'slide_physical_id', 'rescan_number', 'slide_status', 'scenes',
                          'insert_before_one', 'scene_qc_1', 'insert_between_one_two', 'scene_qc_2',
                          'insert_between_two_three', 'scene_qc_3', 'insert_between_three_four', 'scene_qc_4',
                          'insert_between_four_five', 'scene_qc_5', 'insert_between_five_six', 'scene_qc_6',
                          'file_name', 'comments', 'file_size', 'processed'])
        self.assertIsNone(ma.get_exclude(request, self.slide))
        '''

    def test_save_model(self):
        ma = SlideAdmin(Slide, self.site)
        super_user = User.objects.create_superuser(username='super', email='super@email.org',
                                                   password='pass')

        """
        request.user = super_user
        form = ma.get_form(self, request, change=None)
        for i in range(13):
            form.cleaned_data = {
                'slide_status': 'Good',
                'insert_before_one': i,
                'insert_between_one_two': i,
                'insert_between_two_three': i,
                'insert_between_three_four': 0,
                'insert_between_four_five': 0,
                'insert_between_five_six': 0}
            total_inserts = i * 3
            precount = SlideCziToTif.objects.filter(FK_slide_id=self.slide.id).filter(active=1).count()
            ma.save_model(obj=self.slide, request=request, form=form, change=None)
            postcount = SlideCziToTif.objects.filter(FK_slide_id=self.slide.id).filter(active=1).count()
            # some test assertions here
            self.assertEquals(precount + total_inserts, postcount)
    """
