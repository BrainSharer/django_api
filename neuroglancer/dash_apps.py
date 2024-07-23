'''Dash charts for Django
'''
import dash_core_components as dcc
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash
import pandas as pd
from dash.dependencies import Input, Output
import dash_html_components as html

app_name = "ScatterBrain"
styles = {
    'slider': {
        'border': 'thin lightgrey solid',
        'height':'80'
    },
    'table': {
        'border': 'thin lightgrey solid',
        'padding': '0'
    }
}

dashboard_name = 'ScatterPoint'
scatter_points = DjangoDash(name=dashboard_name,
                           serve_locally=True,
                           add_bootstrap_links=True
                          )

scatter_points.layout = html.Div(id='main', children=[
    html.Div([html.H6(id='selected-data')]),
    html.Div(id='section-slider'),
    html.Div(id='output-div'),

])

@scatter_points.expanded_callback(
    Output('output-div', 'children'),
    [Input('section-slider', 'value')])

def callback_initial(section, *args, **kwargs):
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

    slider = html.Div([
        dcc.Slider(
            id='section-slider',
            min=section_min,
            max=section_max,
            value=section,
            marks={k:{'label':'<-' + str(k),
                      'style':{'color':'white',
                               'fontSize':'10',
                               'fontWeight': 'bolder',
                               'background': '#{0:06X}'.format(k*k),
                               'writing-mode':'vertical-rl',
                               'text-orientation':'sideways'}} for k in sections},
            step=None
        )
    ], style=styles['slider'])

    tablecols = ['Layer', 'X', 'Y', 'Section']
    t = go.FigureWidget([go.Table(
        header=dict(values=tablecols,
                    fill=dict(color='#79AEC8'),
                    align=['left'] * 5),
        cells=dict(values=[df[col] for col in tablecols],
                   fill=dict(color='#FFFFFF'),
                   align=['left'] * 5))])
    datatable = dcc.Graph(id='main-table', figure=t, style=styles['table'])


    children = [scatter_plot, slider, datatable]
    return children

@scatter_points.callback(
    Output('selected-data', 'children'),
    [Input('main-scatter', 'selectedData')])
def display_selected_data(selectedData, *args, **kwargs):
    results = "Use the lasso or box to select points"
    if selectedData is not None and 'points' in selectedData:
        points = selectedData['points']
        results = f"You have selected {len(points)} point"
        if len(points) > 1:
            results += "s"
    return results
