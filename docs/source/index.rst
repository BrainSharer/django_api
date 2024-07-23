.. Brainsharer documentation master file, created by
   sphinx-quickstart on Wed Jun  1 15:07:58 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Brainsharer documentation
============================================
These pages contain documentation regarding the MVC (model, view, and controller) programming
classes for the Django database interface. Django breaks up this interface into 'apps'. The two
main apps of interest are:

* Brain - modules that describe all the tools used to manage the animal, scan run, histology, and organic label tables.
* Neuroglancer - tools that are used to manage the Neuroglancer JSON data and annotation data.

There are several other apps that deal with authentictaion and various Django tools, but they
are not listed. 

These apps contain classes for each of the MVC components. The models.py files contains classes
that describe a database schema table.

Use the side navigation panel to view different classes and methods within each module.

****

.. toctree::
   :titlesonly:
   :maxdepth: 1
   :caption: Brain
   :hidden:
   
   Admin module <modules/brain/admin.rst>
   Brain forms <modules/brain/forms.rst> 
   Brain models (database columns) <modules/brain/models.rst> 
   REST API serializers <modules/brain/serializers.rst> 
   REST API endpoints <modules/brain/views.rst>

.. toctree::
   :maxdepth: 1
   :caption: Neuroglancer:
   :hidden:

   Neuroglancer admin module <modules/neuroglancer/admin.rst> 
   Annotation manager <modules/neuroglancer/annotation_session_manager.rst>
   Neuroglancer models (database columns) <modules/neuroglancer/models.rst> 
   REST API serializers <modules/neuroglancer/serializers.rst> 
   Neuroglancer tests <modules/neuroglancer/tests.rst>
   REST API endpoints <modules/neuroglancer/views.rst>
   Align atlas tools <modules/neuroglancer/atlas.rst>

.. toctree::
   :maxdepth: 1
   :caption: Entity relationship diagram for the Brainsharer database:
   
   Diagram showing database tables and columns <modules/erd.rst>

Indices and tables
~~~~~~~~~~~~~~~~~~

* :ref:`genindex`
* :ref:`modindex`
