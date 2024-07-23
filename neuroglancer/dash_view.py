from django.shortcuts import render
from brain.models import ScanRun
from neuroglancer.models import NeuroglancerState

def dash_scatter_view(request, template_name="dash_point_table.html", **kwargs):
    'Example view that inserts content into the dash context passed to the dash application'
    context = {}
    pk = kwargs['pk']
    dash_context = request.session.get("django_plotly_dash", dict())
    dash_context['pk'] = pk
    neuroglancerState = NeuroglancerState.objects.get(pk=pk)
    animal = neuroglancerState.animal
    scanRun = ScanRun.objects.get(prep_id__exact=animal)
    df = neuroglancerState.points
    df = df[(df.Layer == 'PM nucleus') | (df.Layer == 'premotor')]
    df.reset_index(inplace=True)
    dash_context['img_width'] = scanRun.width
    dash_context['img_height'] = scanRun.height
    dash_context['animal'] = animal
    dash_context['comments'] = neuroglancerState.comments
    dash_context['df'] = df.to_json()
    dash_context['points'] = []
    dash_context['section'] = str(df['Section'].min())
    request.session['django_plotly_dash'] = dash_context
    return render(request, template_name=template_name, context=context)

def session_state_view(request, template_name, **kwargs):
    'Example view that exhibits the use of sessions to store state'
    session = request.session
    demo_count = session.get('django_plotly_dash', {})
    ind_use = demo_count.get('ind_use', 0)
    ind_use += 1
    demo_count['ind_use'] = ind_use
    context = {'ind_use' : ind_use}
    session['django_plotly_dash'] = demo_count
    return render(request, template_name=template_name, context=context)
