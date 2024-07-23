from ipywidgets import widgets
import plotly.graph_objects as go
from ipywidgets.embed import embed_data
from neuroglancer.models import NeuroglancerState

def create_2DgraphXXX():


    img_width = 65000
    img_height = 36000

    id = 200
    neuroglancerState = NeuroglancerState.objects.get(pk=id)
    df = neuroglancerState.points
    df.reset_index(inplace=True)
    df['ID'] = df.index
    cols = ['ID', 'Layer', 'X', 'Y', 'Section']

    section = df['Section'].min()

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
            name="showme",
            source=f"https://activebrainatlas.ucsd.edu/data/DK52/www/{section}.png",
            sizing="contain")
    )

    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0))
    fig.update_xaxes(range=[0, img_width])
    fig.update_yaxes(range=[0, img_height], scaleanchor="x")
    fig.update_layout(template="plotly_white")
    fig['layout']['yaxis']['autorange'] = "reversed"

    scatter = fig.data[0]

    scatter.marker.opacity = 1
    scatter.marker.size = 6

    section_selector = widgets.Dropdown(
        options=list(df['Section'].sort_values().unique()),
        value=df['Section'].iloc[0],
        description='Section:',
    )

    layer_selector = widgets.Dropdown(
        options=list(df['Layer'].sort_values().unique()),
        value=df['Layer'].iloc[0],
        description='Layer:',
    )


    def response(change):
        filter_list = [s and l for s, l in
                       zip(df['Section'] == section_selector.value, df['Layer'] == layer_selector.value)]
        tmp_df = df[filter_list]

        x = tmp_df['X']
        y = tmp_df['Y']
        with fig.batch_update():
            fig.layout.xaxis.title = "X"
            fig.layout.yaxis.title = "Y"
            fig.layout.images[0].source = f"https://activebrainatlas.ucsd.edu/data/DK52/www/{section_selector.value}.png"
            scatter.x = x
            scatter.y = y
        with t.batch_update():
            t.layout.title = f"{len(tmp_df)} points"
            t.data[0].cells.values = None


    section_selector.observe(response, names="value")
    layer_selector.observe(response, names="value")

    t = go.FigureWidget([go.Table(header=dict(), cells=dict())])


    def selection_fn(trace, points, selector):
        t.layout.title = f"You have selected {len(points.point_inds)} points"


    scatter.on_selection(selection_fn)

    selection_container = widgets.HBox([section_selector, layer_selector])
    figure_container = widgets.VBox([fig, t])
    return embed_data(views=[figure_container])

def create_2Dgraph(animal, section):


    img_width = 65000
    img_height = 36000

    id = 200
    neuroglancerState = NeuroglancerState.objects.get(pk=id)
    df = neuroglancerState.points
    df.reset_index(inplace=True)
    df['ID'] = df.index

    df = df.loc[ df['Section'] == section]
    section = str(section).zfill(3)

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
            name="showme",
            source=f"https://activebrainatlas.ucsd.edu/data/{animal}/www/{section}.png",
            sizing="contain")
    )

    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0))
    fig.update_xaxes(range=[0, img_width])
    fig.update_yaxes(range=[0, img_height], scaleanchor="x")
    fig.update_layout(template="plotly_white")
    fig['layout']['yaxis']['autorange'] = "reversed"
    return fig
