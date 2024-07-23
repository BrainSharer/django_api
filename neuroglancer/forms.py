from django import forms
from django.forms import ModelChoiceField

from neuroglancer.models import NeuroglancerState

class AnimalChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.prep_id

class LayerForm(forms.ModelForm):
    neuroglancerStates = ModelChoiceField(label='Annotation Layer',
                            queryset=NeuroglancerState.objects.filter(readonly=True).all().order_by('comments'),
                            required=True,
                            widget=forms.Select(attrs={'onchange': 'layerdata_form.submit();', 'class': 'form-control'}))
    class Meta:
        model = NeuroglancerState
        exclude = ['prep','structure','person','url','transformation','input_type',
            'x', 'y', 'section', 'active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['layer'].queryset = LayerData.objects.all()
        self.fields['layer'].options = {'one':1, 'two':2}
    