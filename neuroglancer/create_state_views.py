from django.shortcuts import render
from bs4 import BeautifulSoup
import requests
import os
from brain.models import Animal
from authentication.models import User
from neuroglancer.models import NeuroglancerState
from datetime import datetime


class NeuroglancerJSONStateManager():
    """This class handles the creation of a JSON state for Neuroglancer: 
    """

    def __init__(self):
        self.state = {}

    def fetch_layers(self, request, animal_id):
        """Is this used?????????????
        """

        animal = Animal.objects.get(pk=animal_id)
        url = animal.lab.lab_url
        if 'ucsd' in url.lower():
            url += f'/{animal.animal}/neuroglancer_data/' 
        else:
            url += animal.animal
        directories = self.read_url(url, ext="C")
        datarows = self.create_layer_table(animal.animal, directories)
        return render(request, 'layer_table.html',{'datarows': datarows})

    def create_layer_table(self, animal, directories):
        layers = []
        for directory in directories:
            layer_name = os.path.basename(os.path.normpath(directory))
            if layer_name == animal:
                continue
            layer = {}
            layer['animal'] = animal
            layer['name'] = layer_name
            layer['source'] = f"{directory}"
            layer['type'] = self.get_layer_type(directory)
            layers.append(layer)
        return layers

    def read_url(self, url, ext='', params={}):
        response = requests.get(url, params=params)
        if response.ok:
            response_text = response.text
        else:
            return response.raise_for_status()
        soup = BeautifulSoup(response_text, 'html.parser')
        directories = [url + node.get('href') for node in soup.find_all('a') 
                if '?' not in node.get('href')
                and node.get('href') != "/"]
        return directories


    def get_layer_type(self, url):
        data_type = "NA"
        try:
            url += "info"
            response = requests.get(url)
            response.raise_for_status()
            info = response.json()
            if '@type' in info:
                data_type = info['@type']
            else:
                data_type = info['type']

        except Exception as err:
            print(f'Got error: {err}')
        
        return data_type

            
    def prepare_top_attributes(self, layer):
        # {'id': 9, 'group_name': 'DK39', 'lab': 'UCSD', 'description': 'C3', 'url': 'https://activebrainatlas.ucsd.edu/data/DK39/neuroglancer_data/C3', 'active': True, 'created': '2022-04-15T00:48:11', 'updated': '2022-04-15T14:48:11'}
        layer_name = layer['layer_name']
        visible_layer = layer_name
        resolution = float(layer['resolution']) # 0.325 for full res, 10.4 for downsampled
        zresolution = float(layer['zresolution'])
        # width and height should be in the REST/DB
        width = float(layer['width'])
        height = float(layer['height'])
        depth = float(layer['depth'])
        # 1 is good for downsampled stacks/volume and 
        # 60 is good for full res
        # 3 is good for annotation layer
        # If the image stack is downsampled, we need to adjust the position
        scaling_factor = 32
        crossSectionScale = 1
        if resolution < 5: 
            scaling_factor = 1
            crossSectionScale = 60
        # Note, the princeton version of the Allen atlas has an attribute called: crossSectionOrientation which sets the
        # orientation of the views in the 4 panels. It is necessary for this one but not others. 
        # These four numbers are the quaternions
        if 'cross_section_orientation' in layer and layer['cross_section_orientation'] is not None:
            cso = layer['cross_section_orientation']
            cso_list = []
            for x in cso.split(','):
                try:
                    cso_list.append(float(x))
                except ValueError:
                    break

            if len(cso_list) == 4:
                self.state['crossSectionOrientation'] = cso_list
        
        self.state['crossSectionScale'] =  crossSectionScale
        self.state['dimensions'] = {'x':[resolution, 'um'],
                                'y':[resolution, 'um'],
                                'z':[zresolution, 'um'] }
        self.state['position'] = [width // 2 // scaling_factor, height // 2 // scaling_factor, depth // 2]
        self.state['selectedLayer'] = {'visible': True, 'layer': visible_layer}
        self.state['projectionScale'] = 1024
        self.state['max_range'] = layer['max_range']

    def prepare_bottom_attributes(self):
        self.state['gpuMemoryLimit'] = 4000000000
        self.state['systemMemoryLimit'] = 4000000000
        self.state['layout'] = '4panel'
            
            
    def create_layer(self, data):
        layer_name = data['layer_name']
        url = data['url']
        layer = {}
        max_range = data['max_range']
        shaders = {}
        shaders['C1'] = """
            #uicontrol invlerp normalized (range=[0,{max_range}])
            #uicontrol float gamma slider(min=0.05, max=2.5, default=1.0, step=0.05)
            void main() {{    
                float pix =  normalized();
                pix = pow(pix,gamma);
                    emitGrayscale(pix) ;
                }}
                """.format(max_range=max_range)
        shaders['C2'] = """
            #uicontrol invlerp normalized (range=[0,{max_range}])
            #uicontrol float gamma slider(min=0.05, max=2.5, default=1.0, step=0.05)
            #uicontrol bool colour checkbox(default=true)
            void main() {{
                    float pix =  normalized();
                    pix = pow(pix,gamma);    
                    if (colour) {{
                        emitRGB(vec3(pix,0,0));
                    }} else {{
                        emitGrayscale(pix) ;
                    }}
                    }}
                    """.format(max_range=max_range)
        shaders['C3'] = """
            #uicontrol invlerp normalized (range=[0,{max_range}])
            #uicontrol float gamma slider(min=0.05, max=2.5, default=1.0, step=0.05)
            #uicontrol bool colour checkbox(default=true)
            void main() {{
                    float pix =  normalized();
                    pix = pow(pix,gamma);
                        if (colour) {{      
                            emitRGB(vec3(0, (pix),0));
                        }} else {{
                            emitGrayscale(pix) ;
                        }}
                        }}""".format(max_range=max_range)

        shaders['annotation'] = '#uicontrol float size slider(min=0, max=10, default=1)\nvoid main() {setColor(defaultColor());setPointMarkerSize(size);}'
        layer['name'] = layer_name
        if 'layer_type' in self.state and self.state['layer_type'] == 'image':
            layer['shader'] = shaders.get(layer_name, shaders['C1'])
        if 'layer_type' in self.state and self.state['layer_type'] == 'annotation':
            layer['shader'] = shaders.get('annotation')
        
        layer['source'] = f'precomputed://{url}'
        layer['type'] = data['layer_type']
        layer['visible'] = True
        
        return layer
            
    def create_neuroglancer_model(self, title):

        owner = User.objects.first()

        neuroglancer_state = NeuroglancerState.objects.create(owner=owner, neuroglancer_state=self.state,
            created=datetime.now(), updated=datetime.now(), user_date="999999", 
            comments=title, readonly=False)
        return neuroglancer_state.id