Characterizing ingredients
==========================

In order to guess a product's recipe and to calculate its environmental impact, some characteristics of its ingredients are needed. Nutritional compositions of the ingredients are needed to estimate a product recipe and environmental impact of the ingredients is needed to compute the impact of the product. Characterizing the ingredients can be done by linking the ingredients used in the Open Food Facts database to external databases related to nutrition and environmental impact.

Available data
--------------

Ciqual
++++++

`Ciqual <https://ciqual.anses.fr/>`_ is a nutritional database developed by the `ANSES <https://www.anses.fr/fr>`_ that contains nutritional information for more than 3 000 ingredients and recipes.

FCEN
++++

The `FCEN <https://aliments-nutrition.canada.ca/cnf-fce/index-fra.jsp>`_ is the canadian equivalent of Ciqual. It contains nutritional information for more than 5 000 ingredients and recipes.

Agribalyse
++++++++++

`Agribalyse <https://agribalyse.ademe.fr/>`_ is a database developed by `ADEME <https://www.ademe.fr/>`_ that contains environmental impact data for around 2 500 entries of the Ciqual database.

Linking tables
--------------

In order to link the ingredients from OFF to the aforementioned databases, linking tables have been created. They can be found in ``agribalyse_off_links.csv``, ``ciqual_off_links.csv``, ``fcen_off_links.csv``. These tables are used to establish a link between an ingredient of the OFF database and one or several entries of the nutritional/environmental databases. They can be edited and matches can be added in order to improve the quality of the impact estimation.

``off_duplicates.csv`` contains matches between OFF ingredients. The column ``proxy_type`` is null when the match between the ingredient is consistent from both nutritional and environmental point of view, it is ``1`` if the match concerns only nutrition and ``2`` if it concerns only environmental impact.

Data processing
+++++++++++++++

Nutrition
---------

Environmental impact
--------------------

Ingredients defined percentages distributions
---------------------------------------------
