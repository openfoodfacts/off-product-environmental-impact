Characterizing ingredients
==========================

In order to guess a product's recipe and to calculate its environmental impact, some characteristics of its ingredients are needed. Nutritional compositions of the ingredients are needed to estimate a product recipe. Environmental impact of the ingredients is needed to compute the impact of the product. Characterizing the ingredients can be done by linking the ingredients used in the Open Food Facts database to external databases related to nutrition and environmental impact.

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
---------------

Once the links between OFF products and nutritional/environmental databases entries have been identified, the attributes of the ingredients are gathered in a single dataset. This dataset is stored in ``ingredients_data.json``.

Nutrition
+++++++++

For each ingredient and each considered nutriment, ``ingredients_data.json`` contains three attributes. ``value`` is the reference content of this nutriment, ``min`` and ``max`` are respectively the minimum and maximum contents of this nutriment.

For data coming from Ciqual, the ``min`` and ``max`` values are already available. For FCEN, only a mean and a standard deviation are available. The ``min`` and ``max`` values have been obtained considering a 95% confidence interval for a normal law.

When the ingredient is linked to several entries of the Ciqual and/or FCEN databases, ``value`` is the mean of each entry reference value and ``min`` and ``max`` are the minimum (resp. maximum) of entries minimums (resp. maximums).

Environmental impact
++++++++++++++++++++

The way the environmental impact data is linked to each ingredient is slightly different from the nutritional data. The impact estimation tool does not need a minimum or maximum value but an uncertainty distribution of the impact.

In the most simple case, the ingredient is linked to only one agribalyse entry or to several entries with the same impact. In that case, this value is set in the ``amount`` field of the ingredient and no uncertainty data are created.

If the product is linked to several Agribalyse entries with different impact data, then the ``amount`` field contains the geometric mean of each entry impact and the ``uncertainty_distributions`` field contains one distribution per Agribalyse entry. As the Agribalyse database does not contain impact uncertainty but only a quantitative Data Quality Rating, the uncertainty distributions are only uniform distributions with maximum and minimum being the impact value of the entry. This could be improved in the future by adding real uncertainty distributions from Life Cycle Assessment modelling.

.. note::

    TODO: explain why only agricultural steps are considered.

Data sources
++++++++++++

For traceability purposes, the nutritional and environmental databases entries linked to each ingredient are stored in the ``nutritional_data_sources`` and  ``environmental_impact_data_sources`` attributes.

Ingredients defined percentages distributions
---------------------------------------------
