Calculating recipe environmental impact
=======================================

The calculation of the environmental impact of a recipe is done by :class:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator` or its wrapper :func:`~impacts_estimation.impacts_estimation.impact_from_recipe`. It is calculated by doing a sum of the ingredients masses weighted by their environmental impact. For more information about how the environmental impact of ingredients is collected, see :ref:`Characterizing ingredients`.

Ingredients impacts definition
------------------------------

The first step of recipe environmental impact calculation is to define the impact of the ingredients composing the recipe.


.. code-block:: json
   :caption: Example of ingredient description in ``ingredients_data.json``

    {
      "en:foo": {
        "id": "en:foo",
        "environmental_impact_data_sources": [
          {
            "database": "agribalyse",
            "entry": "Foo, production process A"
          },
          {
            "database": "agribalyse",
            "entry": "Foo, production process B"
          }
        ],
        "impacts": {
          "Score unique EF": {
            "unit": "mPt",
            "amount": 1.46,
            "uncertainty_distributions": [
              {
                "distribution": "uniform",
                "minimum": 0.83,
                "maximum": 1.76
              },
              {
                "distribution": "normal",
                "mean": 1.62,
                "standard deviation": 0.257
              }
            ]
          }
        }
      }
    }


Without uncertainty
+++++++++++++++++++

If :class:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator` is instantiated with ``use_uncertainty=False`` (by default), the impact of the ingredients will be the one specified in the ``amount`` attribute of the environmental impact in ``ingredients_data.json``.

With uncertainty
++++++++++++++++

If :class:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator` is instantiated with ``use_uncertainty=True``, the ingredients impacts will be defined using one randomly chosen distribution among the uncertainty distributions specified in the ``uncertainty_distributions`` attribute of the environmental impact in ``ingredients_data.json``. This allows to use the LCA data uncertainty and to link several possible LCA processes to one ingredient.

.. warning::
   Multiple calls of :func:`~impacts_estimation.impacts_estimation.impact_from_recipe` with ``use_uncertainty=True`` may result in different outputs.

Recipe impact and ingredient impact share
-----------------------------------------

Once the ingredients impacts have been defined (with :meth:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator._define_ingredients_impacts` automatically called at initialization), the recipe environmental impact can be returned by :meth:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator.get_recipe_impact`, as well as the ingredients shares of the recipe's impact with :meth:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator.get_ingredient_impact_share`.