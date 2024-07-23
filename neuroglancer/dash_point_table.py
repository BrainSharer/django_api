"""
This application depends on the png files located in:
/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/DKXXX/www
This program allows the user to view annotations per section, make selections
and place those selected annotations into an editable and exportable datatable, (spreadsheet)
Make sure this app is imported into the admin.py app
"""
import dash_core_components as dcc
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State
import dash_html_components as html

styles = {
    'slider': {
        'border': 'thin lightgrey solid',
    },
    'table': {
        'padding': '10px 100px 10px 100px',
    }
}

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app_name = "ScatterBrain"
dashboard_name = 'DashPointTable'
point_table = DjangoDash(name=dashboard_name,
                         external_stylesheets=external_stylesheets)
tablecols = ['area', 'x', 'y', 'section']
point_table.layout = html.Div(id='main', children=[
    html.Div(id='graph-div'),
    html.Div(id='section-slider'),
    html.Div(id='intermediate-value', style={'display': 'none'}),
    html.Div([
    dash_table.DataTable(
        id='computed-table',
        columns=[{'id': p, 'name': p} for p in tablecols],
    editable=True,
    export_format='xlsx',
    export_headers='display',
    style_table=styles['table']
)
])
])
@point_table.expanded_callback(
    Output('intermediate-value', 'children'),
    [Input('section-slider', 'value')])
def callback_initial(section, *args, **kwargs):
    dfjson = kwargs['session_state']['df']
    df = pd.read_json(dfjson)
    df = df[(df.Layer == 'PM nucleus') | (df.Layer == 'premotor')]
    if section is None:
        section = df['Section'].min()
    return section

@point_table.callback(
    Output(component_id='graph-div', component_property='children'),
    [Input(component_id='section-slider', component_property='value')])
def callback_main(section, *args, **kwargs):
    comments = kwargs['session_state']['comments']
    animal = kwargs['session_state']['animal']
    dfjson = kwargs['session_state']['df']
    df = pd.read_json(dfjson)
    df = df[(df.Layer == 'PM nucleus') | (df.Layer == 'premotor')]
    sections = df['Section'].sort_values().unique().tolist()
    if section is None:
        section = df['Section'].min()
    img_width = kwargs['session_state']['img_width']
    img_height = kwargs['session_state']['img_height']
    section_min = df['Section'].min()
    section_max = df['Section'].max()
    df = df.loc[ df['Section'] == section]
    section = str(section).zfill(3)
    source = f"https://activebrainatlas.ucsd.edu/data/{animal}/www/{section}.png"

    fig = go.FigureWidget([go.Scatter(y=df['Y'], x=df['X'], mode='markers')])
    fig.add_layout_image(
        dict(
            x=0,
            sizex=img_width,
            y=0,
            sizey=img_height,
            xref="x",
            yref="y",
            yanchor="top",
            opacity=0.5,
            layer="below",
            source=source,
            sizing="contain")
    )
    title = f"{comments}, section {section}"
    fig.update_layout(title=title)
    fig.update_xaxes(range=[0, img_width])
    fig.update_yaxes(range=[0, img_height], scaleanchor="x")
    fig.update_layout(template="plotly_white")
    fig['layout']['yaxis']['autorange'] = "reversed"
    fig['layout']['height'] = 600
    scatter = fig.data[0]

    scatter.marker.opacity = 1
    scatter.marker.size = 6
    scatter.marker.color = 'yellow'

    scatter_plot = dcc.Graph(id='main-scatter', figure=fig,
                           style={'display': 'inline-block', 'width': '100%',
                           'height': '100%;'})

    kwargs['session_state']['section'] = section
    slider = dcc.Slider(
            id='section-slider',
            min=section_min,
            max=section_max,
            value=section,
            marks={k:{'label':'-' + str(k) + '-',
                      'style':{'color':'white',
                               'fontSize':'10',
                               'fontWeight': 'bolder',
                               'background': '#{0:06X}'.format(k*k),
                               'writing-mode':'vertical-rl',
                               'text-orientation':'sideways'}} for k in sections},
            step=None
        )


    children = [scatter_plot, slider]
    return children

@point_table.callback(
    Output(component_id='computed-table', component_property='data'),
    [Input(component_id='main-scatter', component_property='selectedData')],
    [State(component_id='computed-table', component_property='data')]
)
def display_selected_data(selectedData, *args, **kwargs):
    points = kwargs['session_state']['points']
    section = kwargs['session_state']['section']

    if selectedData is not None and 'points' in selectedData:
        selected_points = selectedData['points']
        selected_points = [dict(item, section=section) for item in selected_points]
        points.extend(selected_points)
        kwargs['session_state']['points'] = points
    return points

