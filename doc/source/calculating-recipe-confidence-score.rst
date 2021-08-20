Calculating recipe confidence score
===================================

In some cases it may be necessary to evaluate how trustworthy a recipe is. This can be done by looking at how the recipe matches the product nutritional composition and how likely its total ingredient mass is. A confidence score is then created by aggregation of the two criteria. This score can be calculated with :func:`~impacts_estimation.utils.confidence_score`.

Nutritional distance
--------------------

For any recipe obtained with :class:`~impacts_estimation.impacts_estimation.RandomRecipeCreator`, it is possible to estimate a nutritional composition using :func:`~impacts_estimation.utils.nutriments_from_recipe`. This nutritional composition can then be compared to the reference composition of the product to evaluate the quality of the recipe prediction.

Considering a simplified example with only two nutrients, we can represent the nutritional compositions :math:`C` (reference composition) and :math:`\widehat{C}` (calculated composition) in a two-dimensional space, each dimension representing the content in a nutrient. Nutrients :math:`x` and :math:`y` are not the only nutrients composing the product but they are the only ones considered because information for the other nutrients is missing. Therefore the compositions may be below the line :math:`x + y = 1` but not above it.

.. figure:: /_static/confidence_score_nutritional_distance_component.svg
    :width: 300
    :align: center
    :alt: Confidence score nutritional distance component

The distance :math:`d` is the Euclidean distance between the reference and calculated compositions in the space of the nutrients considered. The more accurate the calculated composition, the smaller this distance is. The distance :math:`D` is the largest possible distance between two compositions. We can therefore normalize the distance between the compositions by the largest possible distance to obtain :math:`d/D` which varies between :math:`0` and :math:`1`. This reasoning can be extrapolated to :math:`n` dimensions to create the nutritional distance component of the confidence score.

.. math::
    S_{nutri} &= \frac{d}{D} \\
    S_{nutri} &= \frac{\sqrt{\sum_{n \in N} (M_n - \widehat{M_n})^2}}{\sqrt{2}}\\

Total ingredients mass likelihood
---------------------------------

The total ingredients mass can also be used to assess the likelihood of a recipe. In one hand, the assumption can be made that the food producers will tend to use as less ingredient as possible for a product to decrease production costs. Thus, the higher the total ingredient mass, the less likely the recipe is. In the other hand, when unbalanced recipes are allowed (see :ref:`Allowing unbalanced recipes`) and the total ingredient mass is lower than the final product mass, the lower the total ingredient mass, the more the skewed the mass balance is and the less likely the recipe is.

A total ingredient mass likelihood indicator can easily be created by looking at how far the mass is from the product mass compared to the bounds.

Let :math:`F` be the final mass of the product, :math:`M` the total mass of ingredients used, :math:`M_{min}` the minimum possible mass of ingredients used (:math:`M_{min} = F` if ``allow_unbalanced_recipe=False``) and :math:`M_{max}` the maximum possible mass of ingredients (:math:`M_{max} = \frac{F}{1-E}`). The total ingredient mass component of the confidence score :math:`S_{mass}` is defined as follows.

.. math::
    S_{mass} =
    \begin{cases}
        \frac{F - M}{F - M_{min}} \text{ if } \lt F\\
        \\
        0 \text{ if } M = F \\
        \\
        \frac{M - F}{M_{max} - F} \text{ if } M \gt F
    \end{cases}


.. figure:: /_static/confidence_score_mass_component.svg
    :width: 400
    :align: center
    :alt: Confidence score ingredient mass component

Weighting factor
----------------

Both component of the confidence score have values in :math:`[0,1]` with :math:`0` meaning a very high confidence level and :math:`1` a very poor one. These components can be combined in one score with higher values for better confidence with the following formula.

.. math::
    S = \frac{1}{wS_{nutri}+S_{mass}}

:math:`w` is a weighting factor allowing to give more or less weight to one or the other component. By default, the nutritional distance component accounts 10 times more than the total ingredients mass component.